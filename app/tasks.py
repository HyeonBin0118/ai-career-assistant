import os
import tempfile
from app.celery_app import celery
from app.services.evaluation import transcribe_audio, evaluate_answer
from app.database import SessionLocal
from app import models


@celery.task(bind=True)
def process_audio_task(self, answer_id: int, audio_bytes: bytes, mime_type: str, question_text: str, duration_seconds: float):
    """
    음성 파일을 백그라운드에서 처리한다.
    1. Whisper API로 텍스트 변환
    2. GPT로 답변 평가
    3. DB에 결과 저장
    """
    db = SessionLocal()
    try:
        # 임시 파일로 저장
        suffix = ".webm" if "webm" in mime_type else ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Whisper 변환
        answer_text = transcribe_audio(tmp_path)
        os.unlink(tmp_path)

        # GPT 평가
        eval_result = evaluate_answer(question_text, answer_text, duration_seconds)

        # DB 업데이트
        answer = db.query(models.Answer).filter(models.Answer.id == answer_id).first()
        if answer:
            answer.answer_text = answer_text
            answer.is_processed = True

            evaluation = models.EvaluationResult(
                answer_id=answer_id,
                logic_score=eval_result["logic_score"],
                specificity_score=eval_result["specificity_score"],
                time_score=eval_result["time_score"],
                total_score=eval_result["total_score"],
                feedback=eval_result["feedback"],
            )
            db.add(evaluation)
            db.commit()

        return {"answer_id": answer_id, "answer_text": answer_text, "status": "completed"}

    except Exception as e:
        db.rollback()
        raise self.retry(exc=e, countdown=5, max_retries=3)
    finally:
        db.close()