"""AI Career Assistant - 통합 Streamlit 앱
자소서 작성 → 텍스트 기반 면접 → 음성 대화형 면접 → 연습 기록
"""

from dotenv import load_dotenv
load_dotenv(dotenv_path=r"C:\Users\VisualS2\Desktop\AI_LAB\git\ai-career-assistant\.env")

import streamlit as st
import sys
import os
import threading
import time
import json
import requests
import sounddevice as sd

sys.path.append(os.path.dirname(__file__))

from voice.recorder import record_until_silence, cleanup_audio_file
from voice.stt import transcribe
from voice.tts import speak
from openai import OpenAI
from app.services.interview import crawl_job_posting, extract_job_info

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_BASE = "http://localhost:8000/api/v1"

VOICE_SYSTEM_PROMPT = """당신은 IT 기업의 시니어 개발자 면접관입니다.
다음 규칙을 반드시 지키세요:
- 한 번에 질문 하나만 하세요
- 지원자 답변의 핵심 키워드를 잡아 꼬리질문을 하세요
- 모호한 답변은 구체적으로 파고드세요
- "~하셨군요. 그렇다면 ~는 어떻게 하셨나요?" 형태를 자주 사용하세요
- 압박보다는 대화하듯 자연스럽게 진행하세요
- 답변이 구체적이면 다음 주제로 넘어가세요
- 10턴이 지나면 면접을 마무리하세요
- 반드시 자연스러운 한국어로만 질문하세요"""


# ──────────────────────────────────────────────
# API 공통 함수
# ──────────────────────────────────────────────

def api_post(endpoint: str, **kwargs) -> dict:
    """FastAPI POST 요청 공통 함수"""
    try:
        res = requests.post(f"{API_BASE}/{endpoint}", **kwargs)
        return res.json()
    except Exception as e:
        return {"error": str(e)}


def api_get(endpoint: str) -> dict:
    """FastAPI GET 요청 공통 함수"""
    try:
        res = requests.get(f"{API_BASE}/{endpoint}")
        return res.json()
    except Exception as e:
        return {"error": str(e)}


def poll_answer_status(answer_id: int, max_retries: int = 60) -> dict:
    """Celery 비동기 답변 처리 완료까지 폴링 (0.5초 간격)"""
    for i in range(max_retries):
        time.sleep(0.5)
        data = api_get(f"answers/{answer_id}/status")
        if data.get("status") == "completed":
            return data
        st.session_state.poll_msg = f"음성 분석 중... ({i + 1}초)"
    return {"error": "처리 시간 초과"}


# ──────────────────────────────────────────────
# 음성 면접 LLM 함수
# ──────────────────────────────────────────────

def build_job_context(job_info: dict) -> str:
    """채용공고 정보를 시스템 프롬프트에 주입할 문자열로 변환"""
    if not job_info:
        return ""
    return f"""
채용공고 정보:
- 회사: {job_info.get('company', '')}
- 직무: {job_info.get('position', '')}
- 필수 스킬: {job_info.get('required_skills', [])}
- 우대 스킬: {job_info.get('preferred_skills', [])}
- 요약: {job_info.get('summary', '')}
위 공고 내용을 바탕으로 해당 직무에 맞는 질문을 하세요.
"""


def ask_llm(messages: list, job_info: dict = None) -> str:
    """GPT-4o-mini 호출 공통 함수"""
    system = VOICE_SYSTEM_PROMPT + build_job_context(job_info)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}] + messages,
    )
    return response.choices[0].message.content


def get_opening_question(name: str, role: str, job_info: dict = None) -> str:
    """음성 면접 첫 질문 생성"""
    return ask_llm(
        [{"role": "user", "content": f"지원자 이름: {name}, 지원 직무: {role}. 면접을 시작해주세요. 첫 질문을 해주세요."}],
        job_info,
    )


def get_next_question(history: list, job_info: dict = None) -> str:
    """대화 히스토리 기반 꼬리질문 생성"""
    return ask_llm(history, job_info)


def generate_voice_report(history: list, job_info: dict = None) -> dict:
    """음성 면접 종료 후 항목별 평가 리포트 생성"""
    job_context = (
        f"직무: {job_info.get('position', '')} / 회사: {job_info.get('company', '')}"
        if job_info else ""
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 면접 평가 전문가입니다. 면접 대화를 분석해서 JSON으로 평가 결과를 반환합니다."},
            {"role": "user", "content": f"""
아래 면접 대화를 분석해서 JSON으로 평가해줘.
{job_context}

평가 항목 (각 0~10점):
- tech: 기술 이해도
- specificity: 답변 구체성
- logic: 논리 구조
- communication: 커뮤니케이션

그리고:
- total: 총점 (0~50)
- strengths: 잘한 점 2개 (리스트)
- improvements: 개선할 점 2개 (리스트)
- summary: 한 줄 총평

JSON만 반환해.
대화: {json.dumps(history, ensure_ascii=False)}
"""},
        ],
        temperature=0,
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(result)


def save_voice_to_db(name: str, role: str, job_info: dict, conversation: list, report: dict) -> dict:
    """음성 면접 대화 기록을 DB에 저장"""
    return api_post("sessions/voice", json={
        "name": name,
        "role": role,
        "job_url": "",
        "company": job_info.get("company", "") if job_info else "",
        "position": job_info.get("position", role) if job_info else role,
        "conversation": conversation,
        "report": report,
    })


# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────

def render_sidebar() -> str:
    """사이드바 렌더링. 선택된 페이지 반환."""
    with st.sidebar:
        st.markdown("""
            <div style="text-align:center; padding: 10px 0;">
                <div style="font-size:2rem;">😊</div>
                <div style="font-size:1.1rem; font-weight:700; color:white; margin-top:8px;">Have a Nice Day!</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**📌 메뉴**")
        page = st.radio(
            "메뉴",
            ["🏠 홈", "📝 자소서 작성", "🎤 텍스트 기반 면접", "🗣️ 음성 대화형 면접", "📋 연습 기록"],
            label_visibility="collapsed",
            )
        st.divider()

        # 마이크 설정 (면접 관련 페이지에서만 표시)
        if "음성 대화형" in page:
            devices = sd.query_devices()
            input_devices = {
                f"{i}: {d['name']}": i
                for i, d in enumerate(devices)
                if d["max_input_channels"] > 0
            }
            st.markdown("### 🎙️ 마이크 설정")
            selected = st.selectbox("마이크 선택", list(input_devices.keys()))
            st.session_state.mic_index = input_devices[selected]

            st.markdown("### 🧠 STT 모델")
            model_map = {
                "base (빠름)": "base",
                "medium (권장)": "medium",
                "large (정확)": "large",
            }
            selected_model = st.selectbox("Whisper 모델", list(model_map.keys()), index=1)
            st.session_state.whisper_model = model_map[selected_model]

            if "음성 대화형" in page:
                st.markdown("### 🔇 무음 감지")
                threshold_map = {
                    "낮음 (0.01)": 0.01,
                    "보통 (0.02)": 0.02,
                    "높음 - 블루투스 (0.03)": 0.03,
                    "매우 높음 (0.05)": 0.05,
                }
                sel_thresh = st.selectbox("무음 감지 임계값", list(threshold_map.keys()), index=2)
                st.session_state.silence_threshold = threshold_map[sel_thresh]

                st.markdown("### ⌨️ 입력 방식")
                st.session_state.input_mode = st.radio(
                    "답변 입력 방식",
                    ["🎙️ 음성 입력", "⌨️ 텍스트 입력"],
                    index=1,
                )

    return page


# ──────────────────────────────────────────────
# 페이지: 홈
# ──────────────────────────────────────────────

def show_home():
    st.image("images/banner.png", width=600)
    st.divider()
    st.markdown("### 📝 자소서 작성")
    st.markdown("""
채용공고 URL과 이력서를 입력하면 공고 맞춤형 자소서 초안을 자동 생성합니다.
- 자소서 길이와 항목 형식을 직접 커스터마이징 가능
- 생성된 자소서를 직접 편집 후 구체성/직무연관성/구조 항목으로 품질 평가
- 자소서 완성 후 바로 면접 연습으로 연결 가능
""")
    st.divider()

    st.markdown("### 🎤 텍스트 기반 면접")
    st.markdown("""
채용공고와 이력서를 분석해 맞춤형 면접 질문 8개를 생성합니다.
- 보유 스킬 심화 / 부족 스킬 / 직무·회사 / 인성 카테고리로 구성
- 마이크 녹음, 파일 업로드, 텍스트 직접 입력 3가지 답변 방식 지원
- 답변마다 논리성/구체성/시간 관리 항목별 점수 + 모범 답안 제공
- 면접 종료 후 카테고리별 평균 점수 리포트 제공
""")
    st.divider()

    st.markdown("### 🗣️ 음성 대화형 면접")
    st.markdown("""
면접관 AI와 실시간 음성으로 대화하며 면접을 진행합니다.
- 채용공고 URL 입력 시 해당 직무·기술스택 기반 맞춤 질문 생성
- 답변 키워드를 분석해 자동으로 꼬리질문 생성 (10턴 진행)
- Edge-TTS로 면접관 음성 출력, Whisper STT로 음성 인식
- 면접 종료 후 기술 이해도/구체성/논리/커뮤니케이션 항목별 리포트
- 모든 대화 기록 DB 저장 및 과거 기록 조회 가능
""")
    st.divider()

    st.markdown("### 📋 연습 기록")
    st.markdown("""
지금까지 진행한 모든 면접 세션을 조회할 수 있습니다.
- 세션별 회사/직무/날짜 정보 확인
- 질문별 답변 내용과 항목별 점수 기록 조회
- 반복 연습 시 점수 변화 추이 확인 가능
""")
    st.divider()

    st.info("💡 추천 흐름: 자소서 작성 → 텍스트 기반 면접 → 음성 대화형 면접")


# ──────────────────────────────────────────────
# 페이지: 자소서 작성
# ──────────────────────────────────────────────

def show_cover_letter():
    """자소서 생성 및 품질 평가 페이지"""
    st.title("📝 자소서 작성")

    # 세션 상태 초기화
    if "cover_state" not in st.session_state:
        st.session_state.cover_state = "input"  # input → result
        st.session_state.cover_session_id = None
        st.session_state.cover_letter = None

    # ── 입력 단계 ──
    if st.session_state.cover_state == "input":
        job_url = st.text_input("채용공고 URL", placeholder="https://www.jobkorea.co.kr/...")
        resume_text = st.text_area("이력서 텍스트", placeholder="이력서를 붙여넣으세요...", height=150)

        col1, col2 = st.columns([3, 1])
        with col1:
            length = st.slider("자소서 길이", 200, 1000, 500, step=100)
        with col2:
            st.markdown(f"<br><b>{length}자</b>", unsafe_allow_html=True)

        custom_format = st.text_area(
            "커스텀 형식 (선택)",
            placeholder="비워두면 기본 형식으로 생성됩니다.\n예시:\n1. 지원동기\n2. 직무 관련 경험\n3. 입사 후 포부",
            height=100,
        )

        if st.button("자소서 생성", disabled=not (job_url and resume_text)):
            with st.spinner("자소서 생성 중... (30초 정도 걸려요)"):
                # 세션 생성
                session_data = api_post("sessions", json={"job_url": job_url, "resume_text": resume_text})
                
                if "id" not in session_data:
                    st.error("세션 생성 실패")
                    return

                st.session_state.cover_session_id = session_data["id"]

                # 자소서 생성
                cover_data = api_post("cover-letter/generate", json={
                    "session_id": st.session_state.cover_session_id,
                    "length": length,
                    "custom_format": custom_format,
                })
                if "error" in cover_data:
                    st.error(f"자소서 생성 실패: {cover_data['error']}")
                    return

                st.session_state.cover_letter = cover_data["cover_letter"]
                st.session_state.cover_state = "result"
                st.rerun()

    # ── 결과 단계 ──
    elif st.session_state.cover_state == "result":
        st.markdown("✏️ 각 항목을 직접 수정할 수 있습니다.")

        # 편집 가능한 자소서 표시
        edited = {}
        for key, value in st.session_state.cover_letter.items():
            edited[key] = st.text_area(key, value=value, height=120, key=f"cover_{key}")
        st.session_state.cover_letter = edited

        # 품질 평가
        st.divider()
        if st.button("📊 품질 평가 받기"):
            with st.spinner("평가 중..."):
                eval_data = api_post("cover-letter/evaluate", json={
                    "session_id": st.session_state.cover_session_id,
                    "cover_letter": st.session_state.cover_letter,
                })
                if "error" not in eval_data:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("구체성", f"{eval_data.get('specificity', 0)}/10")
                    col2.metric("직무연관성", f"{eval_data.get('relevance', 0)}/10")
                    col3.metric("구조/논리", f"{eval_data.get('structure', 0)}/10")
                    col4.metric("총점", f"{eval_data.get('total', 0)}/30")
                    st.info(f"💬 {eval_data.get('feedback', '')}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 다시 작성"):
                st.session_state.cover_state = "input"
                st.rerun()
        with col2:
            if st.button("🎤 이 자소서로 면접 보기 →"):
                # 텍스트 면접 페이지로 세션 ID 전달
                st.session_state.text_session_id = st.session_state.cover_session_id
                st.session_state.text_from_cover = True
                st.session_state.text_state = "questions"
                # 질문 로드
                session_data = api_get(f"sessions/{st.session_state.cover_session_id}")
                st.session_state.text_questions = session_data.get("questions", [])
                st.session_state.text_current_idx = 0
                st.session_state.text_finished = False
                st.rerun()


# ──────────────────────────────────────────────
# 페이지: 텍스트 기반 면접
# ──────────────────────────────────────────────

def show_text_interview():
    """텍스트 기반 면접 페이지 - 질문 8개 + 마이크/파일 답변 + 피드백"""
    st.title("🎤 텍스트 기반 면접")

    # 세션 상태 초기화
    if "text_state" not in st.session_state:
        st.session_state.text_state = "setup"
        st.session_state.text_session_id = None
        st.session_state.text_questions = []
        st.session_state.text_current_idx = 0
        st.session_state.text_finished = False
        st.session_state.text_from_cover = False

    # ── 설정 단계 ──
    if st.session_state.text_state == "setup":
        job_url = st.text_input("채용공고 URL", placeholder="https://www.jobkorea.co.kr/...")
        resume_text = st.text_area("이력서 텍스트", placeholder="이력서를 붙여넣으세요...", height=150)

        if st.button("면접 시작", disabled=not (job_url and resume_text)):
            with st.spinner("공고 분석 및 질문 생성 중... (30초 정도 걸려요)"):
                session_data = api_post("sessions", json={"job_url": job_url, "resume_text": resume_text})
                if "error" in session_data:
                    st.error(f"오류: {session_data['error']}")
                    return
                st.session_state.text_session_id = session_data["id"]
                st.session_state.text_questions = session_data.get("questions", [])
                st.session_state.text_current_idx = 0
                st.session_state.text_state = "questions"
                st.rerun()

    # ── 질문 진행 단계 ──
    elif st.session_state.text_state == "questions":
        questions = st.session_state.text_questions
        idx = st.session_state.text_current_idx

        if idx >= len(questions):
            st.session_state.text_state = "report"
            st.rerun()
            return

        q = questions[idx]
        st.markdown(f"**{idx + 1} / {len(questions)}**")
        st.progress((idx) / len(questions))

        # 카테고리 뱃지 색상
        category_colors = {
            "보유 스킬": "🟢",
            "부족 스킬": "🔴",
            "직무/회사": "🔵",
            "인성/경험": "🟡",
        }
        badge = category_colors.get(q.get("category", ""), "⚪")
        st.markdown(f"{badge} **{q.get('category', '')}**")
        st.info(q.get("question_text", ""))

        direct_text = st.text_area("답변을 입력하세요", height=100, placeholder="질문에 대한 답변을 입력하세요...")
        if st.button("제출"):
            if direct_text.strip():
                _submit_text_answer(q["id"], direct_text.strip(), 0)
            else:
                st.warning("답변을 입력해주세요.")

        # 피드백 표시
        if "text_feedback" in st.session_state:
            feedback = st.session_state.text_feedback
            st.divider()
            st.markdown("### 📊 답변 평가")
            col1, col2, col3 = st.columns(3)
            col1.metric("논리성", f"{feedback.get('logic_score', 0)}/5")
            col2.metric("구체성", f"{feedback.get('specificity_score', 0)}/5")
            col3.metric("총점", f"{feedback.get('total_score', 0)}/10")
            st.success(f"💬 {feedback.get('feedback', '')}")

            # 모범 답안
            if q.get("model_answer"):
                with st.expander("📖 모범 답안 보기"):
                    st.markdown(q["model_answer"])
            if q.get("tip"):
                with st.expander("💡 팁 보기"):
                    st.markdown(q["tip"])

            if st.button("다음 질문 →"):
                st.session_state.text_current_idx += 1
                del st.session_state.text_feedback
                if "text_transcript" in st.session_state:
                    del st.session_state.text_transcript
                st.rerun()

    # ── 최종 리포트 단계 ──
    elif st.session_state.text_state == "report":
        st.markdown("### 🎉 면접 완료")
        with st.spinner("리포트 생성 중..."):
            report = api_get(f"sessions/{st.session_state.text_session_id}/report")
            stats = api_get(f"sessions/{st.session_state.text_session_id}/category-stats")

        if "error" not in report:
            avg = report.get("overall_avg")
            st.metric("전체 평균 점수", f"{avg}/15" if avg else "-")
            st.caption(f"{report.get('answered_questions', 0)}개 질문 답변 완료 / 전체 {report.get('total_questions', 0)}개")

            # 카테고리별 점수
            if "error" not in stats:
                cats = stats.get("categories", [])
                if any(c.get("avg_score") for c in cats):
                    import pandas as pd
                    df = pd.DataFrame([
                        {"카테고리": c["category"], "평균 점수": c["avg_score"] or 0}
                        for c in cats
                    ])
                    st.bar_chart(df.set_index("카테고리"))

            # 최고/최저 답변
            col1, col2 = st.columns(2)
            with col1:
                if report.get("best_answer"):
                    st.success(f"✅ **가장 잘한 답변**\n\n{report['best_answer']['question']}\n\n총점 {report['best_answer']['score']}/15")
            with col2:
                if report.get("worst_answer"):
                    st.error(f"⚠️ **가장 부족한 답변**\n\n{report['worst_answer']['question']}\n\n총점 {report['worst_answer']['score']}/15")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("다시 시작"):
                for key in ["text_state", "text_session_id", "text_questions", "text_current_idx",
                            "text_finished", "text_from_cover", "text_feedback", "text_transcript"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        with col2:
            if st.button("📋 연습 기록 보기"):
                st.session_state.goto_history = True
                st.rerun()


def _submit_text_answer(question_id: int, text: str, duration: int):
    """텍스트 답변 평가 API 호출 후 피드백 저장"""
    with st.spinner("평가 중..."):
        result = api_post("evaluate-text", json={
            "question_id": question_id,
            "answer_text": text,
            "duration_seconds": duration,
        })
    if "error" not in result:
        st.session_state.text_feedback = result
        st.rerun()
    else:
        st.error(f"평가 실패: {result['error']}")


def _show_text_feedback(feedback: dict, q: dict):
    """파일 업로드 방식 답변 피드백 표시"""
    st.session_state.text_feedback = feedback
    st.rerun()


# ──────────────────────────────────────────────
# 페이지: 음성 대화형 면접
# ──────────────────────────────────────────────

def handle_voice_answer(answer_text: str):
    """음성 답변 처리 - 히스토리 추가 후 꼬리질문 or 종료"""
    st.session_state.voice_history.append({"role": "user", "content": answer_text})
    st.session_state.voice_turn += 1

    if st.session_state.voice_turn >= 10:
        closing = "수고하셨습니다. 오늘 면접은 여기서 마치겠습니다. 좋은 결과 있으시길 바랍니다."
        st.session_state.voice_history.append({"role": "assistant", "content": closing})
        speak(closing)
        with st.spinner("면접 결과 분석 중..."):
            report = generate_voice_report(st.session_state.voice_history, st.session_state.get("voice_job_info"))
            st.session_state.voice_report = report
        with st.spinner("면접 기록 저장 중..."):
            result = save_voice_to_db(
                st.session_state.get("voice_name", ""),
                st.session_state.get("voice_role", ""),
                st.session_state.get("voice_job_info"),
                st.session_state.voice_history,
                report,
            )
            if "error" not in result:
                st.session_state.voice_saved_id = result.get("session_id")
        st.session_state.voice_finished = True
    else:
        with st.spinner("면접관이 생각 중..."):
            next_q = get_next_question(st.session_state.voice_history, st.session_state.get("voice_job_info"))
            st.session_state.voice_history.append({"role": "assistant", "content": next_q})
            speak(next_q)

    st.rerun()


def record_with_ui():
    """마이크 녹음 + 실시간 스펙트럼 표시 후 STT 변환"""
    shared_state = {"level": 0.0, "done": False, "path": None}

    def _record():
        shared_state["path"] = record_until_silence(
            device_index=st.session_state.get("mic_index"),
            shared_state=shared_state,
            silence_threshold=st.session_state.get("silence_threshold", 0.02),
        )
        shared_state["done"] = True

    t = threading.Thread(target=_record)
    t.start()
    ui = st.empty()
    start = time.time()
    while not shared_state["done"]:
        elapsed = time.time() - start
        bars = min(int(shared_state["level"] * 400), 20)
        ui.markdown(f"🎙️ **녹음 중** ⏱️ **{elapsed:.1f}초**\n\n`{'█' * bars}{'░' * (20 - bars)}`")
        time.sleep(0.05)
    t.join()
    ui.markdown(f"✅ 녹음 완료 ({time.time() - start:.1f}초)")

    audio_path = shared_state["path"]
    if not audio_path:
        st.warning("녹음에 실패했습니다.")
        return
    with st.spinner("답변 인식 중..."):
        text = transcribe(audio_path, st.session_state.get("whisper_model", "medium"))
        cleanup_audio_file(audio_path)
    if text:
        handle_voice_answer(text)
    else:
        st.warning("답변이 인식되지 않았습니다.")


def show_voice_interview():
    """음성 대화형 면접 페이지"""
    st.title("🗣️ 음성 대화형 면접")

    # 세션 상태 초기화
    if "voice_started" not in st.session_state:
        st.session_state.voice_started = False
        st.session_state.voice_history = []
        st.session_state.voice_turn = 0
        st.session_state.voice_finished = False
        st.session_state.voice_job_info = None
        st.session_state.voice_report = None

    # ── 시작 전 ──
    if not st.session_state.voice_started:
        name = st.text_input("이름", placeholder="홍길동")
        role = st.text_input("지원 직무", placeholder="AI 백엔드 개발자")
        job_url = st.text_input("채용공고 URL (선택)", placeholder="https://www.jobkorea.co.kr/...")
        st.caption("URL 입력 시 공고 맞춤 꼬리질문이 생성됩니다.")

        if st.button("면접 시작", disabled=not (name and role)):
            job_info = None
            if job_url:
                with st.spinner("채용공고 분석 중..."):
                    try:
                        content = crawl_job_posting(job_url)
                        job_info = extract_job_info(content)
                        st.success(f"✅ {job_info.get('company', '')} — {job_info.get('position', '')} 공고 분석 완료")
                    except Exception as e:
                        st.warning(f"공고 분석 실패: {e}. 일반 질문으로 진행합니다.")
            with st.spinner("면접관이 준비 중입니다..."):
                first_q = get_opening_question(name, role, job_info)
                st.session_state.voice_history.append({"role": "assistant", "content": first_q})
                st.session_state.voice_name = name
                st.session_state.voice_role = role
                st.session_state.voice_job_info = job_info
                st.session_state.voice_started = True
                speak(first_q)
            st.rerun()
        return

    # ── 종료: 리포트 ──
    if st.session_state.voice_finished:
        st.success("면접이 종료되었습니다.")
        if st.session_state.get("voice_saved_id"):
            st.info(f"📁 기록 저장 완료 (세션 ID: {st.session_state.voice_saved_id})")

        report = st.session_state.get("voice_report", {})
        if report:
            st.markdown("### 📊 면접 평가 리포트")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("기술 이해도", f"{report.get('tech', 0)}/10")
                st.metric("논리 구조", f"{report.get('logic', 0)}/10")
            with col2:
                st.metric("답변 구체성", f"{report.get('specificity', 0)}/10")
                st.metric("커뮤니케이션", f"{report.get('communication', 0)}/10")
            total = report.get("total", 0)
            st.markdown(f"### 🏆 총점: {total}/50")
            st.progress(total / 50)
            st.markdown(f"**💬 총평:** {report.get('summary', '')}")
            st.markdown("**✅ 잘한 점**")
            for s in report.get("strengths", []):
                st.markdown(f"- {s}")
            st.markdown("**📈 개선할 점**")
            for item in report.get("improvements", []):
                st.markdown(f"- {item}")
            st.divider()

        st.markdown("### 📋 대화 기록")
        for msg in st.session_state.voice_history:
            label = "🤵 면접관" if msg["role"] == "assistant" else "🙋 나"
            st.markdown(f"**{label}**: {msg['content']}")

        if st.button("다시 시작"):
            for key in [k for k in st.session_state if k.startswith("voice_")]:
                del st.session_state[key]
            st.rerun()
        return

    # ── 면접 진행 중 ──
    if st.session_state.voice_job_info:
        job = st.session_state.voice_job_info
        st.caption(f"📌 {job.get('company', '')} — {job.get('position', '')} 공고 기반 면접")

    st.markdown(f"### 💬 면접 진행 중 (턴: {st.session_state.voice_turn + 1} / 10)")
    for msg in st.session_state.voice_history:
        label = "🤵 면접관" if msg["role"] == "assistant" else "🙋 나"
        st.markdown(f"**{label}**: {msg['content']}")
    st.divider()

    if st.session_state.get("input_mode") == "⌨️ 텍스트 입력":
        text_answer = st.text_area("답변을 입력하세요", height=100)
        if st.button("제출"):
            if text_answer.strip():
                handle_voice_answer(text_answer.strip())
            else:
                st.warning("답변을 입력해주세요.")
    else:
        if st.button("🎙️ 답변하기 (말이 끝나면 자동 종료)"):
            record_with_ui()


# ──────────────────────────────────────────────
# 페이지: 연습 기록
# ──────────────────────────────────────────────

def show_history():
    """저장된 면접 세션 목록 및 상세 조회"""
    st.title("📋 연습 기록")

    sessions = api_get("sessions?limit=20")
    if isinstance(sessions, dict) and "error" in sessions:
        st.error("기록을 불러올 수 없습니다. API 서버가 실행 중인지 확인하세요.")
        return
    if not sessions:
        st.info("저장된 면접 기록이 없습니다.")
        return

    for s in sessions:
        session_id = s.get("id")
        company = s.get("company") or "회사 미상"
        position = s.get("position") or "직무 미상"
        created = s.get("created_at", "")[:10]
        q_count = s.get("question_count", 0)
        a_count = s.get("answer_count", 0)

        with st.expander(f"#{session_id} | {company} — {position} | {created} | 질문 {q_count}개 / 답변 {a_count}회"):
            try:
                detail = api_get(f"sessions/{session_id}/history")
                for q in detail.get("questions", []):
                    st.markdown(f"**🤵 질문:** {q.get('question_text', '')}")
                    for a in q.get("answers", []):
                        st.markdown(f"**🙋 답변:** {a.get('answer_text', '')}")
                        ev = a.get("evaluation")
                        if ev:
                            cols = st.columns(4)
                            if ev.get("logic_score") is not None:
                                cols[0].metric("논리", ev.get("logic_score"))
                                cols[1].metric("구체성", ev.get("specificity_score"))
                                cols[2].metric("시간", ev.get("time_score"))
                                cols[3].metric("총점", f"{ev.get('total_score')}/15")
                            elif ev.get("total_score") is not None:
                                cols[0].metric("총점", f"{ev.get('total_score')}/100")
                            if ev.get("feedback"):
                                st.caption(f"💬 {ev['feedback']}")
                    st.divider()
            except Exception as e:
                st.error(f"상세 기록 로드 실패: {e}")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main():
    """앱 진입점 - 사이드바 렌더링 후 페이지 라우팅"""
    st.set_page_config(page_title="AI Career Assistant", page_icon="🤖", layout="wide")
    page = render_sidebar()

    if page == "🏠 홈":
        show_home()
    elif page == "📝 자소서 작성":
        show_cover_letter()
    elif page == "🎤 텍스트 기반 면접":
        show_text_interview()
    elif page == "🗣️ 음성 대화형 면접":
        show_voice_interview()
    elif page == "📋 연습 기록":
        show_history()


if __name__ == "__main__":
    main()