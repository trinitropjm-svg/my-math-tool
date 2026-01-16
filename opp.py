import streamlit as st
import requests
import random
import os
import re
import json

# =========================
# [1] 선생님 필수 설정
# =========================
# ※ 주의: 여기에 선생님의 실제 API 키를 정확히 입력해 주세요.
API_KEY = "AIzaSyChQxUSqXF6jJ7fDpESBXl4gW9wdp86Waw".strip()
TEACHER_PASSWORD = "1234" 

# =========================
# [2] 모델 자동 탐색 기능 (안정화 패치)
# =========================
@st.cache_resource
def find_available_model(api_key):
    """선생님의 키로 사용 가능한 최적의 모델을 자동으로 찾습니다."""
    # 1순위: v1beta flash, 2순위: v1 flash, 3순위: 최신 flash
    urls = [
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
    ]
    
    for url in urls:
        try:
            res = requests.get(url, timeout=5).json()
            if "models" in res:
                # 'flash'가 포함된 모델 중 가장 최신 것을 찾음
                flash_models = [m["name"] for m in res["models"] if "flash" in m["name"].lower()]
                if flash_models:
                    # 'v1beta' 주소였으면 v1beta 엔드포인트 반환, 아니면 v1 반환
                    version = "v1beta" if "v1beta" in url else "v1"
                    model_path = flash_models[0] # 예: models/gemini-1.5-flash
                    return f"https://generativelanguage.googleapis.com/{version}/{model_path}:generateContent?key={api_key}"
        except:
            continue
    # 최후의 수단 (기본값)
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

# 최적의 API 주소 자동 설정
FINAL_API_URL = find_available_model(API_KEY)

# =========================
# [3] UI + 음성(TTS/STT) + 보안
# =========================
st.set_page_config(page_title="중등수학 AI 감독관", layout="centered")

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
            alert("🎤 인식 내용: " + transcript + "\\n\\n확인 후 입력창에 적고 엔터를 쳐주세요!");
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
# [4] 데이터 로더 (무결성 유지)
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
# [5] 앱 화면 로직
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

if st.session_state.step == "auth":
    st.title("🔒 AI 수학 구술감독관")
    st.info(f"시스템 진단: 연결 주소 자동 최적화 완료")
    pw = st.text_input("접속 비밀번호 (1234)", type="password")
    if st.button("접속하기"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else: st.error("비밀번호 불일치")
    st.stop()

if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    name = st.text_input("학생 이름")
    if not MATH_DB: st.error("데이터 파일이 없습니다."); st.stop()
    sem = st.selectbox("학기", list(MATH_DB.keys()))
    units = sorted(list(set(d["unit"] for d in MATH_DB[sem])))
    unit = st.selectbox("소단원", units)
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
    st.stop()

if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit} 테스트")
    if st.button("🎤 마이크 켜기 (말하기)"):
        st.components.v1.html("<script>window.parent.startListening();</script>", height=0)

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("정답을 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        curr_q = st.session_state.questions[st.session_state.q_idx]
        
        payload = {
            "contents": [{"parts": [{"text": f"수학 선생님으로서 채점해줘. 문제: {curr_q['q']}, 정답: {curr_q['a']}, 학생답: {prompt}. 맞으면 칭찬하고 다음 문제로 가고, 틀리면 힌트만 줘. 수식은 한글로 말해줘."}]}],
            "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
        }
        
        try:
            r = requests.post(FINAL_API_URL, json=payload, timeout=15)
            res = r.json()
            if "error" in res:
                reply = f"❌ API 에러: {res['error']['message']}"
            else:
                reply = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            reply = f"❌ 시스템 오류: {str(e)}"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        tts(reply)
        
        if "정답" in reply[:25] or "맞았" in reply or "훌륭" in reply:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제! Q{st.session_state.q_idx+1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
        st.rerun()

