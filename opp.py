import streamlit as st
import requests

# --- [1단계] 설정 (비밀번호만 넣어주세요) ---
API_KEY = "선생님의_진짜_열쇠".strip()
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

# --- [2단계] 6개 학기별 비밀 지시서 (선생님이 만드신 Gem 내용을 여기에 넣으세요) ---
# 아래 따옴표 안에 각 학기별 핵심 내용을 요약해서 넣으시면 됩니다.
INSTRUCTIONS = {
    "중1-1 (수와 연산, 문자와 식)": "너는 중1-1 수학 선생님이야. 소인수분해, 정수와 유리수 위주로 질문해줘.",
    "중1-2 (도형, 통계)": "너는 중1-2 수학 선생님이야. 점, 선, 면과 입체도형 위주로 질문해줘.",
    "중2-1 (식의 계산, 부등식)": "너는 중2-1 수학 선생님이야. 유리수와 순환소수, 연립방정식 위주로 질문해줘.",
    "중2-2 (도형의 성질, 확률)": "너는 중2-2 수학 선생님이야. 삼각형과 사각형의 성질, 확률 위주로 질문해줘.",
    "중3-1 (제곱근, 이차함수)": "너는 중3-1 수학 선생님이야. 제곱근과 실수, 이차방정식 위주로 질문해줘.",
    "중3-2 (삼각비, 원의 성질)": "너는 중3-2 수학 선생님이야. 삼각비와 원의 성질 위주로 질문해줘."
}

# --- [3단계] 화면 UI 구성 ---
st.set_page_config(page_title="중등수학 학기별 도우미", page_icon="📐")
st.title("📐 중등수학 학기별 예습 진단")

# 사이드바에서 학기 선택하기
st.sidebar.title("학기 선택")
selected_semester = st.sidebar.selectbox("지금 공부하는 학기를 골라주세요:", list(INSTRUCTIONS.keys()))
current_instruction = INSTRUCTIONS[selected_semester]

# 학기가 바뀌면 대화 내용 초기화하기 (선택 사항)
if "last_semester" not in st.session_state or st.session_state.last_semester != selected_semester:
    st.session_state.messages = []
    st.session_state.last_semester = selected_semester

st.sidebar.info(f"현재 모드: {selected_semester}")

# --- [4단계] 대화 저장 및 표시 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- [5단계] 대화하기 ---
if prompt := st.chat_input("질문을 입력하거나 공부한 내용을 말해주세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 구글 서버로 보낼 편지 구성
    payload = {
        "contents": [{
            "parts": [{"text": f"지시사항: {current_instruction}\n\n학생 질문: {prompt}"}]
        }]
    }

    try:
        response = requests.post(API_URL, json=payload)
        result = response.json()
        
        if "candidates" in result:
            answer = result["candidates"][0]["content"]["parts"][0]["text"]
            with st.chat_message("assistant"):
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            st.error("인공지능과 연결에 문제가 생겼습니다. API 키를 확인해주세요.")
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

