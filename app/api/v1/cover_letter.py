from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.services.interview import generate_cover_letter, evaluate_cover_letter, match_resume, get_cached_job, crawl_job_posting, extract_job_info, set_cached_job
from pydantic import BaseModel

router = APIRouter()


class CoverLetterRequest(BaseModel):
    session_id: int
    length: int = 500
    custom_format: str = ""


class EvaluateRequest(BaseModel):
    session_id: int
    cover_letter: dict


@router.post("/cover-letter/generate")
def generate(body: CoverLetterRequest, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == body.session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    job_info = get_cached_job(session.job_url)
    if not job_info:
        job_content = crawl_job_posting(session.job_url)
        job_info = extract_job_info(job_content)
        set_cached_job(session.job_url, job_info)

    match_result = match_resume(session.resume_text, job_info)

    try:
        cover_letter = generate_cover_letter(
            resume_text=session.resume_text,
            job_info=job_info,
            match_result=match_result,
            length=body.length,
            custom_format=body.custom_format,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "session_id": body.session_id,
        "cover_letter": cover_letter,
        "match_result": match_result,
        "job_info": {
            "company": job_info.get("company"),
            "position": job_info.get("position"),
        }
    }


@router.post("/cover-letter/evaluate")
def evaluate(body: EvaluateRequest, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.id == body.session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    job_info = get_cached_job(session.job_url)
    if not job_info:
        job_content = crawl_job_posting(session.job_url)
        job_info = extract_job_info(job_content)
        set_cached_job(session.job_url, job_info)

    try:
        result = evaluate_cover_letter(body.cover_letter, job_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result