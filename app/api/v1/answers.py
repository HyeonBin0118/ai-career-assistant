import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.services.evaluation import transcribe_audio, evaluate_answer
from app.schemas import AnswerWithEval
from app.tasks import process_audio_task
from pydantic import BaseModel
from typing import List

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/questions/{question_id}/answers")
def submit_answer(
    question_id: int,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """음성 파일 업로드 → Celery 비동기 처리"""
    question = db.query(models.Question).filter(
        models.Question.id == question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    audio_bytes = audio.file.read()
    mime_type = audio.content_type or "audio/webm"
    duration_seconds = len(audio_bytes) / 16000

    answer = models.Answer(
        question_id=question_id,
        answer_text=None,
        duration_seconds=duration_seconds,
        is_processed=0,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    process_audio_task.delay(
        answer_id=answer.id,
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        question_text=question.question_text,
        duration_seconds=duration_seconds,
    )

    return {
        "answer_id": answer.id,
        "question_id": question_id,
        "status": "processing",
        "message": "음성 파일이 접수됐습니다. 잠시 후 결과를 확인하세요.",
    }


@router.get("/answers/{answer_id}/status")
def get_answer_status(answer_id: int, db: Session = Depends(get_db)):
    """Celery 비동기 처리 완료 여부 확인 (프론트 폴링용)"""
    answer = db.query(models.Answer).filter(
        models.Answer.id == answer_id
    ).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    if answer.is_processed == 0 or not answer.evaluation:
        return {"answer_id": answer_id, "status": "processing"}

    ev = answer.evaluation
    return {
        "answer_id": answer_id,
        "status": "completed",
        "answer_text": answer.answer_text,
        "logic_score": ev.logic_score,
        "specificity_score": ev.specificity_score,
        "time_score": ev.time_score,
        "total_score": ev.total_score,
        "feedback": ev.feedback,
    }


@router.get("/answers/{answer_id}/feedback")
def get_feedback(answer_id: int, db: Session = Depends(get_db)):
    """답변 피드백 조회 (없으면 GPT 평가 후 저장)"""
    answer = db.query(models.Answer).filter(
        models.Answer.id == answer_id
    ).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    if answer.evaluation:
        ev = answer.evaluation
        return {
            "answer_id": answer_id,
            "answer_text": answer.answer_text,
            "logic_score": ev.logic_score,
            "specificity_score": ev.specificity_score,
            "time_score": ev.time_score,
            "total_score": ev.total_score,
            "feedback": ev.feedback,
        }

    question = db.query(models.Question).filter(
        models.Question.id == answer.question_id
    ).first()

    try:
        result = evaluate_answer(
            question_text=question.question_text,
            answer_text=answer.answer_text,
            duration_seconds=answer.duration_seconds or 60,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평가 실패: {e}")

    evaluation = models.EvaluationResult(
        answer_id=answer_id,
        logic_score=result.get("logic_score"),
        specificity_score=result.get("specificity_score"),
        time_score=result.get("time_score"),
        total_score=result.get("total_score"),
        feedback=result.get("feedback"),
    )
    db.add(evaluation)
    db.commit()

    return {
        "answer_id": answer_id,
        "answer_text": answer.answer_text,
        "logic_score": result.get("logic_score"),
        "specificity_score": result.get("specificity_score"),
        "time_score": result.get("time_score"),
        "total_score": result.get("total_score"),
        "feedback": result.get("feedback"),
    }


class EvaluateTextRequest(BaseModel):
    question_id: int
    answer_text: str
    duration_seconds: float = 60.0


@router.post("/evaluate-text")
def evaluate_text(body: EvaluateTextRequest, db: Session = Depends(get_db)):
    """텍스트 답변 평가 + DB 저장 (면접 연습 텍스트 입력 방식)"""
    question = db.query(models.Question).filter(
        models.Question.id == body.question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    try:
        result = evaluate_answer(
            question_text=question.question_text,
            answer_text=body.answer_text,
            duration_seconds=body.duration_seconds,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 답변 DB 저장
    answer = models.Answer(
        question_id=body.question_id,
        answer_text=body.answer_text,
        duration_seconds=body.duration_seconds,
        is_processed=1,
    )
    db.add(answer)
    db.flush()

    # 평가 결과 DB 저장
    evaluation = models.EvaluationResult(
        answer_id=answer.id,
        logic_score=result.get("logic_score"),
        specificity_score=result.get("specificity_score"),
        time_score=result.get("time_score"),
        total_score=result.get("total_score"),
        feedback=result.get("feedback"),
    )
    db.add(evaluation)
    db.commit()

    return {
        "answer_text": body.answer_text,
        "logic_score": result.get("logic_score"),
        "specificity_score": result.get("specificity_score"),
        "time_score": result.get("time_score"),
        "total_score": result.get("total_score"),
        "feedback": result.get("feedback"),
    }


@router.get("/questions/{question_id}/answers", response_model=List[AnswerWithEval])
def get_question_answers(question_id: int, db: Session = Depends(get_db)):
    """질문별 답변 목록 조회"""
    question = db.query(models.Question).filter(
        models.Question.id == question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question.answers