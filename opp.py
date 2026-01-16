import streamlit as st
import requests
import random
import os
import re
import json
from datetime import datetime

# =========================
# [1] 필수 설정 (선생님 확인)
# =========================
# ※ 주의: 여기에 선생님의 API 키를 정확히 넣어주세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
TEACHER_PASSWORD = "1234" 

# 구글 API 호출을 위한 모델명 수정 (v1beta용 최적화)
MODEL_NAME = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# =========================
# [2] UI + 음성(TTS/STT) + 보안 통합
# =========================
st.set_page_config(page_title="AI 수학 감독관", layout="centered")

# CSS 및 JavaScript 통합 (마이크 인식 및 음성 출력)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    .stChatFloatingInputContainer {padding-bottom: 20px;}
    </style>
    <script>
    // 1. AI 목소리 출력 (TTS)
    function speak(text) {
        window.speechSynthesis.cancel();
        const msg = new SpeechSynthesisUtterance();
        msg.text = text;
        msg.lang = 'ko-KR';
        msg.rate = 1.1;
        window.speechSynthesis.speak(msg);
    }

    // 2. 음성 인식 (STT) - 마이크 기능
    let recognition;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.lang = 'ko-KR';
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            // 스트림릿 입력창에 텍스트를 강제로 주입하는 대신 알림창으로 보여줌
            alert("인식된 내용: " + transcript + "\\n\\n확인 버튼을 누른 후, 아래 입력창에 이 내용을 적고 엔터를 쳐주세요!");
        };
    }

    function startListening() {
        if(recognition) {
            recognition.start();
        } else {
            alert("이 브라우저는 음성 인식을 지원하지 않습니다. 크롬(Chrome)을 사용해 주세요.");
        }
    }
    </script>
    """, unsafe_allow_html=True)

def tts(text: str):
    """AI 답변을 음성으로 출력"""
    clean_text = re.sub(r'[*#_~]', '', text) # 특수문자 제거
    safe_text = json.dumps(clean_text.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_text});</script>", height=0)

# =========================
# [3] 데이터 로딩 (슬래시 관련 완전 삭제)
# =========================
@st.cache_data
def load_math_data():
    all_data = {}
    semesters = ["중1-1", "중1-2", "중2-1", "중2-2", "중3-1", "중3-2"]
    for sem in semesters:
        file_path = f"{sem}수학.txt"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    parsed = []
                    for line in f:
                        # [선생님 요청]: 슬래시 관련 모든 명령 삭제 및 안전 처리
                        clean_line = line.strip().replace("\\", "")
                        if not clean_line or "소단원명" in clean_line: continue
                        parts = clean_line.split("\t")
                        if len(parts) >= 3:
                            parsed.append({"unit": parts[0].strip(), "q": parts[1].strip(), "a": parts[2].strip()})
                    if parsed: all_data[sem] = parsed
            except: continue
    return all_data

MATH_DB = load_math_data()

# =========================
# [4] 인공지능 호출 (에러 수정판)
# =========================
def call_gemini(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(API_URL, json=payload, timeout=20)
        res = r.json()
        if "error" in res:
            return f"⚠️ AI 서버 에러: {res['error']['message']}"
        return res["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"⚠️ 연결 오류: {str(e)}"

# =========================
# [5] 앱 상태 관리 및 화면 로직
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

# --- 1단계: 접속 보안 ---
if st.session_state.step == "auth":
    st.title("🔒 AI 수학 구술감독관")
    pw = st.text_input("학원 비밀번호", type="password")
    if st.button("시스템 접속"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 2단계: 학생 설정 ---
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    name = st.text_input("학생 이름을 입력하세요")
    if not MATH_DB:
        st.error("데이터 파일을 찾을 수 없습니다.")
        st.stop()
    sem = st.selectbox("학기 선택", list(MATH_DB.keys()))
    units = sorted(list(set(d["unit"] for d in MATH_DB[sem])))
    unit = st.selectbox("소단원 선택", units)
    
    if st.button("테스트 시작"):
        if name:
            st.session_state.user_name = name
            st.session_state.sel_unit = unit
            qs = [d for d in MATH_DB[sem] if d["unit"] == unit]
            random.shuffle(qs)
            st.session_state.questions = qs[:10]
            st.session_state.step = "test"
            
            # 첫 인사
            intro = f"안녕 {name}! {unit} 테스트를 시작할게. Q1. {st.session_state.questions[0]['q']}"
            st.session_state.messages.append({"role": "assistant", "content": intro})
            st.rerun()
        else:
            st.warning("이름을 입력해 주세요.")
    st.stop()

# --- 3단계: 구술 시험 진행 (채팅) ---
if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit} 테스트")

    # 마이크 버튼 (음성 인식)
    if st.button("🎤 마이크 켜기 (말하기 시작)"):
        st.components.v1.html("<script>window.parent.startListening();</script>", height=0)
        st.info("지금 말씀하세요! 다 말씀하신 후 알림창을 확인해 주세요.")

    # 대화 기록 표시
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # 입력창 (엔터 키 문제 해결을 위해 위치 고정)
    if prompt := st.chat_input("여기에 답을 입력하고 엔터를 치세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        curr_q = st.session_state.questions[st.session_state.q_idx]
        
        # 채점 프롬프트
        ai_prompt = f"""
        너는 다정한 수학 선생님이야. 
        문제: {curr_q['q']}
        정답: {curr_q['a']}
        학생 답: {prompt}
        
        맞으면 칭찬하고 다음 질문으로 넘어가자고 해. 
        틀리면 정답을 말하지 말고 힌트를 줘. 
        수식은 반드시 한글로 ('루트 2', 'x의 제곱') 표현해줘.
        """
        
        with st.spinner("선생님 채점 중..."):
            reply = call_gemini(ai_prompt)
            
        st.session_state.messages.append({"role": "assistant", "content": reply})
        tts(reply)
        
        # 정답 여부에 따른 문제 전환
        if "정답" in reply[:20] or "맞았어" in reply:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제! Q{st.session_state.q_idx + 1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
        
        st.rerun() # 화면 갱신을 통해 다음 질문 표시 및 입력창 활성화
