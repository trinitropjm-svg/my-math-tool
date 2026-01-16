import streamlit as st
import requests
import random
import os
import re
import json

# --- [1] 선생님 필수 설정 ---
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip() # 여기에 진짜 API 키를 넣어주세요.
TEACHER_PASSWORD = "1234"  # 학원 접속용 비밀번호

# --- [2] UI 보안 잠금 및 한국어 음성(TTS) 설정 ---
st.set_page_config(page_title="중등수학 AI 감독관", layout="centered")

# 메뉴 숨기기 및 브라우저 음성을 사용하는 자바스크립트 스크립트
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

# --- [3] 데이터 로더: 6개 학기 텍스트 파일(탭 구분) 통합 읽기 ---
@st.cache_data
def load_all_math_data():
    all_data = {}
    semesters = ["중1-1", "중1-2", "중2-1", "중2-2", "중3-1", "중3-2"]
    
    for sem in semesters:
        file_path = f"{sem}수학.txt"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    parsed_qs = []
                    for line in lines:
                        # [에러 원천 차단]: 역슬래시 에러를 일으키던 코드를 안전한 방식으로 대체
                        line = line.strip().replace("\\", "") 
                        if not line or "소단원명" in line:
                            continue
                        
                        # 불필요한 태그 제거
                        line = re.sub(r"\", "", line)
                        
                        # 탭(\t)으로 단원, 질문, 정답 분리
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            parsed_qs.append({
                                "unit": parts[0].strip(),
                                "q": parts[1].strip(),
                                "a": parts[2].strip()
                            })
                    if parsed_qs:
                        all_data[sem] = parsed_qs
            except Exception as e:
                st.error(f"{sem} 파일 읽기 중 오류 발생: {e}")
    return all_data

MATH_DB = load_all_math_data()

# --- [4] 앱 상태(세션) 관리 ---
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 1
if "wrong_notes" not in st.session_state: st.session_state.wrong_notes = []

# --- [5] 화면 로직 ---

# 1단계: 접속 비밀번호 잠금 (보안)
if st.session_state.step == "auth":
    st.title("🔒 AI 구술 시험 시스템")
    pw_input = st.text_input("학원 비밀번호를 입력하세요", type="password")
    if st.button("시스템 접속"):
        if pw_input == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# 2단계: 학생 이름 및 학기/단원 선택
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    st.session_state.user_name = st.text_input("학생 이름을 입력해주세요:")
    
    if not MATH_DB:
        st.error("학습 데이터(.txt) 파일을 찾을 수 없습니다. 6개 파일이 폴더에 있는지 확인해주세요.")
        st.stop()
        
    st.session_state.sel_sem = st.selectbox("학기 선택", list(MATH_DB.keys()))
    
    # 선택된 학기의 소단원 리스트 추출
    unit_list = sorted(list(set([d["unit"] for d in MATH_DB[st.session_state.sel_sem]])))
    st.session_state.sel_unit = st.selectbox("오늘 공부한 소단원을 선택하세요:", unit_list)
    
    if st.button("테스트 시작"):
        # 단원 문제 필터링 및 섞기
        st.session_state.questions = [d for d in MATH_DB[st.session_state.sel_sem] if d["unit"] == st.session_state.sel_unit]
        random.shuffle(st.session_state.questions)
        st.session_state.step = "test"
        
        # 시작 인사 (지시사항 원칙 반영)
        intro = f"안녕하세요 {st.session_state.sel_sem}수학 테스트입니다. 학생 이름과 소단원을 말씀해주세요."
        st.session_state.messages.append({"role": "assistant", "content": intro})
        st.rerun()
    st.stop()

# 3단계: 메인 구술 시험 진행 (음성 지원 포함)
st.title(f"📐 {st.session_state.sel_unit} 테스트")

# 첫 진입 시 음성 지시 (지시사항 반영)
if len(st.session_state.messages) == 1:
    voice_msg = "화면에 나오는 단원 중 오늘 공부한 단원 이름을 말해줘!"
    st.components.v1.html(f"<script>window.parent.speak('{voice_msg}');</script>", height=0)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("답변을 입력하세요 (끝내려면 '그만' 입력)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if prompt == "그만" or st.session_state.q_idx > 20:
        st.session_state.step = "report"
        st.rerun()

    # 인공지능 지시사항 (선생님이 주신 프롬프트 원칙 100% 반영)
    instruction = f"""
    너는 다정하고 전문적인 '수학 선생님'이자 '구술 시험 감독관'이야.
    업로드된 데이터를 기반으로 학생과 대화하며 테스트를 진행해라.

    [가장 중요한 상호작용 원칙]
    1. 로봇 같은 표현 금지: "다시 말할게요", "질문을 시작합니다" 등 기계적인 멘트 절대 금지.
    2. 의학적/전문적 자문 관련 경고 멘트 절대 금지.
    3. 니가 한 말은 절대 반복하지 말고 계속 진행한다.
    4. 학생이 답을 수정하면 "네 알겠습니다"라고 답하며 배려한다.
    5. 정답이면 크게 칭찬하고 다음 질문을 한다.
    6. 틀리면 힌트를 주어 스스로 답하게 유도한다. (최대 2번)
    7. 수식은 반드시 'x의 제곱', '2분의 1', '루트 3'처럼 한글로만 풀어서 말한다.
    8. 질문은 "Q{st.session_state.q_idx}. (질문 내용)" 형식으로 하나씩만 한다.

    [현재 상황]
    - 학생 이름: {st.session_state.user_name}
    - 테스트 단원: {st.session_state.sel_unit}
    - 참고 문제 데이터: {json.dumps(st.session_state.questions, ensure_ascii=False)}
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
            # 음성 출력 (특수문자 제거 후 JS 호출)
            safe_text = ai_reply.replace("'", "").replace('"', "").replace("\n", " ")
            st.components.v1.html(f"<script>window.parent.speak('{safe_text}');</script>", height=0)
    except:
        st.error("AI 선생님과 연결이 잠시 불안정합니다. 다시 입력해 주세요.")

# 4단계: 리포트 생성 (읽지 않고 표시만 함)
if st.session_state.step == "report":
    st.balloons()
    st.subheader("📋 학습 리포트 (선생님 확인용)")
    st.write(f"- **학생 이름**: {st.session_state.user_name}")
    st.write(f"- **학습 단원**: {st.session_state.sel_sem} {st.session_state.sel_unit}")
    st.write(f"- **진행 문항**: {st.session_state.q_idx - 1}문항")
    st.info("AI 선생님 종합 의견: 오늘 배운 개념을 끝까지 성실하게 설명해준 모습이 아주 훌륭해! 부족한 부분만 살짝 더 복습해보자.")
    if st.button("처음으로 돌아가기"):
        st.session_state.clear()
        st.rerun()
