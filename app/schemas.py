from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class QuestionOut(BaseModel):
    id: int
    category: str
    question_text: str
    model_answer: Optional[str]
    tip: Optional[str]
    difficulty: Optional[int]
    specificity: Optional[int]

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    job_url: str
    resume_text: str


class SessionOut(BaseModel):
    id: int
    company: Optional[str]
    position: Optional[str]
    job_url: str
    questions: List[QuestionOut] = []

    class Config:
        from_attributes = True


# ── 히스토리용 스키마 ──────────────────────────────────────

class EvalOut(BaseModel):
    logic_score: Optional[float]
    specificity_score: Optional[float]
    time_score: Optional[float]
    total_score: Optional[float]
    feedback: Optional[str]

    class Config:
        from_attributes = True


class AnswerWithEval(BaseModel):
    id: int
    answer_text: Optional[str]
    duration_seconds: Optional[float]
    created_at: Optional[datetime]
    evaluation: Optional[EvalOut]

    class Config:
        from_attributes = True


class QuestionHistory(BaseModel):
    id: int
    category: str
    question_text: str
    answers: List[AnswerWithEval] = []

    class Config:
        from_attributes = True


class SessionHistory(BaseModel):
    id: int
    company: Optional[str]
    position: Optional[str]
    job_url: str
    created_at: Optional[datetime]
    questions: List[QuestionHistory] = []

    class Config:
        from_attributes = True


class SessionListItem(BaseModel):
    id: int
    company: Optional[str]
    position: Optional[str]
    job_url: str
    created_at: Optional[datetime]
    question_count: int
    answer_count: int

    class Config:
        from_attributes = True