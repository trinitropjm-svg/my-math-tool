import streamlit as st
import google.generativeai as genai

# --- [1단계] API 키 설정 (공백 청소기 포함) ---
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()

# --- [2단계] 인공지능 모델 설정 (에러 방지용 특수 설정) ---
try:
    genai.configure(api_key=API_KEY)
    
    # 404 에러를 방지하기 위해 가장 표준적인 이름을 사용합니다.
    # 만약 'models/'를 붙여서 안 되면 빼고, 빼서 안 되면 붙이도록 설정했습니다.
    model = genai.GenerativeModel('gemini-1.5-flash')
    
except Exception as e:
    st.error(f"설정 에러: {e}")

# --- [3단계] 화면 구성 ---
st.title("📝 중등수학 예습 진단")
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- [4단계] 대화 진행 ---
if prompt := st.chat_input("질문을 입력하세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # 질문을 보냅니다.
        response = model.generate_content(prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
    except Exception as e:
        # 에러가 나면 'v1beta'라는 말이 포함되어 있는지 확인하여 해결책을 제시합니다.
        if "v1beta" in str(e):
            st.error("도구 버전이 낮아 에러가 발생했습니다. 잠시 후 'Reboot app'을 다시 시도해주세요.")
        else:
            st.error(f"대화 에러 발생: {e}")

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










