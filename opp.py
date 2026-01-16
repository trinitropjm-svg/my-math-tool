import streamlit as st
import requests
import random
import os
import re

# --- [1] 선생님 필수 설정 ---
# 선생님의 진짜 API 키를 따옴표 안에 넣어주세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
TEACHER_PASSWORD = "1234"  # 학원용 접속 비밀번호

# --- [2] UI 보안 잠금 및 음성 지원 설정 ---
st.set_page_config(page_title="중등수학 AI 감독관", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    <script>
    function speak(text) {
        // 이전 음성이 나오고 있다면 중지
        window.speechSynthesis.cancel();
        const msg = new SpeechSynthesisUtterance();
        msg.text = text;
        msg.lang = 'ko-KR';
        msg.rate = 1.0;
        window.speechSynthesis.speak(msg);
    }
    </script>
    """, unsafe_allow_html=True)

# --- [3] 데이터 로더: 텍스트 파일을 읽어 6개 학기 통합 ---
@st.cache_data
def load_all_data():
    all_data = {}
    semesters = ["중1-1", "중1-2", "중2-1", "중2-2", "중3-1", "중3-2"]
    
    for sem in semesters:
        file_path = f"{sem}수학.txt"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    parsed_questions = []
                    for line in lines:
                        # [문제의 44라인 수정]: 소스 표시 제거
                        # r"\" 라고 정확히 써야 에러가 안 납니다.
                        clean_line = re.sub(r"\", "", line).strip()
                        
                        if not clean_line or "소단원명" in clean_line:
                            continue
                        
                        parts = clean_line.split("\t")
                        if len(parts) >= 3:
                            parsed_questions.append({
                                "unit": parts[0].strip(),
                                "q": parts[1].strip(),
                                "a": parts[2].strip()
                            })
                    if parsed_questions:
                        all_data[sem] = parsed_questions
            except Exception as e:
                st.error(f"{file_path} 읽기 오류: {e}")
    return all_data

ALL_MATH_DATA = load_all_data()

# --- [4] 시스템 상태 관리 ---
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_count" not in st.session_state: st.session_state.q_count = 0

# --- [5] 화면 로직 ---

# [1단계: 비밀번호 잠금]
if st.session_state.step == "auth":
    st.title("🔒 AI 구술 시험 시스템")
    pw = st.text_input("수업 비밀번호를 입력하세요", type="password")
    if st.button("시스템 접속"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# [2단계: 학생 이름 및 단원 선택]
if st.session_state.step == "init":
    st.subheader("👨‍🏫 테스트 설정")
    st.session_state.user_name = st.text_input("학생 이름을 입력해주세요:")
    
    if not ALL_MATH_DATA:
        st.error("학습 데이터(.txt) 파일을 찾을 수 없습니다. 깃허브에 파일이 있는지 확인해 주세요.")
        st.stop()
        
    st.session_state.cur_sem = st.selectbox("학기 선택", list(ALL_MATH_DATA.keys()))
    
    units = sorted(list(set([d["unit"] for d in ALL_MATH_DATA[st.session_state.cur_sem]])))
    st.session_state.cur_unit = st.selectbox("소단원 선택", units)
    
    if st.button("테스트 시작"):
        st.session_state.step = "test"
        st.session_state.questions = [d for d in ALL_MATH_DATA[st.session_state.cur_sem] if d["unit"] == st.session_state.cur_unit]
        random.shuffle(st.session_state.questions)
        
        welcome_msg = f"안녕하세요 {st.session_state.user_name} 학생! {st.session_state.cur_sem} 수학 테스트입니다. {st.session_state.cur_unit} 단원을 얼마나 잘 알고 있는지 확인해 볼게. 준비됐니?"
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
        st.rerun()
    st.stop()

# [3단계: 메인 구술 테스트]
st.title(f"📐 {st.session_state.cur_unit} 구술 시험")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("답변을 입력하세요 (그만하려면 '그만')"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if prompt == "그만" or st.session_state.q_count >= 20:
        st.session_state.step = "report"
        st.rerun()

    # 인공지능 지시사항 (선생님 프롬프트)
    system_instruction = f"""
    너는 다정하고 전문적인 '수학 선생님'이야.
    - 학생 이름: {st.session_state.user_name}
    - 질문 데이터: {st.session_state.questions}
    - 규칙: 로봇 말투 금지, 수식은 한글로('루트 2' 등), 틀리면 힌트 2번 주기.
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": f"{system_instruction}\n학생 답변: {prompt}"}]}]}
    
    try:
        res = requests.post(url, json=payload).json()
        ai_reply = res['candidates'][0]['content']['parts'][0]['text']
        
        with st.chat_message("assistant"):
            st.markdown(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            st.session_state.q_count += 1
            # 음성 출력 (따옴표 에러 방지 처리)
            safe_reply = ai_reply.replace("'", "").replace("\n", " ")
            st.components.v1.html(f"<script>window.parent.speak('{safe_reply}');</script>", height=0)
    except:
        st.error("AI 선생님과 연결이 잠시 끊겼습니다. 다시 시도해 주세요.")

# [4단계: 리포트 생성]
if st.session_state.step == "report":
    st.balloons()
    st.subheader("📋 학습 리포트")
    st.write(f"- **학생 이름**: {st.session_state.user_name}")
    st.write(f"- **학습 단원**: {st.session_state.cur_sem} {st.session_state.cur_unit}")
    st.info("오늘 테스트 받느라 수고했어! 선생님께 이 화면을 보여드리면 돼.")


