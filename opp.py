import streamlit as st
import requests
import random
import os
import re
import json

# --- [1] 설정 ---
API_KEY = "선생님의_API_키_입력".strip() 
TEACHER_PASSWORD = "1234" # 학원 접속 암호

# --- [2] UI 보안 및 한국어 음성(TTS) 설정 ---
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
        msg.rate = 1.0;
        window.speechSynthesis.speak(msg);
    }
    </script>
    """, unsafe_allow_html=True)

# --- [3] 데이터 로더 (6개 학기 파일 읽기) ---
@st.cache_data
def load_math_data():
    all_semesters = {}
    files = ["중1-1", "중1-2", "중2-1", "중2-2", "중3-1", "중3-2"]
    for sem in files:
        fname = f"{sem}수학.txt"
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8") as f:
                content = f.readlines()
                qs = []
                for line in content:
                    # [에러 해결]: 역슬래시 단독 사용을 피하고 source 태그만 제거
                    line = re.sub(r"\", "", line).strip()
                    if not line or "소단원명" in line: continue
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        qs.append({"unit": parts[0].strip(), "q": parts[1].strip(), "a": parts[2].strip()})
                if qs: all_semesters[sem] = qs
    return all_semesters

MATH_DB = load_math_data()

# --- [4] 앱 상태 관리 ---
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "wrong_list" not in st.session_state: st.session_state.wrong_list = []

# --- [5] 화면 로직 ---

# 1단계: 접속 잠금
if st.session_state.step == "auth":
    st.title("🔒 AI 구술 시험 시스템")
    pw = st.text_input("학원 비밀번호", type="password")
    if st.button("시스템 접속"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else: st.error("비밀번호가 틀렸습니다.")
    st.stop()

# 2단계: 학생 이름 및 단원 선택
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    st.session_state.user_name = st.text_input("학생 이름을 입력하세요")
    st.session_state.sel_sem = st.selectbox("학기 선택", list(MATH_DB.keys()))
    
    units = sorted(list(set([d["unit"] for d in MATH_DB[st.session_state.sel_sem]])))
    st.session_state.sel_unit = st.selectbox("소단원을 골라주세요:", units)
    
    if st.button("테스트 시작"):
        st.session_state.questions = [d for d in MATH_DB[st.session_state.sel_sem] if d["unit"] == st.session_state.sel_unit]
        random.shuffle(st.session_state.questions)
        st.session_state.step = "test"
        
        # 시작 인사
        start_text = f"안녕하세요 {st.session_state.sel_sem}수학 테스트입니다. 학생 이름과 소단원을 말씀해주세요."
        st.session_state.messages.append({"role": "assistant", "content": start_text})
        st.rerun()
    st.stop()

# 3단계: 구술 시험 및 음성 지원
st.title(f"📐 {st.session_state.sel_unit} 테스트")

# 단원 리스트 표시
if len(st.session_state.messages) == 1:
    st.info(f"선택된 단원: {st.session_state.sel_unit}")
    voice_intro = "화면에 나오는 단원 중 오늘 공부한 단원 이름을 말해줘!" #
    st.components.v1.html(f"<script>window.parent.speak('{voice_intro}');</script>", height=0)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("정답을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    if prompt == "그만" or len(st.session_state.messages) > 40:
        st.session_state.step = "report"
        st.rerun()

    # 인공지능 지시사항 (선생님 프롬프트 원칙 반영)
    instruction = f"""
    너는 다정하고 전문적인 '수학 선생님'이자 '구술 시험 감독관'이야. 
    참고 데이터: {json.dumps(st.session_state.questions, ensure_ascii=False)}

    [원칙]
    1. 로봇 말투 절대 금지 ("질문을 시작합니다" 등)
    2. 수식은 반드시 'x의 제곱', '2분의 1', '루트 3'처럼 한글로만 말할 것
    3. 정답이면 크게 칭찬, 틀리면 힌트 최대 2번 주기
    4. 의학적 자문 경고 문구 절대 금지
    5. 했던 말 반복 금지
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": f"{instruction}\n\n학생 답변: {prompt}"}]}]}
    
    try:
        res = requests.post(url, json=payload).json()
        ai_reply = res['candidates'][0]['content']['parts'][0]['text']
        
        with st.chat_message("assistant"):
            st.markdown(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            # 음성 출력
            safe_text = ai_reply.replace("'", "").replace("\n", " ")
            st.components.v1.html(f"<script>window.parent.speak('{safe_text}');</script>", height=0)
    except:
        st.error("잠시 후 다시 시도해 주세요.")

# 4단계: 리포트 생성
if st.session_state.step == "report":
    st.subheader("📋 학습 결과 리포트")
    st.write(f"- 학생: {st.session_state.user_name} / 단원: {st.session_state.sel_unit}")
    st.info("리포트는 읽지 않고 마칩니다. 선생님께 보여주세요!")
    if st.button("처음으로"):
        st.session_state.clear()
        st.rerun()
