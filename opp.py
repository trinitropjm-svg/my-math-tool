import streamlit as st
import requests
import random
import os
import re
import json

# =========================
# [1] 선생님 필수 설정
# =========================
# ※ 주의: 여기에 선생님의 API 키를 정확히 붙여넣으세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0" 
TEACHER_PASSWORD = "1234" 

MODEL = "gemini-1.5-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}"

# =========================
# [2] UI 및 음성 설정
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
    </script>
    """, unsafe_allow_html=True)

def tts(text: str):
    clean_text = re.sub(r'[*#_~]', '', text)
    safe_json = json.dumps(clean_text.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_json});</script>", height=0)

# =========================
# [3] 데이터 로딩
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
                        parts = line.strip().replace("\\", "").split("\t")
                        if len(parts) >= 3:
                            parsed.append({"unit": parts[0].strip(), "q": parts[1].strip(), "a": parts[2].strip()})
                    if parsed: all_data[sem] = parsed
            except: continue
    return all_data

MATH_DB = load_math_data()

# =========================
# [4] Gemini 호출 (에러 진단 기능 강화)
# =========================
def call_gemini(api_key, prompt):
    url = API_URL.format(MODEL, api_key)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [ # 안전 필터로 인해 답변이 막히는 것을 방지
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    try:
        r = requests.post(url, json=payload, timeout=20)
        res = r.json()
        
        # 실제 서버 에러가 있을 경우 에러 메시지 반환
        if "error" in res:
            return f"⚠️ API 에러 발생: {res['error']['message']}"
        
        # 답변이 필터링되었을 경우
        if "candidates" not in res or not res["candidates"][0].get("content"):
             return "⚠️ AI가 답변을 거부했습니다. (안전 필터 작동 가능성)"
             
        return res["candidates"][0]["content"]["parts"][0]['text'].strip()
    except Exception as e:
        return f"⚠️ 연결 오류 발생: {str(e)}"

# =========================
# [5] 화면 로직
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

if st.session_state.step == "auth":
    st.title("🔒 AI 수학 구술감독관")
    pw = st.text_input("학원 비밀번호", type="password")
    if pw == TEACHER_PASSWORD:
        if st.button("시스템 접속"):
            st.session_state.step = "init"
            st.rerun()
    st.stop()

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

if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit}")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("답을 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
            
        curr_q = st.session_state.questions[st.session_state.q_idx]
        
        # 프롬프트 구성
        instruction = f"""
        너는 다정한 수학 선생님이야. 
        학생의 답: {prompt}
        문제: {curr_q['q']}
        정답: {curr_q['a']}
        
        학생의 답이 맞는지 채점하고, 틀렸다면 친절한 힌트를 줘. 
        수식은 반드시 'x의 제곱' 같이 한글로만 말해줘.
        """
        
        ai_reply = call_gemini(API_KEY, instruction)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        with st.chat_message("assistant"): st.markdown(ai_reply)
        tts(ai_reply)
        
        # 에러가 아닌 경우에만 정답 판정 진행
        if "⚠️" not in ai_reply and "정답" in ai_reply[:20]:
            st.session_state.q_idx += 1
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제! Q{st.session_state.q_idx+1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
                st.rerun()
