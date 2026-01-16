import streamlit as st
import requests
import random
import os
import re
import json

# =========================
# [1] 선생님 필수 설정
# =========================
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
TEACHER_PASSWORD = "1234" 

# 구글 v1 API 경로 (안정적)
API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

# =========================
# [2] UI + 음성 시스템 (TTS/STT 통합 강화)
# =========================
st.set_page_config(page_title="중등수학 AI 감독관", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    .mic-info { color: #2e7d32; font-weight: bold; background-color: #e8f5e9; padding: 10px; border-radius: 5px; }
    </style>
    <script>
    // 1. 목소리 출력 (TTS) - 목소리를 더 선생님답게 설정
    function speak(text) {
        window.speechSynthesis.cancel(); // 기존 목소리 중단
        const msg = new SpeechSynthesisUtterance();
        msg.text = text;
        msg.lang = 'ko-KR';
        msg.rate = 1.0;  // 말하기 속도 (1.0이 보통)
        msg.pitch = 1.0; // 목소리 톤
        window.speechSynthesis.speak(msg);
    }

    // 2. 음성 인식 (STT)
    let recognition;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.lang = 'ko-KR';
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            alert("🎤 인식 결과: " + transcript + "\\n\\n입력창에 적고 엔터를 쳐주세요!");
        };
    }
    function startListening() {
        if(recognition) recognition.start();
        else alert("브라우저가 음성 인식을 지원하지 않습니다.");
    }
    </script>
    """, unsafe_allow_html=True)

def tts(text: str):
    """AI 답변을 실제 목소리로 출력하는 함수"""
    # 불필요한 특수문자 제거
    clean_text = re.sub(r'[*#_~]', '', text)
    safe_text = json.dumps(clean_text.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_text});</script>", height=0)

# =========================
# [3] 데이터 로더
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
                        clean = line.strip().replace("\\", "")
                        if not clean or "소단원명" in clean: continue
                        parts = clean.split("\t")
                        if len(parts) >= 3:
                            parsed.append({"unit": parts[0].strip(), "q": parts[1].strip(), "a": parts[2].strip()})
                    if parsed: all_data[sem] = parsed
            except: continue
    return all_data

MATH_DB = load_math_data()

# =========================
# [4] 화면 로직
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

# 1단계: 로그인
if st.session_state.step == "auth":
    st.title("🔒 AI 수학 구술감독관")
    pw = st.text_input("접속 비밀번호", type="password")
    if st.button("접속하기"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else: st.error("비밀번호 불일치")
    st.stop()

# 2단계: 설정
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    name = st.text_input("학생 이름")
    if not MATH_DB: st.error("파일 없음"); st.stop()
    sem = st.selectbox("학기", list(MATH_DB.keys()))
    units = sorted(list(set(d["unit"] for d in MATH_DB[sem])))
    unit = st.selectbox("소단원", units)
    
    if st.button("시험 시작 (목소리 켜짐)"):
        if name:
            st.session_state.user_name = name
            st.session_state.sel_unit = unit
            qs = [d for d in MATH_DB[sem] if d["unit"] == unit]
            random.shuffle(qs)
            st.session_state.questions = qs[:10]
            st.session_state.step = "test"
            
            # 첫 질문 생성 및 소리 출력 트리거
            first_q = st.session_state.questions[0]['q']
            intro = f"안녕 {name}! {unit} 테스트를 시작할게. 첫 번째 문제야. {first_q}"
            st.session_state.messages.append({"role": "assistant", "content": intro})
            st.rerun()
    st.stop()

# 3단계: 시험 진행
if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit}")

    # 소리 안 나올 때 클릭 유도 및 마이크 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔊 목소리 다시 듣기"):
            tts(st.session_state.messages[-1]["content"])
    with col2:
        if st.button("🎤 마이크 켜기"):
            st.components.v1.html("<script>window.parent.startListening();</script>", height=0)

    # 대화창 렌더링
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    # 화면에 처음 들어왔을 때 첫 질문 읽어주기 (딱 한 번 실행)
    if len(st.session_state.messages) == 1:
        tts(st.session_state.messages[0]["content"])

    if prompt := st.chat_input("정답을 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        curr_q = st.session_state.questions[st.session_state.q_idx]
        
        # AI 호출
        payload = {"contents": [{"parts": [{"text": f"수학 선생님으로서 채점해줘. 문제: {curr_q['q']}, 정답: {curr_q['a']}, 학생답: {prompt}. 맞으면 칭찬하고 다음 문제로 가자고 하고, 틀리면 힌트만 줘. 수식은 한글로 말해줘."}]}]}
        try:
            r = requests.post(API_URL, json=payload, timeout=15)
            reply = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except:
            reply = "연결이 잠시 끊겼어. 다시 말해볼래?"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        
        # 정답이면 다음 문제 번호 증가
        if "정답" in reply[:25] or "맞았" in reply:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제! Q{st.session_state.q_idx+1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
        
        st.rerun()

    # 채팅이 업데이트될 때마다 마지막 assistant 메시지 읽어주기
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        tts(st.session_state.messages[-1]["content"])
