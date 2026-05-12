from dotenv import load_dotenv
load_dotenv(dotenv_path=r"C:\Users\VisualS2\Desktop\AI_LAB\git\ai-career-assistant\.env")

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(__file__))

from voice.recorder import record_until_silence, cleanup_audio_file
from voice.stt import transcribe
from voice.tts import speak
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """당신은 IT 기업의 시니어 개발자 면접관입니다.
다음 규칙을 반드시 지키세요:
- 한 번에 질문 하나만 하세요
- 지원자 답변의 핵심 키워드를 잡아 꼬리질문을 하세요
- 모호한 답변은 구체적으로 파고드세요
- "~하셨군요. 그렇다면 ~는 어떻게 하셨나요?" 형태를 자주 사용하세요
- 압박보다는 대화하듯 자연스럽게 진행하세요
- 답변이 구체적이면 다음 주제로 넘어가세요
- 10턴이 지나면 면접을 마무리하세요"""


def get_opening_question(name: str, role: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"지원자 이름: {name}, 지원 직무: {role}. 면접을 시작해주세요. 첫 질문을 해주세요."}
        ]
    )
    return response.choices[0].message.content


def get_next_question(conversation_history: list) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
    )
    return response.choices[0].message.content


def run_interview():
    # 마이크 선택 사이드바 추가
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
    st.title("🎤 AI 음성 면접 시뮬레이터")

    # 세션 상태 초기화
    if "started" not in st.session_state:
        st.session_state.started = False
        st.session_state.history = []
        st.session_state.turn = 0
        st.session_state.finished = False

    # 시작 전 입력폼
    if not st.session_state.started:
        st.markdown("면접 정보를 입력하고 시작하세요.")
        name = st.text_input("이름", placeholder="홍길동")
        role = st.text_input("지원 직무", placeholder="AI 백엔드 개발자")

        if st.button("면접 시작", disabled=not (name and role)):
            with st.spinner("면접관이 준비 중입니다..."):
                first_question = get_opening_question(name, role)
                st.session_state.history.append({
                    "role": "assistant",
                    "content": first_question
                })
                st.session_state.name = name
                st.session_state.role = role
                st.session_state.started = True
                speak(first_question)
            st.rerun()
        return

    # 면접 종료
    if st.session_state.finished:
        st.success("면접이 종료되었습니다.")
        st.markdown("### 📋 대화 기록")
        for msg in st.session_state.history:
            role_label = "🤵 면접관" if msg["role"] == "assistant" else "🙋 나"
            st.markdown(f"**{role_label}**: {msg['content']}")

        if st.button("다시 시작"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return

    # 대화 기록 출력
    st.markdown(f"### 💬 면접 진행 중 (턴: {st.session_state.turn + 1} / 10)")
    for msg in st.session_state.history:
        role_label = "🤵 면접관" if msg["role"] == "assistant" else "🙋 나"
        st.markdown(f"**{role_label}**: {msg['content']}")

    st.divider()

    # 녹음 버튼
    if st.button("🎙️ 답변하기 (말이 끝나면 자동 종료)"):
        with st.spinner("녹음 중... 말을 마치면 잠시 기다려주세요"):
            audio_path = record_until_silence(
                device_index=st.session_state.get("mic_index")
            )

        if audio_path:
            with st.spinner("답변 인식 중..."):
                answer_text = transcribe(audio_path)
                cleanup_audio_file(audio_path)

            if answer_text:
                st.session_state.history.append({
                    "role": "user",
                    "content": answer_text
                })
                st.session_state.turn += 1

                # 10턴 이상이면 종료
                if st.session_state.turn >= 10:
                    closing = "수고하셨습니다. 오늘 면접은 여기서 마치겠습니다. 좋은 결과 있으시길 바랍니다."
                    st.session_state.history.append({
                        "role": "assistant",
                        "content": closing
                    })
                    speak(closing)
                    st.session_state.finished = True
                else:
                    with st.spinner("면접관이 생각 중..."):
                        next_q = get_next_question(st.session_state.history)
                        st.session_state.history.append({
                            "role": "assistant",
                            "content": next_q
                        })
                        speak(next_q)

                st.rerun()
            else:
                st.warning("답변이 인식되지 않았습니다. 다시 시도해주세요.")
        else:
            st.warning("녹음에 실패했습니다. 다시 시도해주세요.")


if __name__ == "__main__":
    run_interview()