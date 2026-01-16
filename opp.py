import streamlit as st
import requests
import random
import os
import re
import json
from datetime import datetime

# =========================
# [1] 선생님 필수 설정
# =========================
# 여기에 선생님의 실제 Gemini API 키를 넣어주세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0" 
TEACHER_PASSWORD = "1234" 

MODEL = "gemini-1.5-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}"

# =========================
# [2] UI + 보안 + 음성(TTS & STT) 통합 설정
# =========================
st.set_page_config(page_title="중등수학 AI 감독관", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    .stChatFloatingInputContainer {padding-bottom: 20px;}
    </style>
    <script>
    // AI 목소리 출력 (TTS)
    function speak(text) {
        window.speechSynthesis.cancel();
        const msg = new SpeechSynthesisUtterance();
        msg.text = text;
        msg.lang = 'ko-KR';
        msg.rate = 1.1;
        window.speechSynthesis.speak(msg);
    }

    // 학생 목소리 인식 (STT) - 브라우저 기능 사용
    let recognition;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.lang = 'ko-KR';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onresult = function(event) {
            const result = event.results[0][0].transcript;
            // 텍스트를 입력창에 넣는 대신 알림으로 표시 (학생이 확인 후 입력창에 기입 유도)
            alert("인식된 내용: " + result + "\\n\\n이 내용을 입력창에 적거나 '그대로 입력' 버튼을 눌러주세요.");
        };
    }

    function startListening() {
        if (recognition) recognition.start();
        else alert("이 브라우저는 음성 인식을 지원하지 않습니다. 크롬을 사용해 주세요.");
    }
    </script>
    """, unsafe_allow_html=True)

def tts(text: str):
    clean_text = re.sub(r'[*#_~]', '', text)
    safe_json = json.dumps(clean_text.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_json});</script>", height=0)

# =========================
# [3] 데이터 로딩 (중략 없음)
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
                        # 슬래시 에러 방지를 위한 안전한 처리
                        parts = line.strip().replace("\\", "").split("\t")
                        if len(parts) >= 3:
                            parsed.append({"unit": parts[0].strip(), "q": parts[1].strip(), "a": parts[2].strip()})
                    if parsed: all_data[sem] = parsed
            except: continue
    return all_data

MATH_DB = load_math_data()

def call_gemini(api_key, prompt):
    url = API_URL.format(MODEL, api_key)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=20)
        return r.json()["candidates"][0]["content"]["parts"][0]['text'].strip()
    except: return "선생님이 잠시 자리를 비웠나 봐. 다시 말해줄래?"

# =========================
# [4] 화면 로직 (Step by Step)
# =========================

if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

# 1단계: 로그인
if st.session_state.step == "auth":
    st.title("🔒 AI 수학 구술감독관")
    pw = st.text_input("학원 비밀번호", type="password")
    if pw == TEACHER_PASSWORD:
        if st.button("시스템 접속"):
            st.session_state.step = "init"
            st.rerun()
    st.stop()

# 2단계: 설정
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    st.session_state.user_name = st.text_input("학생 이름")
    if MATH_DB:
        st.session_state.sel_sem = st.selectbox("학기 선택", list(MATH_DB.keys()))
        units = sorted(list(set(d["unit"] for d in MATH_DB[st.session_state.sel_sem])))
        st.session_state.sel_unit = st.selectbox("소단원 선택", units)
        if st.button("시험 시작"):
            qs = [d for d in MATH_DB[st.session_state.sel_sem] if d["unit"] == st.session_state.sel_unit]
            random.shuffle(qs)
            st.session_state.questions = qs[:10]
            st.session_state.step = "test"
            msg = f"반가워 {st.session_state.user_name}! {st.session_state.sel_unit} 테스트를 시작할게. Q1. {st.session_state.questions[0]['q']}"
            st.session_state.messages.append({"role": "assistant", "content": msg})
            st.rerun()
    st.stop()

# 3단계: 시험 진행
if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit}")

    # 마이크 버튼 (STT)
    if st.button("🎤 목소리로 대답하기 (누르고 말씀하세요)"):
        st.components.v1.html("<script>window.parent.startListening();</script>", height=0)

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("여기에 답을 적어주세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
            
        curr_q = st.session_state.questions[st.session_state.q_idx]
        
        # AI 지시사항
        instruction = f"너는 다정한 수학 선생님이야. 학생의 답 '{prompt}'이 문제 '{curr_q['q']}'(정답: {curr_q['a']})에 대해 맞는지 확인해줘. 틀리면 힌트만 주고 수식은 한글로 풀어서 말해줘."
        
        ai_reply = call_gemini(API_KEY, instruction)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        with st.chat_message("assistant"): st.markdown(ai_reply)
        tts(ai_reply)
        
        # 정답이면 다음 문제로
        if "정답" in ai_reply[:15]:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"다음 문제! Q{st.session_state.q_idx+1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
                st.rerun()
            else:
                st.session_state.step = "report"
                st.rerun()

# 4단계: 결과
if st.session_state.step == "report":
    st.balloons()
    st.title("📋 테스트 종료")
    st.success(f"{st.session_state.user_name} 학생, 수고했어! 오늘 테스트를 모두 마쳤어.")
    if st.button("처음으로 돌아가기"):
        st.session_state.clear()
        st.rerun()
