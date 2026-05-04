import os
import time
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.services.evaluation import transcribe_audio, evaluate_answer
from app.schemas import AnswerWithEval
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
    question = db.query(models.Question).filter(
        models.Question.id == question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    file_path = f"{UPLOAD_DIR}/{question_id}_{int(time.time())}_{audio.filename}"
    with open(file_path, "wb") as f:
        f.write(audio.file.read())

    try:
        answer_text = transcribe_audio(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Whisper 변환 실패: {e}")

    file_size = os.path.getsize(file_path)
    duration_seconds = file_size / 16000

    answer = models.Answer(
        question_id=question_id,
        answer_text=answer_text,
        audio_path=file_path,
        duration_seconds=duration_seconds,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    return {
        "answer_id": answer.id,
        "question_id": question_id,
        "answer_text": answer_text,
        "duration_seconds": duration_seconds,
    }


@router.get("/answers/{answer_id}/feedback")
def get_feedback(answer_id: int, db: Session = Depends(get_db)):
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
    question = db.query(models.Question).filter(
        models.Question.id == question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question.answers