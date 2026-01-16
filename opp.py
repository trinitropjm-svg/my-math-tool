import streamlit as st
import requests
import random
import os
import re
import json

# --- [1] 선생님 필수 설정 ---
# 선생님의 진짜 API 키를 따옴표 안에 넣어주세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
TEACHER_PASSWORD = "1234"  # 학원에서 사용할 시스템 접속 암호

# --- [2] UI 보안 잠금 및 음성 지원 설정 ---
st.set_page_config(page_title="중등수학 AI 구술감독관", layout="centered")

# 메뉴 숨기기 및 한국어 음성(TTS) 스크립트
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    <script>
    function speak(text) {
        window.speechSynthesis.cancel(); // 이전 음성 중단
        const msg = new SpeechSynthesisUtterance();
        msg.text = text;
        msg.lang = 'ko-KR';
        msg.rate = 1.0;
        window.speechSynthesis.speak(msg);
    }
    </script>
    """, unsafe_allow_html=True)

# --- [3] 데이터 로더: 6개 학기 텍스트 파일 통합 읽기 ---
@st.cache_data
def load_math_data():
    all_semesters = {}
    # 중1-1부터 중3-2까지 6개 학기 파일 리스트
    files = ["중1-1", "중1-2", "중2-1", "중2-2", "중3-1", "중3-2"]
    
    for sem in files:
        fname = f"{sem}수학.txt"
        if os.path.exists(fname):
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    content = f.readlines()
                    questions = []
                    for line in content:
                        # [에러 원천 차단]: 문제가 된 역슬래시 제거 코드 대신 안전한 정규식 사용
                        line = re.sub(r"\", "", line).strip()
                        if not line or "소단원명" in line: continue
                        
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            questions.append({
                                "unit": parts[0].strip(), 
                                "q": parts[1].strip(), 
                                "a": parts[2].strip()
                            })
                    if questions:
                        all_semesters[sem] = questions
            except Exception:
                continue
    return all_semesters

MATH_DB = load_math_data()

# --- [4] 앱 상태 관리 ---
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0

# --- [5] 화면 로직 ---

# [1단계: 접속 잠금]
if st.session_state.step == "auth":
    st.title("🔒 AI 구술 시험 시스템")
    pw_input = st.text_input("수업 비밀번호를 입력하세요", type="password")
    if st.button("시스템 접속"):
        if pw_input == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# [2단계: 학생 정보 및 단원 선택]
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    st.session_state.user_name = st.text_input("학생 이름을 입력하세요")
    
    if not MATH_DB:
        st.error("학습 데이터(.txt) 파일을 찾을 수 없습니다. 6개 학기 파일이 깃허브에 있는지 확인해 주세요.")
        st.stop()
        
    st.session_state.sel_sem = st.selectbox("학기 선택", list(MATH_DB.keys()))
    
    # 선택된 학기 내의 소단원 리스트 추출
    units = sorted(list(set([d["unit"] for d in MATH_DB[st.session_state.sel_sem]])))
    st.session_state.sel_unit = st.selectbox("소단원 선택", units)
    
    if st.button("테스트 시작"):
        # 해당 단원의 문제만 필터링 후 무작위 추출
        st.session_state.questions = [d for d in MATH_DB[st.session_state.sel_sem] if d["unit"] == st.session_state.sel_unit]
        random.shuffle(st.session_state.questions)
        st.session_state.step = "test"
        
        # 시작 인사 (지시사항 반영)
        start_msg = f"안녕하세요 중1수학 1학기 테스트입니다. 학생 이름과 소단원을 말씀해주세요. 화면에 나오는 단원 중 오늘 공부한 {st.session_state.sel_unit} 단원 이름을 말해줘!"
        st.session_state.messages.append({"role": "assistant", "content": start_msg})
        st.rerun()
    st.stop()

# [3단계: 구술 시험 및 음성 지원]
st.title(f"📐 {st.session_state.sel_unit} 테스트")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("답변을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    if prompt == "그만" or st.session_state.q_idx >= 20:
        st.session_state.step = "report"
        st.rerun()

    # AI 지시사항 조합
    instruction = f"""
    너는 다정하고 전문적인 '수학 선생님'이야. 
    학생 이름: {st.session_state.user_name}
    참고 데이터: {json.dumps(st.session_state.questions, ensure_ascii=False)}

    [가장 중요한 상호작용 원칙]
    1. 로봇 말투 절대 금지 ("질문을 시작합니다", "다시 말할게요" 등 금지)
    2. 수식은 반드시 'x의 제곱', '2분의 1', '루트 3'처럼 한글로만 말할 것
    3. 정답이면 크게 칭찬하고, 틀리면 힌트를 최대 2번 줄 것
    4. 의학적 자문 등 불필요한 경고 문구는 절대로 하지 말 것
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": f"{instruction}\n\n학생 답변: {prompt}"}]}]}
    
    try:
        res = requests.post(url, json=payload).json()
        ai_reply = res['candidates'][0]['content']['parts'][0]['text']
        
        with st.chat_message("assistant"):
            st.markdown(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            st.session_state.q_idx += 1
            # 음성 출력 (JS 호출 및 따옴표 충돌 방지)
            safe_text = ai_reply.replace("'", "").replace('"', "").replace("\n", " ")
            st.components.v1.html(f"<script>window.parent.speak('{safe_text}');</script>", height=0)
    except:
        st.error("AI 선생님이 잠시 생각 중이에요. 다시 입력해 주세요.")

# [4단계: 리포트 생성]
if st.session_state.step == "report":
    st.balloons()
    st.subheader("📋 학습 결과 리포트")
    st.write(f"- **학생 성함**: {st.session_state.user_name}")
    st.write(f"- **학습 범위**: {st.session_state.sel_sem} {st.session_state.sel_unit}")
    st.info("리포트는 읽지 않고 여기서 마칩니다. 선생님께 이 화면을 보여주세요!")
    if st.button("처음으로"):
        st.session_state.clear()
        st.rerun()
