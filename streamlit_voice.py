from dotenv import load_dotenv
load_dotenv(dotenv_path=r"C:\Users\VisualS2\Desktop\AI_LAB\git\ai-career-assistant\.env")

import streamlit as st
import sys
import os
import threading
import time
import json

sys.path.append(os.path.dirname(__file__))

from voice.recorder import record_until_silence, cleanup_audio_file
from voice.stt import transcribe
from voice.tts import speak
from openai import OpenAI
from app.services.interview import crawl_job_posting, extract_job_info

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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


def build_job_context(job_info: dict) -> str:
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


def get_opening_question(name: str, role: str, job_info: dict = None) -> str:
    job_context = build_job_context(job_info)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + job_context},
            {"role": "user", "content": f"지원자 이름: {name}, 지원 직무: {role}. 면접을 시작해주세요. 첫 질문을 해주세요."}
        ]
    )
    return response.choices[0].message.content


def get_next_question(conversation_history: list, job_info: dict = None) -> str:
    job_context = build_job_context(job_info)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT + job_context}] + conversation_history
    )
    return response.choices[0].message.content


def generate_report(conversation_history: list, job_info: dict = None) -> dict:
    job_context = f"직무: {job_info.get('position', '')} / 회사: {job_info.get('company', '')}" if job_info else ""
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
{json.dumps(conversation_history, ensure_ascii=False)}
"""}
        ],
        temperature=0
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(result)

def save_to_db(name: str, role: str, job_info: dict, conversation: list, report: dict):
    import requests
    payload = {
        "name": name,
        "role": role,
        "job_url": "",
        "company": job_info.get("company", "") if job_info else "",
        "position": job_info.get("position", role) if job_info else role,
        "conversation": conversation,
        "report": report
    }
    try:
        res = requests.post("http://localhost:8000/api/v1/sessions/voice", json=payload)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def handle_answer(answer_text: str):
    """답변 처리 공통 로직"""
    st.session_state.history.append({
        "role": "user",
        "content": answer_text
    })
    st.session_state.turn += 1

    if st.session_state.turn >= 10:
        closing = "수고하셨습니다. 오늘 면접은 여기서 마치겠습니다. 좋은 결과 있으시길 바랍니다."
        st.session_state.history.append({
            "role": "assistant",
            "content": closing
        })
        speak(closing)
        with st.spinner("면접 결과 분석 중..."):
            report = generate_report(
                st.session_state.history,
                job_info=st.session_state.get("job_info")
            )
            st.session_state.report = report
        with st.spinner("면접 기록 저장 중..."):
            save_result = save_to_db(
                name=st.session_state.get("name", ""),
                role=st.session_state.get("role", ""),
                job_info=st.session_state.get("job_info"),
                conversation=st.session_state.history,
                report=report
            )
            if "error" not in save_result:
                st.session_state.saved_session_id = save_result.get("session_id")
        st.session_state.finished = True

    else:
        with st.spinner("면접관이 생각 중..."):
            next_q = get_next_question(
                st.session_state.history,
                job_info=st.session_state.get("job_info")
            )
            st.session_state.history.append({
                "role": "assistant",
                "content": next_q
            })
            speak(next_q)

    st.rerun()


def run_interview():
    st.title("🎤 AI 음성 면접 시뮬레이터")

    import sounddevice as sd
    devices = sd.query_devices()
    input_devices = {
        f"{i}: {d['name']}": i
        for i, d in enumerate(devices)
        if d['max_input_channels'] > 0
    }

    with st.sidebar:
        st.markdown("### 🎙️ 마이크 설정")
        selected = st.selectbox("마이크 선택", list(input_devices.keys()))
        st.session_state.mic_index = input_devices[selected]

        st.markdown("### 🧠 STT 모델 설정")
        model_options = {
            "base (빠름, 정확도 낮음)": "base",
            "medium (권장, 정확도 높음)": "medium",
            "large (최고 정확도, 느림)": "large"
        }
        selected_model = st.selectbox("Whisper 모델", list(model_options.keys()), index=1)
        st.session_state.whisper_model = model_options[selected_model]
        st.caption("⚠️ 모델 변경 시 첫 인식 때 다운로드가 발생할 수 있습니다.")

        st.markdown("### 🔇 무음 감지 민감도")
        threshold_options = {
            "낮음 - 조용한 환경 (0.01)": 0.01,
            "보통 - 일반 환경 (0.02)": 0.02,
            "높음 - 블루투스/노이즈 많은 환경 (0.03)": 0.03,
            "매우 높음 - 노이즈 심한 환경 (0.05)": 0.05,
        }
        selected_threshold = st.selectbox(
            "무음 감지 임계값",
            list(threshold_options.keys()),
            index=2
        )
        st.session_state.silence_threshold = threshold_options[selected_threshold]
        st.caption("값이 높을수록 더 쉽게 무음으로 판단합니다.")

        st.markdown("### ⌨️ 입력 방식")
        input_mode = st.radio(
            "답변 입력 방식",
            ["🎙️ 음성 입력", "⌨️ 텍스트 입력"],
            index=1
        )
        st.session_state.input_mode = input_mode

    if "started" not in st.session_state:
        st.session_state.started = False
        st.session_state.history = []
        st.session_state.turn = 0
        st.session_state.finished = False
        st.session_state.job_info = None
        st.session_state.report = None

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
                first_question = get_opening_question(name, role, job_info)
                st.session_state.history.append({
                    "role": "assistant",
                    "content": first_question
                })
                st.session_state.name = name
                st.session_state.role = role
                st.session_state.job_info = job_info
                st.session_state.started = True
                speak(first_question)
            st.rerun()
        return

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
            for i in report.get("improvements", []):
                st.markdown(f"- {i}")

            st.divider()

        st.markdown("### 📋 대화 기록")
        for msg in st.session_state.history:
            role_label = "🤵 면접관" if msg["role"] == "assistant" else "🙋 나"
            st.markdown(f"**{role_label}**: {msg['content']}")

        if st.button("다시 시작"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return

    if st.session_state.job_info:
        job = st.session_state.job_info
        st.caption(f"📌 {job.get('company', '')} — {job.get('position', '')} 공고 기반 면접")

    st.markdown(f"### 💬 면접 진행 중 (턴: {st.session_state.turn + 1} / 10)")
    for msg in st.session_state.history:
        role_label = "🤵 면접관" if msg["role"] == "assistant" else "🙋 나"
        st.markdown(f"**{role_label}**: {msg['content']}")

    st.divider()

    if st.session_state.get("input_mode") == "⌨️ 텍스트 입력":
        text_answer = st.text_area("답변을 입력하세요", placeholder="답변을 입력하고 제출 버튼을 누르세요", height=100)
        if st.button("제출"):
            answer_text = text_answer.strip()
            if answer_text:
                handle_answer(answer_text)
            else:
                st.warning("답변을 입력해주세요.")
    else:
        if st.button("🎙️ 답변하기 (말이 끝나면 자동 종료)"):
            shared_state = {"level": 0.0, "done": False, "path": None}

            def record_thread():
                path = record_until_silence(
                    device_index=st.session_state.get("mic_index"),
                    shared_state=shared_state,
                    silence_threshold=st.session_state.get("silence_threshold", 0.02)
                )
                shared_state["path"] = path
                shared_state["done"] = True

            t = threading.Thread(target=record_thread)
            t.start()

            ui_status = st.empty()
            start_time = time.time()

            while not shared_state["done"]:
                elapsed = time.time() - start_time
                level = shared_state["level"]
                bars = min(int(level * 400), 20)
                bar_str = "█" * bars + "░" * (20 - bars)
                ui_status.markdown(
                    f"🎙️ **녹음 중** &nbsp;&nbsp; ⏱️ **{elapsed:.1f}초**\n\n"
                    f"`{bar_str}`"
                )
                time.sleep(0.05)

            t.join()
            elapsed_total = time.time() - start_time
            ui_status.markdown(f"✅ 녹음 완료 &nbsp;&nbsp; ⏱️ **{elapsed_total:.1f}초**")
            audio_path = shared_state["path"]

            if audio_path:
                with st.spinner("답변 인식 중..."):
                    answer_text = transcribe(
                        audio_path,
                        model_size=st.session_state.get("whisper_model", "medium")
                    )
                    cleanup_audio_file(audio_path)

                if answer_text:
                    handle_answer(answer_text)
                else:
                    st.warning("답변이 인식되지 않았습니다. 다시 시도해주세요.")
            else:
                st.warning("녹음에 실패했습니다. 다시 시도해주세요.")


if __name__ == "__main__":
    run_interview()