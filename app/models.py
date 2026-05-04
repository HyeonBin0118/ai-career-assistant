from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class InterviewSession(Base):
    """
    면접 세션.
    이력서와 채용공고 한 쌍당 세션 하나가 생성된다.
    """
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    resume_text = Column(Text, nullable=False)
    job_url = Column(String(500), nullable=False)
    company = Column(String(200))
    position = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    questions = relationship("Question", back_populates="session", cascade="all, delete")


class Question(Base):
    """
    생성된 면접 질문.
    카테고리(보유스킬/부족스킬/직무/인성)와 난이도, 구체성 점수를 함께 저장.
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    category = Column(String(50), nullable=False)   # 보유 스킬 / 부족 스킬 / 직무·회사 / 인성
    question_text = Column(Text, nullable=False)
    model_answer = Column(Text)
    tip = Column(Text)
    difficulty = Column(Integer)                    # 1~5
    specificity = Column(Integer)                   # 1~5
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete")


class Answer(Base):
    """
    사용자 답변.
    텍스트(Whisper 변환 결과)와 음성 파일 경로를 함께 저장.
    같은 질문에 여러 번 답할 수 있어 반복 연습 추이 추적이 가능하다.
    """
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text)                      # Whisper 변환 텍스트
    audio_path = Column(String(500))                # 음성 파일 경로
    duration_seconds = Column(Float)                # 답변 시간
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    question = relationship("Question", back_populates="answers")
    evaluation = relationship("EvaluationResult", back_populates="answer", uselist=False)


class EvaluationResult(Base):
    """
    GPT 답변 평가 결과.
    논리성/구체성/시간 관리 세 지표로 점수를 산출한다.
    Answer와 1:1 관계.
    """
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=False)
    logic_score = Column(Float)                     # 논리성 1~5
    specificity_score = Column(Float)               # 구체성 1~5
    time_score = Column(Float)                      # 시간 관리 1~5 (권장 1~2분)
    total_score = Column(Float)                     # 총점 (15점 만점)
    feedback = Column(Text)                         # GPT 한 줄 피드백
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answer = relationship("Answer", back_populates="evaluation")