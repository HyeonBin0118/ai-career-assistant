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
    if duration_seconds < 30:
        time_score = 1
    elif duration_seconds < 60:
        time_score = 3
    elif duration_seconds <= 120:
        time_score = 5
    else:
        time_score = 2

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
면접 질문과 답변을 평가해줘.

**중요: 답변이 질문의 의도와 무관하거나 엉뚱한 내용이면 logic_score를 1점으로 준다.**

평가 기준:
- logic_score: 논리성 (1~5)
  * 1점: 질문과 전혀 무관한 답변이거나 의미없는 내용
  * 2점: 질문과 약간 관련있지만 핵심을 벗어남
  * 3점: 질문에 답하고 있으나 근거가 부족함
  * 4점: 질문에 잘 답하고 있고 근거가 있음
  * 5점: 질문 의도를 완벽히 파악하고 명확한 근거와 함께 답변
- specificity_score: 구체성 (1~5)
  * 1점: 구체적 사례/수치/기술명 전혀 없음
  * 3점: 일부 구체적 내용 포함
  * 5점: 구체적 수치, 사례, 기술명 풍부하게 포함
- total_score: logic_score + specificity_score + {time_score} (시간 점수 고정)
- feedback: 한 줄 개선 피드백 (질문과 무관한 답변이면 그 점을 명확히 지적)

질문: {question_text}
답변: {answer_text}

JSON만 반환해. time_score는 반드시 {time_score}로 고정해.
"""}],
        temperature=0
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    data = json.loads(result)
    data['time_score'] = time_score
    data['total_score'] = data.get('logic_score', 0) + data.get('specificity_score', 0) + time_score
    return data