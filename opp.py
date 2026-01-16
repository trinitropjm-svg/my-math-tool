import streamlit as st
import requests
import random
import os
import re
import json

# --- [1] 선생님 필수 설정 ---
# 선생님의 API 키를 아래 따옴표 안에 넣어주세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
TEACHER_PASSWORD = "1234"  # 접속 비밀번호

# --- [2] UI 보안 및 음성 지원(TTS) 설정 ---
st.set_page_config(page_title="중등수학 AI 감독관", layout="centered")

# 메뉴 숨기기 및 한국어 TTS 스크립트 (백슬래시 에러 방지를 위해 문자열 구조 최적화)
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

# --- [3] 데이터 로더: 6개 학기 파일 통합 읽기 ---
@st.cache_data
def load_math_data():
    all_data = {}
    semesters = ["중1-1", "중1-2", "중2-1", "중2-2", "중3-1", "중3-2"]
    
    for sem in semesters:
        file_path = f"{sem}수학.txt"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    parsed_qs = []
                    for line in f:
                        # [에러 해결]: 백슬래시 문법 에러를 유발하는 re.sub 대신 
                        # 가장 안전한 .replace() 함수를 사용했습니다.
                        line = line.strip().replace("\\", "")
                        
                        if not line or "소단원명" in line:
                            continue
                        
                        # 형태의 태그 제거 (안전한 정규식)
                        line = re.sub(r"\", "", line)
                        
                        # 탭(\t)으로 구분된 데이터 분리
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            parsed_qs.append({
                                "unit": parts[0].strip(),
                                "q": parts[1].strip(),
                                "a": parts[2].strip()
                            })
                    if parsed_qs:
                        all_data[sem] = parsed_qs
            except Exception:
                continue
    return all_data

MATH_DB = load_math_data()

# --- [4] 앱 상태 관리 ---
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 1

# --- [5] 화면 로직 ---

# [1단계: 보안 접속]
if st.session_state.step == "auth":
    st.title("🔒 AI 구술 시험 시스템")
    pw = st.text_input("학원 비밀번호를 입력하세요", type="password")
    if st.button("시스템 접속"):
        if pw == TEACHER_PASSWORD:
            st.session_state.step = "init"
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# [2단계: 학생 이름 및 단원 선택]
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    st.session_state.user_name = st.text_input("학생 이름을 입력해주세요:")
    
    if not MATH_DB:
        st.error("데이터 파일(.txt)을 찾을 수 없습니다. 6개 파일이 깃허브에 있는지 확인해주세요.")
        st.stop()
        
    st.session_state.sel_sem = st.selectbox("학기 선택", list(MATH_DB.keys()))
    units = sorted(list(set([d["unit"] for d in MATH_DB[st.session_state.sel_sem]])))
    st.session_state.sel_unit = st.selectbox("오늘 공부한 소단원을 선택하세요:", units)
    
    if st.button("테스트 시작"):
        # 단원 문제 필터링 및 섞기
        st.session_state.questions = [d for d in MATH_DB[st.session_state.sel_sem] if d["unit"] == st.session_state.sel_unit]
        random.shuffle(st.session_state.questions)
        st.session_state.step = "test"
        
        # 시작 인사 원칙 반영
        intro = f"안녕하세요 중1수학 1학기 테스트입니다. {st.session_state.user_name} 학생, 오늘 공부한 {st.session_state.sel_unit} 단원을 얼마나 잘 알고 있는지 확인해볼게!"
        st.session_state.messages.append({"role": "assistant", "content": intro})
        st.rerun()
    st.stop()

# [3단계: 메인 구술 시험 및 TTS]
st.title(f"📐 {st.session_state.sel_unit} 테스트")

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

    # 인공지능 지시사항 (선생님 프롬프트 원칙 100% 반영)
    instruction = f"""
    너는 다정하고 전문적인 '수학 선생님'이야. 
    로봇 말투 금지: "질문을 시작합니다" 등 기계적인 멘트 금지.
    의학적 자문 등 불필요한 경고 멘트 절대 금지.
    
    [핵심 규칙]
    1. 수식은 반드시 한글로 ('x의 제곱', '2분의 1', '루트 3') 말하기.
    2. 정답이면 크게 칭찬하고 다음 질문(Q{st.session_state.q_idx}. 형식) 하기.
    3. 틀리면 정답을 바로 주지 말고 힌트를 최대 2번 줄 것.
    4. 학생이 답을 수정하면 배려하며 진행할 것.

    [현재 상황]
    - 학생 성함: {st.session_state.user_name}
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
            # TTS를 위한 텍스트 정제 (따옴표 에러 방지)
            safe_text = ai_reply.replace("'", "").replace('"', "").replace("\n", " ")
            st.components.v1.html(f"<script>window.parent.speak('{safe_text}');</script>", height=0)
    except:
        st.error("AI 선생님이 잠시 생각 중이에요. 다시 입력해 주세요.")

# [4단계: 리포트]
if st.session_state.step == "report":
    st.balloons()
    st.subheader("📋 학습 결과 리포트")
    st.write(f"- 학생 이름: {st.session_state.user_name}")
    st.write(f"- 학습 범위: {st.session_state.sel_sem} {st.session_state.sel_unit}")
    st.info("오늘 테스트 받느라 고생했어! 선생님께 이 화면을 보여드려.")
    if st.button("처음으로 돌아가기"):
        st.session_state.clear()
        st.rerun()
