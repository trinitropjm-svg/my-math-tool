import streamlit as st
import requests
import random
import os
import re
import json
from datetime import datetime

# =========================
# [1] 설정 및 상수
# =========================
DEFAULT_API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
if not DEFAULT_API_KEY:
    try:
        DEFAULT_API_KEY = st.secrets.get("GOOGLE_API_KEY", "").strip()
    except:
        DEFAULT_API_KEY = ""

TEACHER_PASSWORD = "1234" 
MODEL = "gemini-1.5-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}"

MAX_HINTS = 2
MAX_QUESTIONS = 20

# =========================
# [2] UI 보안 및 TTS (자바스크립트 통합)
# =========================
st.set_page_config(page_title="중등수학 AI 감독관", layout="centered")

# 메뉴 숨기기 및 음성 출력(TTS) 자바스크립트
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
        msg.rate = 1.1; // 약간 빠르게 설정
        window.speechSynthesis.speak(msg);
    }
    </script>
    """, unsafe_allow_html=True)

def tts(text: str):
    """AI 답변을 브라우저 스피커로 출력"""
    # 불필요한 마크다운 기호 제거 후 전송
    clean_text = re.sub(r'[*#_~]', '', text)
    safe_json = json.dumps(clean_text.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_json});</script>", height=0)

# =========================
# [3] 데이터 로더 (6개 학기 파일 통합)
# =========================
@st.cache_data
def load_math_data():
    all_data = {}
    semesters = ["중1-1", "중1-2", "중2-1", "중2-2", "중3-1", "중3-2"]
    
    for sem in semesters:
        file_path = f"{sem}수학.txt"
        if not os.path.exists(file_path):
            continue
            
        parsed_qs = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    clean = line.strip()
                    if not clean or "소단원명" in clean:
                        continue
                    
                    # [에러 해결]: 역슬래시 및 특수 제어문자 제거
                    clean = clean.replace("\\", "")
                    
                    parts = clean.split("\t")
                    if len(parts) >= 3:
                        unit = parts[0].strip()
                        q = parts[1].strip()
                        a = parts[2].strip()
                        parsed_qs.append({"unit": unit, "q": q, "a": a})
            
            if parsed_qs:
                all_data[sem] = parsed_qs
        except:
            continue
    return all_data

MATH_DB = load_math_data()

# =========================
# [4] AI 지시사항 및 호출
# =========================
def call_gemini(api_key, prompt):
    url = API_URL.format(MODEL, api_key)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=20)
        res = r.json()
        return res["candidates"][0]["content"]["parts"][0]["text"].strip()
    except:
        return "죄송해, 잠시 통신이 불안정해. 다시 한 번 말해줄래?"

def build_grader_prompt(q, correct_a, student_a, hint_count):
    return f"""
너는 다정한 중학교 수학 선생님이다. 학생의 답을 평가하되 다음 원칙을 사수하라.

1. 새로운 문제를 내지 마라. (앱이 다음 문제를 낸다)
2. 정답 여부를 판정하라.
3. 틀렸다면 정답을 말하지 말고 '힌트'만 주어라 (힌트는 최대 2번까지).
4. 수식은 반드시 한글로 ('루트 2', 'x의 제곱') 표현하라. 마크다운 수식($)은 절대 쓰지 마라.
5. 말투는 다정하고 친절하게.

[문제 정보]
- 문제: {q}
- 정답: {correct_a}
- 학생 답변: {student_a}
- 사용한 힌트: {hint_count} / 2

[출력 형식]
판정: (정답/오답/부분정답)
코멘트: (칭찬 또는 격려)
행동: (정답이면 "다음 문제로 가자!", 오답이면 힌트 제공)
"""

# =========================
# [5] 세션 상태 초기화
# =========================
if "step" not in st.session_state: st.session_state.step = "auth"
if "messages" not in st.session_state: st.session_state.messages = []
if "q_idx" not in st.session_state: st.session_state.q_idx = 0
if "hint_used" not in st.session_state: st.session_state.hint_used = 0
if "results" not in st.session_state: st.session_state.results = []

# =========================
# [6] 화면 렌더링
# =========================

# --- 1단계: 로그인 ---
if st.session_state.step == "auth":
    st.title("🔒 AI 수학 구술감독관")
    pw = st.text_input("학원 비밀번호", type="password")
    key = st.text_input("Gemini API Key", value=DEFAULT_API_KEY, type="password")
    if st.button("시스템 접속"):
        if pw == TEACHER_PASSWORD and key:
            st.session_state.api_key = key
            st.session_state.step = "init"
            st.rerun()
        else:
            st.error("비밀번호 또는 API 키를 확인하세요.")
    st.stop()

# --- 2단계: 설정 ---
if st.session_state.step == "init":
    st.title("👨‍🏫 테스트 설정")
    st.session_state.user_name = st.text_input("학생 이름")
    
    if MATH_DB:
        st.session_state.sel_sem = st.selectbox("학기", list(MATH_DB.keys()))
        units = sorted(list(set(d["unit"] for d in MATH_DB[st.session_state.sel_sem])))
        st.session_state.sel_unit = st.selectbox("소단원", units)
        num_q = st.slider("문항 수", 5, 20, 10)
        
        if st.button("테스트 시작"):
            if not st.session_state.user_name:
                st.warning("이름을 입력하세요.")
            else:
                qs = [d for d in MATH_DB[st.session_state.sel_sem] if d["unit"] == st.session_state.sel_unit]
                random.shuffle(qs)
                st.session_state.questions = qs[:num_q]
                st.session_state.step = "test"
                st.session_state.test_start = datetime.now().strftime("%H:%M")
                
                # 첫 문제 발성
                first_msg = f"반가워 {st.session_state.user_name}! {st.session_state.sel_unit} 단원 테스트를 시작할게. Q1. {st.session_state.questions[0]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": first_msg})
                st.rerun()
    st.stop()

# --- 3단계: 테스트 ---
if st.session_state.step == "test":
    st.title(f"📐 {st.session_state.sel_unit} 테스트")
    
    # 채팅 창 표시
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("답변을 입력하세요 ('그만' 입력 시 종료)"):
        if prompt == "그만":
            st.session_state.step = "report"
            st.rerun()
            
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        curr_q = st.session_state.questions[st.session_state.q_idx]
        
        with st.spinner("선생님이 생각 중..."):
            ai_reply = call_gemini(st.session_state.api_key, build_grader_prompt(curr_q['q'], curr_q['a'], prompt, st.session_state.hint_used))
        
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        with st.chat_message("assistant"):
            st.markdown(ai_reply)
        tts(ai_reply)
        
        # 정답 여부 파싱
        is_correct = "정답" in ai_reply.split('\n')[0]
        
        if is_correct:
            st.session_state.results.append({"q": curr_q['q'], "a": curr_q['a'], "res": "⭕ 정답", "hint": st.session_state.hint_used})
            st.session_state.q_idx += 1
            st.session_state.hint_used = 0
            
            if st.session_state.q_idx < len(st.session_state.questions):
                next_q = f"자, 다음 문제야! Q{st.session_state.q_idx + 1}. {st.session_state.questions[st.session_state.q_idx]['q']}"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
                st.rerun()
            else:
                st.session_state.step = "report"
                st.rerun()
        else:
            if st.session_state.hint_used < MAX_HINTS:
                st.session_state.hint_used += 1
            else:
                # 힌트 다 쓰면 오답 처리 후 다음으로
                st.session_state.results.append({"q": curr_q['q'], "a": curr_q['a'], "res": "❌ 오답", "hint": st.session_state.hint_used})
                st.session_state.q_idx += 1
                st.session_state.hint_used = 0
                st.rerun()

# --- 4단계: 리포트 ---
if st.session_state.step == "report":
    st.balloons()
    st.subheader("📋 학습 리포트")
    st.write(f"학생: {st.session_state.user_name} | 단원: {st.session_state.sel_unit}")
    
    correct_count = sum(1 for r in st.session_state.results if "⭕" in r['res'])
    st.metric("정답률", f"{correct_count}/{len(st.session_state.questions)}")
    
    for i, r in enumerate(st.session_state.results):
        with st.expander(f"Q{i+1}. {r['res']} (힌트 {r['hint']}회)"):
            st.write(f"**문제:** {r['q']}")
            st.write(f"**정답:** {r['a']}")
            
    if st.button("다시 시작"):
        st.session_state.clear()
        st.rerun()
