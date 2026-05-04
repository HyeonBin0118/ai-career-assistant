from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import SessionCreate, SessionOut, SessionHistory, SessionListItem
from app.services import interview
from app import models
from typing import List
from pydantic import BaseModel

router = APIRouter()


@router.post("/sessions", response_model=SessionOut)
def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    try:
        session = interview.create_session(
            db=db,
            job_url=body.job_url,
            resume_text=body.resume_text,
        )
        return session
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=List[SessionListItem])
def list_sessions(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    sessions = (
        db.query(models.InterviewSession)
        .order_by(models.InterviewSession.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    result = []
    for s in sessions:
        answer_count = sum(len(q.answers) for q in s.questions)
        result.append(SessionListItem(
            id=s.id,
            company=s.company,
            position=s.position,
            job_url=s.job_url,
            created_at=s.created_at,
            question_count=len(s.questions),
            answer_count=answer_count,
        ))
    return result


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/history", response_model=SessionHistory)
def get_session_history(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/category-stats")
def get_category_stats(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    stats = {}
    for question in session.questions:
        category = question.category
        scores = []
        for answer in question.answers:
            if answer.evaluation and answer.evaluation.total_score is not None:
                scores.append(answer.evaluation.total_score)
        if category not in stats:
            stats[category] = {"scores": [], "question_count": 0}
        stats[category]["scores"].extend(scores)
        stats[category]["question_count"] += 1

    result = []
    for category, data in stats.items():
        scores = data["scores"]
        result.append({
            "category": category,
            "question_count": data["question_count"],
            "answer_count": len(scores),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
            "max_score": max(scores) if scores else None,
            "min_score": min(scores) if scores else None,
        })

    return {"session_id": session_id, "categories": result}