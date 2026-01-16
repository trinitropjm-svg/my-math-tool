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
# [2] 모델 자동 탐색 기능 (안정화 패치)
# =========================
@st.cache_resource
def get_best_model(api_key):
    """사용 가능한 최신 모델을 자동으로 찾아 반환합니다."""
    # 후보 모델 리스트 (최신순)
    candidates = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        res = requests.get(url, timeout=5).json()
        
        if "models" in res:
            available = [m["name"].split("/")[-1] for m in res["models"]]
            # 후보 중 사용 가능한 첫 번째 모델 선택
            for cand in candidates:
                if cand in available:
                    return cand
            # 후보에 없으면 목록 중 첫 번째 flash 모델이라도 선택
            for m in available:
                if "flash" in m: return m
    except:
        pass
    return "gemini-1.5-flash"  # 기본값

# 모델 확정
ACTIVE_MODEL = get_best_model(API_KEY)
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{ACTIVE_MODEL}:generateContent?key={API_KEY}"

# =========================
# [3] UI + 음성(TTS/STT) + 보안
# =========================
st.set_page_config(page_title="AI 수학 구술감독관", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    .mic-btn { background-color: #ff4b4b; color: white; border-radius: 20px; padding: 10px 20px; border: none; cursor: pointer; }
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

    // 2. 음성 인식 (STT) - 마이크 기능 (인식 후 입력창 강제 주입)
    let recognition;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.lang = 'ko-KR';
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            // 스트림릿 텍스트 입력창을 찾아 값을 넣고 이벤트를 발생시킴
            const textArea = window.parent.document.querySelector('textarea[aria-label="답변을 입력하고 엔터를 치세요"]');
            if (textArea) {
                textArea.value = transcript;
                textArea.dispatchEvent(new Event('input', { bubbles: True }));
            }
            alert("🎤 인식 결과: " + transcript + "\\n\\n입력창에 자동 입력되었습니다. 엔터를 눌러주세요!");
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
# [4] 데이터 로더 (안전 모드)
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
# [5] 앱 화면 흐름
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

# 1. 로그인
if st.session_state.step == "auth":
    st.title("🔒 운영자 모드 접속")
    st.info(f"시스템 현재 활성 모델: {ACTIVE_MODEL}")
    pw = st.text_input("비밀번호", type="password")
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
    name = st.text_input("학생 이름")
    sem = st.selectbox("학기", list(MATH_DB.keys()) if MATH_DB else ["데이터 없음"])
    if not MATH_DB: st.stop()
    
    units = sorted(list(set(d["unit"] for d in MATH_DB[sem])))
    unit = st.selectbox("단원", units)
    
    if st.button("테스트 시작"):
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

# 3. 메인 시험 (마이크 및 엔터 키 최적화)
if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit}")

    if st.button("🎤 마이크 켜기"):
        st.components.v1.html("<script>window.parent.startListening();</script>", height=0)

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    # 입력창 (라벨을 스크립트와 일치시킴)
    if prompt := st.chat_input("답변을 입력하고 엔터를 치세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        curr_q = st.session_state.questions[st.session_state.q_idx]
        ai_prompt = f"수학 선생님으로서 학생답 '{prompt}'을 문제 '{curr_q['q']}'(정답: {curr_q['a']})에 대해 채점해줘. 틀리면 힌트를 주고 수식은 한글로 말해줘."
        
        try:
            r = requests.post(API_URL, json={"contents": [{"parts": [{"text": ai_prompt}]}]}, timeout=15)
            reply = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except:
            reply = "잠시 연결이 끊겼어. 다시 한번 말해줄래?"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        tts(reply)
        
        if "정답" in reply[:20] or "맞았" in reply:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제! Q{st.session_state.q_idx + 1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
        
        st.rerun()
