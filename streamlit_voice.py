"""AI 음성 면접 시뮬레이터 - Streamlit UI"""

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

SYSTEM_PROMPT = """당신은 IT 기업의 시니어 개발자 면접관입니다.
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
# LLM 호출 함수
# ──────────────────────────────────────────────

def build_job_context(job_info: dict) -> str:
    """채용공고 정보를 프롬프트에 주입할 문자열로 변환"""
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
    """GPT-4o-mini에 메시지를 보내고 응답을 반환하는 공통 함수"""
    system = SYSTEM_PROMPT + build_job_context(job_info)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}] + messages,
    )
    return response.choices[0].message.content


def get_opening_question(name: str, role: str, job_info: dict = None) -> str:
    """면접 첫 질문 생성"""
    return ask_llm(
        [{"role": "user", "content": f"지원자 이름: {name}, 지원 직무: {role}. 면접을 시작해주세요. 첫 질문을 해주세요."}],
        job_info,
    )


def get_next_question(history: list, job_info: dict = None) -> str:
    """대화 히스토리 기반 꼬리질문 생성"""
    return ask_llm(history, job_info)


def generate_report(history: list, job_info: dict = None) -> dict:
    """면접 종료 후 항목별 평가 리포트 생성"""
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
- total: 총점 (0~100)
- strengths: 잘한 점 2개 (리스트)
- improvements: 개선할 점 2개 (리스트)
- summary: 한 줄 총평

JSON만 반환해.

대화:
{json.dumps(history, ensure_ascii=False)}
"""},
        ],
        temperature=0,
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(result)


# ──────────────────────────────────────────────
# DB 저장/조회
# ──────────────────────────────────────────────

def save_to_db(name: str, role: str, job_info: dict, conversation: list, report: dict) -> dict:
    """면접 대화 기록과 평가 리포트를 FastAPI → PostgreSQL에 저장"""
    payload = {
        "name": name,
        "role": role,
        "job_url": "",
        "company": job_info.get("company", "") if job_info else "",
        "position": job_info.get("position", role) if job_info else role,
        "conversation": conversation,
        "report": report,
    }
    try:
        return requests.post(f"{API_BASE}/sessions/voice", json=payload).json()
    except Exception as e:
        return {"error": str(e)}


def fetch_sessions() -> list:
    """저장된 면접 세션 목록 조회"""
    try:
        return requests.get(f"{API_BASE}/sessions?limit=20").json()
    except Exception as e:
        st.error(f"기록을 불러올 수 없습니다: {e}")
        return []


def fetch_session_detail(session_id: int) -> dict:
    """세션 상세 조회 (대화 기록 + 평가)"""
    return requests.get(f"{API_BASE}/sessions/{session_id}/history").json()


# ──────────────────────────────────────────────
# 답변 처리
# ──────────────────────────────────────────────

def handle_answer(answer_text: str):
    """답변 텍스트를 히스토리에 추가하고 다음 단계(꼬리질문 or 종료) 처리"""
    st.session_state.history.append({"role": "user", "content": answer_text})
    st.session_state.turn += 1

    if st.session_state.turn >= 10:
        # 면접 종료 → 리포트 생성 → DB 저장
        closing = "수고하셨습니다. 오늘 면접은 여기서 마치겠습니다. 좋은 결과 있으시길 바랍니다."
        st.session_state.history.append({"role": "assistant", "content": closing})
        speak(closing)

        with st.spinner("면접 결과 분석 중..."):
            report = generate_report(st.session_state.history, st.session_state.get("job_info"))
            st.session_state.report = report

        with st.spinner("면접 기록 저장 중..."):
            result = save_to_db(
                st.session_state.get("name", ""),
                st.session_state.get("role", ""),
                st.session_state.get("job_info"),
                st.session_state.history,
                report,
            )
            if "error" not in result:
                st.session_state.saved_session_id = result.get("session_id")

        st.session_state.finished = True
    else:
        # 꼬리질문 생성
        with st.spinner("면접관이 생각 중..."):
            next_q = get_next_question(st.session_state.history, st.session_state.get("job_info"))
            st.session_state.history.append({"role": "assistant", "content": next_q})
            speak(next_q)

    st.rerun()


# ──────────────────────────────────────────────
# 사이드바 설정
# ──────────────────────────────────────────────

def render_sidebar() -> str:
    """사이드바 렌더링. 페이지 선택값 반환."""
    with st.sidebar:
        # 페이지 전환
        st.markdown("## 📌 메뉴")
        page = st.radio("", ["🎤 면접 시작", "📋 기록 보기"], label_visibility="collapsed")
        st.divider()

        # 마이크 선택
        devices = sd.query_devices()
        input_devices = {
            f"{i}: {d['name']}": i
            for i, d in enumerate(devices)
            if d["max_input_channels"] > 0
        }

        st.markdown("### 🎙️ 마이크 설정")
        selected = st.selectbox("마이크 선택", list(input_devices.keys()))
        st.session_state.mic_index = input_devices[selected]

        # Whisper 모델
        st.markdown("### 🧠 STT 모델 설정")
        model_map = {
            "base (빠름, 정확도 낮음)": "base",
            "medium (권장, 정확도 높음)": "medium",
            "large (최고 정확도, 느림)": "large",
        }
        selected_model = st.selectbox("Whisper 모델", list(model_map.keys()), index=1)
        st.session_state.whisper_model = model_map[selected_model]
        st.caption("⚠️ 모델 변경 시 첫 인식 때 다운로드가 발생할 수 있습니다.")

        # 무음 감지 임계값
        st.markdown("### 🔇 무음 감지 민감도")
        threshold_map = {
            "낮음 - 조용한 환경 (0.01)": 0.01,
            "보통 - 일반 환경 (0.02)": 0.02,
            "높음 - 블루투스/노이즈 많은 환경 (0.03)": 0.03,
            "매우 높음 - 노이즈 심한 환경 (0.05)": 0.05,
        }
        selected_threshold = st.selectbox("무음 감지 임계값", list(threshold_map.keys()), index=2)
        st.session_state.silence_threshold = threshold_map[selected_threshold]
        st.caption("값이 높을수록 더 쉽게 무음으로 판단합니다.")

        # 입력 방식
        st.markdown("### ⌨️ 입력 방식")
        st.session_state.input_mode = st.radio(
            "답변 입력 방식",
            ["🎙️ 음성 입력", "⌨️ 텍스트 입력"],
            index=1,
        )

    return page


# ──────────────────────────────────────────────
# 음성 녹음 UI
# ──────────────────────────────────────────────

def record_with_ui():
    """음성 녹음 + 실시간 스펙트럼/타이머 표시 후 STT 처리"""
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

    # 실시간 스펙트럼 + 타이머
    ui_status = st.empty()
    start_time = time.time()
    while not shared_state["done"]:
        elapsed = time.time() - start_time
        bars = min(int(shared_state["level"] * 400), 20)
        bar_str = "█" * bars + "░" * (20 - bars)
        ui_status.markdown(f"🎙️ **녹음 중** &nbsp;&nbsp; ⏱️ **{elapsed:.1f}초**\n\n`{bar_str}`")
        time.sleep(0.05)

    t.join()
    elapsed_total = time.time() - start_time
    ui_status.markdown(f"✅ 녹음 완료 &nbsp;&nbsp; ⏱️ **{elapsed_total:.1f}초**")

    # STT 처리
    audio_path = shared_state["path"]
    if not audio_path:
        st.warning("녹음에 실패했습니다. 다시 시도해주세요.")
        return

    with st.spinner("답변 인식 중..."):
        answer_text = transcribe(audio_path, st.session_state.get("whisper_model", "medium"))
        cleanup_audio_file(audio_path)

    if answer_text:
        handle_answer(answer_text)
    else:
        st.warning("답변이 인식되지 않았습니다. 다시 시도해주세요.")


# ──────────────────────────────────────────────
# 페이지: 면접 기록 조회
# ──────────────────────────────────────────────

def show_history():
    """저장된 면접 기록 목록 및 상세 조회 페이지"""
    st.title("📋 면접 기록")

    sessions = fetch_sessions()
    if not sessions:
        st.info("저장된 면접 기록이 없습니다.")
        return

    for s in sessions:
        session_id = s.get("id")
        company = s.get("company") or "회사 미상"
        position = s.get("position") or "직무 미상"
        created = s.get("created_at", "")[:10]

        with st.expander(f"#{session_id} | {company} — {position} | {created}"):
            try:
                detail = fetch_session_detail(session_id)
                for q in detail.get("questions", []):
                    st.markdown(f"**🤵 면접관:** {q.get('question_text', '')}")
                    for a in q.get("answers", []):
                        st.markdown(f"**🙋 나:** {a.get('answer_text', '')}")
                        if a.get("evaluation"):
                            score = a["evaluation"].get("total_score")
                            feedback = a["evaluation"].get("feedback", "")
                            if score is not None:
                                st.caption(f"점수: {score}점 | {feedback}")
                    st.divider()
            except Exception as e:
                st.error(f"상세 기록 로드 실패: {e}")


# ──────────────────────────────────────────────
# 페이지: 면접 진행
# ──────────────────────────────────────────────

def show_interview():
    """면접 시작 → 진행 → 종료 리포트까지의 메인 페이지"""
    st.title("🎤 AI 음성 면접 시뮬레이터")

    # 세션 상태 초기화
    if "started" not in st.session_state:
        st.session_state.started = False
        st.session_state.history = []
        st.session_state.turn = 0
        st.session_state.finished = False
        st.session_state.job_info = None
        st.session_state.report = None

    # ── 시작 전: 정보 입력 ──
    if not st.session_state.started:
        st.markdown("면접 정보를 입력하고 시작하세요.")
        name = st.text_input("이름", placeholder="홍길동")
        role = st.text_input("지원 직무", placeholder="AI 백엔드 개발자")
        job_url = st.text_input("채용공고 URL (선택)", placeholder="https://www.jobkorea.co.kr/...")
        st.caption("URL 입력 시 공고 맞춤 질문이 생성됩니다.")

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
                st.session_state.history.append({"role": "assistant", "content": first_q})
                st.session_state.name = name
                st.session_state.role = role
                st.session_state.job_info = job_info
                st.session_state.started = True
                speak(first_q)
            st.rerun()
        return

    # ── 면접 종료: 리포트 ──
    if st.session_state.finished:
        st.success("면접이 종료되었습니다.")
        if st.session_state.get("saved_session_id"):
            st.info(f"📁 면접 기록이 저장되었습니다. (세션 ID: {st.session_state.saved_session_id})")

        report = st.session_state.get("report", {})
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
            st.markdown(f"### 🏆 총점: {total}/100")
            st.progress(total / 100)
            st.markdown(f"**💬 총평:** {report.get('summary', '')}")

            st.markdown("**✅ 잘한 점**")
            for s in report.get("strengths", []):
                st.markdown(f"- {s}")
            st.markdown("**📈 개선할 점**")
            for item in report.get("improvements", []):
                st.markdown(f"- {item}")
            st.divider()

        # 대화 기록 출력
        st.markdown("### 📋 대화 기록")
        for msg in st.session_state.history:
            label = "🤵 면접관" if msg["role"] == "assistant" else "🙋 나"
            st.markdown(f"**{label}**: {msg['content']}")

        if st.button("다시 시작"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return

    # ── 면접 진행 중 ──
    if st.session_state.job_info:
        job = st.session_state.job_info
        st.caption(f"📌 {job.get('company', '')} — {job.get('position', '')} 공고 기반 면접")

    st.markdown(f"### 💬 면접 진행 중 (턴: {st.session_state.turn + 1} / 10)")
    for msg in st.session_state.history:
        label = "🤵 면접관" if msg["role"] == "assistant" else "🙋 나"
        st.markdown(f"**{label}**: {msg['content']}")
    st.divider()

    # 입력 방식에 따른 분기
    if st.session_state.get("input_mode") == "⌨️ 텍스트 입력":
        text_answer = st.text_area("답변을 입력하세요", placeholder="답변을 입력하고 제출 버튼을 누르세요", height=100)
        if st.button("제출"):
            if text_answer.strip():
                handle_answer(text_answer.strip())
            else:
                st.warning("답변을 입력해주세요.")
    else:
        if st.button("🎙️ 답변하기 (말이 끝나면 자동 종료)"):
            record_with_ui()


# ──────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────

def main():
    """앱 진입점 - 사이드바 렌더링 후 페이지 라우팅"""
    page = render_sidebar()
    if page == "📋 기록 보기":
        show_history()
    else:
        show_interview()


if __name__ == "__main__":
    main()