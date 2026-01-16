import streamlit as st
import google.generativeai as genai

# --- [1단계] API 키 설정 (선생님의 진짜 키를 넣어주세요) ---
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0"

try:
    genai.configure(api_key=API_KEY)
    # 모델 이름을 가장 기본형인 'gemini-1.5-flash'로 설정합니다.
   # 'models/'를 빼고 이름만 적어주는 것이 현재 버전에서 더 정확할 수 있습니다.
model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"설정 단계 에러: {e}")

# --- [2단계] 화면 구성 ---
st.title("📝 중등수학 예습 진단")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- [3단계] 대화 및 진짜 에러 표시 ---
if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # 질문을 던집니다.
        response = model.generate_content(prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
    except Exception as e:
        # 앗! 에러가 나면 이제 '쉬고 있다'는 말 대신 진짜 이유를 보여줍니다.
        st.error("🚨 에러가 발생했습니다! 아래 내용을 알려주세요:")
        st.error(f"내용: {e}")
# --- [3단계] 화면 꾸미기 ---
st.set_page_config(page_title="중등수학 도우미", page_icon="📝")
st.title("📝 중등수학 예습 진단")

# [중요] '처음부터 다시하기' 버튼 (에러가 날 때 눌러주세요)
if st.sidebar.button("🔄 대화 초기화 (에러 시 클릭)"):
    st.session_state.messages = []
    st.rerun()

# 대화 내용 저장소 만들기
if "messages" not in st.session_state:
    st.session_state.messages = []

# 기존 대화 보여주기
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

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






