import json
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def transcribe_audio(audio_file_path: str) -> str:
    """
    Whisper API로 음성 파일을 텍스트로 변환한다.
    """
    with open(audio_file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ko"
        )
    return transcript.text


def evaluate_answer(question_text: str, answer_text: str, duration_seconds: float) -> dict:
    """
    GPT로 면접 답변을 평가한다.
    논리성, 구체성, 시간 관리 세 가지 지표로 점수를 산출한다.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
면접 질문과 답변을 평가해줘.

평가 기준:
- logic_score: 논리성 (1~5) — 답변이 논리적으로 구성되어 있는가
- specificity_score: 구체성 (1~5) — 구체적인 사례나 수치를 포함하는가
- time_score: 시간 관리 (1~5) — 적절한 답변 길이인가 (60~120초가 이상적)
  * 30초 미만: 1점
  * 30~60초: 3점
  * 60~120초: 5점
  * 120초 초과: 2점
- total_score: 총점 (3~15)
- feedback: 한 줄 개선 피드백

질문: {question_text}
답변: {answer_text}
답변 시간: {duration_seconds:.1f}초

JSON만 반환해.
"""}],
        temperature=0
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(result)