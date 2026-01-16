import streamlit as st
import requests
import random
import os
import re
import json

# =========================
# [1] 필수 설정 (선생님 확인)
# =========================
# ※ 주의: 여기에 선생님의 실제 API 키를 입력해 주세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
TEACHER_PASSWORD = "1234" 

# [해결] 선생님이 분석하신 대로 v1 정규 버전 주소를 사용합니다.
API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

# =========================
# [2] UI + 음성(TTS/STT) + 보안
# =========================
st.set_page_config(page_title="중등수학 AI 감독관", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    .mic-info { color: #ff4b4b; font-size: 0.85em; margin-bottom: 5px; font-weight: bold; }
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
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRec();
        recognition.lang = 'ko-KR';
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            alert("🎤 인식 내용: " + transcript + "\\n\\n확인 후 입력창에 적고 엔터를 쳐주세요!");
        };
        recognition.onerror = function(e) {
            alert("마이크 오류: " + e.error + "\\n주소창 옆 '자물쇠' 아이콘을 눌러 마이크 허용을 확인해주세요.");
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
    clean_text = re.sub(r'[*#_~]', '', text)
    safe_text = json.dumps(clean_text.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_text});</script>", height=0)

# =========================
# [3] 데이터 로더 (슬래시 에러 방지)
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
# [4] AI 호출 (v1 정식 버전 최적화)
# =========================
def call_gemini(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(API_URL, json=payload, timeout=20)
        res = r.json()
        if "error" in res:
            return f"⚠️ API 에러: {res['error']['message']} (상세: {res['error'].get('status')})"
        return res["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"⚠️ 시스템 오류: {str(e)}"

# =========================
# [5] 앱 상태 및 화면 흐름
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

# 1. 로그인 단계
if st.session_state.step == "auth":
    st.title("🔒 AI 수학 구술감독관")
    pw = st.text_input("접속 비밀번호", type="password")
    if st.button("접속하기"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# 2. 학생 및 단원 설정 단계
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    name = st.text_input("학생 이름")
    if not MATH_DB:
        st.error("데이터 파일을 찾을 수 없습니다. 파일명을 확인해 주세요.")
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
            
            msg = f"안녕 {name}! {unit} 테스트를 시작할게. Q1. {st.session_state.questions[0]['q']}"
            st.session_state.messages.append({"role": "assistant", "content": msg})
            st.rerun()

# 3. 메인 시험 단계
if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit}")

    st.markdown('<p class="mic-info">🎤 마이크 사용 시 주소창 왼쪽 자물쇠 아이콘을 눌러 "허용"을 확인하세요.</p>', unsafe_allow_html=True)
    if st.button("🎤 마이크 켜기 (말하기 시작)"):
        st.components.v1.html("<script>window.parent.startListening();</script>", height=0)

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("정답을 입력하고 엔터를 치세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        curr_q = st.session_state.questions[st.session_state.q_idx]
        ai_prompt = f"수학 선생님으로서 채점해줘. 문제: {curr_q['q']}, 정답: {curr_q['a']}, 학생답: {prompt}. 맞으면 칭찬하고 다음 문제로 가자고 하고, 틀리면 힌트를 줘. 수식은 한글로 말해줘."
        
        with st.spinner("AI 선생님 확인 중..."):
            reply = call_gemini(ai_prompt)
            
        st.session_state.messages.append({"role": "assistant", "content": reply})
        tts(reply)
        
        # 정답 판정 (맞았을 경우 다음 문제 준비)
        if "정답" in reply[:25] or "맞았" in reply:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제! Q{st.session_state.q_idx + 1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
        
        st.rerun()
