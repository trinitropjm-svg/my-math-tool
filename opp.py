import streamlit as st
import requests
import random
import os
import re
import json

# =========================
# [1] 보안 설정 (Secrets 사용)
# =========================
API_KEY = st.secrets.get("GOOGLE_API_KEY", "").strip()
TEACHER_PASSWORD = "1234" 

# =========================
# [2] 모델 자동 탐색 기능
# =========================
@st.cache_resource
def find_available_model(api_key):
    if not api_key: return ""
    urls = [
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=5).json()
            if "models" in res:
                flash_models = [m["name"] for m in res["models"] if "flash" in m["name"].lower()]
                if flash_models:
                    version = "v1beta" if "v1beta" in url else "v1"
                    return f"https://generativelanguage.googleapis.com/{version}/{flash_models[0]}:generateContent?key={api_key}"
        except: continue
    return ""

FINAL_API_URL = find_available_model(API_KEY)

# =========================
# [3] UI + 음성(TTS) 시스템 보강
# =========================
st.set_page_config(page_title="AI 수학 구술감독관", layout="centered")

# JavaScript: 브라우저 소리 잠금 해제 및 재생 기능
st.markdown("""
    <script>
    let synth = window.speechSynthesis;
    
    function speak(text) {
        if (!text) return;
        synth.cancel(); // 기존 음성 중단
        const msg = new SpeechSynthesisUtterance();
        msg.text = text;
        msg.lang = 'ko-KR';
        msg.rate = 1.0;
        msg.pitch = 1.0;
        synth.speak(msg);
    }
    
    // 사용자가 버튼을 누를 때 호출하여 소리 권한 획득
    function unlockAudio() {
        speak("음성 시스템이 준비되었습니다.");
    }
    </script>
    """, unsafe_allow_html=True)

def tts(text: str):
    """AI 답변을 목소리로 출력하는 함수"""
    clean = re.sub(r'[*#_~]', '', text)
    safe_text = json.dumps(clean.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_text});</script>", height=0)

# =========================
# [4] 데이터 로더
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
# [5] 화면 로직
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

# 1단계: 로그인
if st.session_state.step == "auth":
    st.title("🔒 AI 수학 구술감독관")
    if not API_KEY:
        st.error("⚠️ Secrets에 API 키를 등록해 주세요.")
    pw = st.text_input("접속 비밀번호", type="password")
    if st.button("접속하기"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else: st.error("비밀번호 불일치")
    st.stop()

# 2단계: 설정 및 음성 활성화
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    st.warning("🔈 시험 시작 전, 아래 '음성 활성화' 버튼을 먼저 꼭 눌러주세요!")
    
    if st.button("🔊 음성 시스템 시작 (클릭 필수)"):
        st.components.v1.html("<script>window.parent.unlockAudio();</script>", height=0)

    name = st.text_input("학생 이름")
    sem = st.selectbox("학기 선택", list(MATH_DB.keys()) if MATH_DB else ["파일 없음"])
    if not MATH_DB: st.stop()
    unit = st.selectbox("소단원 선택", sorted(list(set(d["unit"] for d in MATH_DB[sem]))))
    
    if st.button("테스트 시작"):
        if name:
            st.session_state.user_name = name
            st.session_state.sel_unit = unit
            qs = [d for d in MATH_DB[sem] if d["unit"] == unit]
            random.shuffle(qs)
            st.session_state.questions = qs[:10]
            st.session_state.step = "test"
            msg = f"안녕 {name}! {unit} 테스트를 시작할게. 첫 번째 질문이야. {st.session_state.questions[0]['q']}"
            st.session_state.messages.append({"role": "assistant", "content": msg})
            st.rerun()
    st.stop()

# 3단계: 테스트 진행
if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit}")
    
    # 음성 다시 듣기 버튼
    if st.button("🔊 목소리 다시 듣기"):
        tts(st.session_state.messages[-1]["content"])

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("정답을 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        curr_q = st.session_state.questions[st.session_state.q_idx]
        
        payload = {"contents": [{"parts": [{"text": f"수학 선생님으로서 채점해줘. 문제: {curr_q['q']}, 정답: {curr_q['a']}, 학생답: {prompt}. 맞으면 칭찬하고 다음 문제로 가고, 틀리면 힌트를 줘. 수식은 한글로 말해줘."}]}]}
        
        try:
            r = requests.post(FINAL_API_URL, json=payload, timeout=15)
            res = r.json()
            reply = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        except:
            reply = "연결이 잠시 끊겼어. 다시 말해볼래?"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        tts(reply)
        
        if "정답" in reply[:25] or "맞았" in reply:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제! Q{st.session_state.q_idx+1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
        st.rerun()
