import streamlit as st
import requests
import random
import os
import re
import json
from datetime import datetime

# =========================
# [1] 선생님 필수 설정
# =========================
# ※ 주의: 여기에 선생님의 실제 API 키를 입력해 주세요.
API_KEY = "AIzaSyBsxvpd_PBZXG1vzM0rdKmZAsc7hZoS0F0".strip()
TEACHER_PASSWORD = "1234" 

# =========================
# [2] 모델 자동 탐색 기능 (안정화 패치)
# =========================
@st.cache_resource
def get_best_model(api_key):
    """사용 가능한 최신 모델을 자동으로 찾아 반환합니다."""
    candidates = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        res = requests.get(url, timeout=5).json()
        if "models" in res:
            available = [m["name"].split("/")[-1] for m in res["models"]]
            for cand in candidates:
                if cand in available: return cand
            for m in available:
                if "flash" in m: return m
    except: pass
    return "gemini-1.5-flash"

ACTIVE_MODEL = get_best_model(API_KEY)
API_URL = f"https://generativelanguage.googleapis.com/v1/models/{ACTIVE_MODEL}:generateContent?key={API_KEY}"

# =========================
# [3] UI + 음성(TTS/STT) 설정
# =========================
st.set_page_config(page_title="AI 수학 구술감독관", layout="centered")

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
        msg.rate = 1.1;
        window.speechSynthesis.speak(msg);
    }
    let recognition;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.lang = 'ko-KR';
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            alert("🎤 인식 결과: " + transcript + "\\n\\n입력창에 적고 엔터를 쳐주세요!");
        };
    }
    function startListening() {
        if(recognition) recognition.start();
        else alert("브라우저가 음성 인식을 지원하지 않습니다.");
    }
    </script>
    """, unsafe_allow_html=True)

def tts(text: str):
    clean_text = re.sub(r'[*#_~]', '', text)
    safe_text = json.dumps(clean_text.replace("\n", " "))
    st.components.v1.html(f"<script>window.parent.speak({safe_text});</script>", height=0)

# =========================
# [4] 데이터 로더
# =========================
@st.cache_data
def load_math_data():
    all_data = {}
    semesters = ["중1-1", "중1-2", "중2-1", "중2-2", "중3-1", "중3-2"]
    for sem in semesters:
        file_path = f"{sem}수학.txt"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    parsed = []
                    for line in f:
                        clean = line.strip().replace("\\", "")
                        if not clean or "소단원명" in clean: continue
                        parts = clean.split("\t")
                        if len(parts) >= 3:
                            parsed.append({"unit": parts[0].strip(), "q": parts[1].strip(), "a": parts[2].strip()})
                    if parsed: all_data[sem] = parsed
            except: continue
    return all_data

MATH_DB = load_
