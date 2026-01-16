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
# ※ 주의: 여기에 선생님의 실제 API 키를 입력해 주세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
TEACHER_PASSWORD = "1234" 

# =========================
# [2] 모델 자동 탐색 기능
# =========================
@st.cache_resource
def get_best_model(api_key):
    """사용 가능한 최신 모델을 자동으로 찾아 반환합니다."""
    candidates = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        res = requests.get(url, timeout=5).json()
        if "models" in res:
            available = [m["name"].split("/")[-1] for m in res["models"]]
            for cand in candidates:
                if cand in available: return cand
            for m in available:
                if "flash" in m: return m
    except: pass
    return "gemini-1.5-flash"

ACTIVE_MODEL = get_best_model(API_KEY)
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{ACTIVE_MODEL}:generateContent?key={API_KEY}"

# =========================
# [3] UI + 음성(TTS/STT) 설정
# =========================
st.set_page_config(page_title="AI 수학 구술감독관", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    <script>
    function speak(text) {
        window.speechSynthesis.cancel();
        const msg = new SpeechSynthesisUtterance();
        msg.text = text;
        msg.lang = 'ko-KR';
        msg.rate = 1.1;
        window.speechSynthesis.speak(msg);
    }
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
    clean_text = re.sub(r'[*#_~]', '', text)
    safe_text = json.dumps(clean_text.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_text});</script>", height=0)

# =========================
# [4] 데이터 로더 (여기가 에러 지점입니다. 끝까지 복사 확인!)
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

# [에러 해결] 함수 이름인 load_math_data()가 끝까지 다 써졌는지 꼭 확인하세요!
MATH_DB = load_math_data()

# =========================
# [5] 앱 상태 및 화면 로직
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

# 1. 로그인
if st.session_state.step == "auth":
    st.title("🔒 운영자 모드 접속")
    st.write(f"현재 시스템 모델: `{ACTIVE_MODEL}`")
    pw = st.text_input("접속 비밀번호 (1234)", type="password")
    if st.button("접속하기"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# 2. 초기 설정
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    name = st.text_input("학생 이름을 입력하세요")
    if not MATH_DB:
        st.error("데이터 파일을 찾을 수 없습니다.")
        st.stop()
    sem = st.selectbox("학기 선택", list(MATH_DB.keys()))
    units = sorted(list(set(d["unit"] for d in MATH_DB[sem])))
    unit = st.selectbox("소단원 선택", units)
    
    if st.button("시험 시작"):
        if name:
            st.session_state.user_name = name
            st.session_state.sel_unit = unit
            qs = [d for d in MATH_DB[sem] if d["unit"] == unit]
            random.shuffle(qs)
            st.session_state.questions = qs[:10]
            st.session_state.step = "test"
            msg = f"안녕 {name}! {unit} 테스트를 시작할게. Q1. {st.session_state.questions[0]['q']}"
            st.session_state.messages.append({"role": "assistant", "content": msg})
            st.rerun()
        else:
            st.warning("이름을 입력해 주세요.")
    st.stop()

# 3. 메인 시험
if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit}")
    if st.button("🎤 마이크 켜기"):
        st.components.v1.html("<script>window.parent.startListening();</script>", height=0)

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("정답을 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        curr_q = st.session_state.questions[st.session_state.q_idx]
        ai_prompt = f"수학 선생님으로서 채점해줘. 문제: {curr_q['q']}, 정답: {curr_q['a']}, 학생답: {prompt}. 맞으면 칭찬하고 다음 문제로 가고, 틀리면 힌트만 줘. 수식은 한글로 말해줘."
        
        try:
            r = requests.post(API_URL, json={"contents": [{"parts": [{"text": ai_prompt}]}]}, timeout=15)
            reply = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except:
            reply = "잠시 연결이 불안정해. 다시 말해줄래?"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        tts(reply)
        
        if "정답" in reply[:25] or "맞았" in reply:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제! Q{st.session_state.q_idx + 1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
            else:
                st.session_state.step = "report"
        st.rerun()

# 4. 결과 리포트
if st.session_state.step == "report":
    st.balloons()
    st.title("📋 테스트 종료")
    st.success(f"{st.session_state.user_name} 학생, 고생 많았어! 선생님께 이 화면을 보여드려.")
    if st.button("처음으로 돌아가기"):
        st.session_state.clear()
        st.rerun()
