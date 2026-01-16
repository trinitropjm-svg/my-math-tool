import streamlit as st
import google.generativeai as genai

# --- [1단계] API 키 설정 ---
# 선생님의 진짜 AIza... 키를 따옴표 안에 넣어주세요.
API_KEY = "여기에_진짜_열쇠를_넣으세요".strip()

# --- [2단계] 인공지능 연결 시도 (try-except 세트) ---
try:
    genai.configure(api_key=API_KEY)
    # 반드시 try 아래는 아래처럼 '들여쓰기(빈칸)'가 되어 있어야 합니다.
    model = genai.GenerativeModel('gemini-1.5-flash')
    
except Exception as e:
    # try와 except는 반드시 줄이 딱 맞아야 합니다!
    st.error(f"연결 중에 문제가 생겼어요: {e}")

# --- [3단계] 화면 구성 ---
st.title("📝 중등수학 예습 진단")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response = model.generate_content(prompt)
        with st.chat_message("assistant"):
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        st.error(f"대화 중 에러 발생: {e}")
# --- [4단계] 대화 진행하기 ---
if prompt := st.chat_input("공부한 내용을 입력하세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # 대화 기록을 포함하여 인공지능에게 전달
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("앗! 인공지능이 잠시 쉬고 있나 봐요. '대화 초기화' 버튼을 눌러보시거나 API 키를 확인해주세요.")

# --- [5단계] 선생님께 보낼 리포트 생성 ---
st.sidebar.divider()
if st.sidebar.button("📊 평가 리포트 생성"):
    if len(st.session_state.messages) > 0:
        with st.sidebar:
            report_res = model.generate_content("지금까지의 대화를 요약해서 선생님께 보낼 학습 리포트를 작성해줘.")
            st.code(report_res.text)
            st.write("위 내용을 복사해서 카톡으로 보내주세요!")
    else:
        st.sidebar.warning("대화 내용이 없어요.")







