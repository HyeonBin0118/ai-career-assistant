import httpx
import json
import re
import time
from bs4 import BeautifulSoup
from openai import OpenAI
from sqlalchemy.orm import Session
from app.core.config import settings
from app import models
from app.services.cache import get_cached_job, set_cached_job

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def crawl_job_posting(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
    
    # 인코딩 자동 감지 후 디코딩
    try:
        text_content = response.content.decode('utf-8')
    except UnicodeDecodeError:
        text_content = response.content.decode('euc-kr', errors='ignore')

    soup = BeautifulSoup(text_content, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    for tag in soup.find_all(class_=re.compile(r"(ad|banner|menu|popup)", re.I)):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"[^\w\s가-힣.,·\-/()%+]", " ", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    seen = set()
    cleaned = []
    for line in lines:
        if line not in seen and len(line) > 1:
            seen.add(line)
            cleaned.append(line)

    return "\n".join(cleaned)


def extract_job_info(content: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
아래 채용공고 텍스트에서 다음 항목을 JSON으로 추출해줘.
- company, position, required_skills, preferred_skills, experience, summary
JSON만 반환해.
텍스트: {content[:3000]}
"""}],
        temperature=0
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    print(f"[DEBUG] extract_job_info result: {result[:200]}")
    return json.loads(result)


def generate_questions(resume_text: str, job_info: dict, match_result: dict) -> list:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
아래 정보를 바탕으로 면접 예상 질문 8개와 모범 답안을 생성해줘.
질문 구성:
- 보유 스킬 기반 심화 질문 3개
- 부족 스킬 관련 질문 2개
- 직무/회사 관련 질문 2개
- 인성/경험 질문 1개

JSON 배열로 반환해줘:
[
  {{
    "category": "보유 스킬",
    "question": "질문 내용",
    "answer": "모범 답안 (200자 내외)",
    "tip": "답변 시 주의할 점 한 줄",
    "difficulty": 3,
    "specificity": 3
  }}
]

채용공고: {json.dumps(job_info, ensure_ascii=False)}
보유 스킬: {match_result.get("matched_skills", [])}
부족 스킬: {match_result.get("missing_skills", [])}
이력서: {resume_text[:2000]}
JSON 배열만 반환해.
"""}],
        temperature=0.7
    )
    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)


def match_resume(resume_text: str, job_info: dict) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
이력서와 채용공고를 비교해서 JSON으로 반환해줘.
- matched_skills, missing_skills, score(0~100), summary
채용공고: {json.dumps(job_info, ensure_ascii=False)}
이력서: {resume_text[:3000]}
JSON만 반환해.
"""}],
        temperature=0
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(result)


def create_session(db: Session, job_url: str, resume_text: str) -> models.InterviewSession:
    total_start = time.time()

    # 1. 캐시 확인 → 없으면 크롤링
    job_info = get_cached_job(job_url)
    if job_info:
        print(f"[CACHE HIT] {job_url}")
        job_info_time = 0.0
    else:
        print(f"[CACHE MISS] {job_url}")
        t = time.time()
        job_content = crawl_job_posting(job_url)
        job_info = extract_job_info(job_content)
        set_cached_job(job_url, job_info)
        job_info_time = time.time() - t

    # 2. 이력서 매칭
    t = time.time()
    match_result = match_resume(resume_text, job_info)
    match_time = time.time() - t

    # 3. 면접 질문 생성
    t = time.time()
    questions_data = generate_questions(resume_text, job_info, match_result)
    question_time = time.time() - t

    total_time = time.time() - total_start

    if job_info_time > 0:
        print(f"[TIMING] 크롤링+공고분석: {job_info_time*1000:.0f}ms")
    print(f"[TIMING] 이력서 매칭: {match_time*1000:.0f}ms")
    print(f"[TIMING] 질문 생성: {question_time*1000:.0f}ms")
    print(f"[TIMING] 전체 응답시간: {total_time*1000:.0f}ms")

    # 4. DB 저장
    session = models.InterviewSession(
        resume_text=resume_text,
        job_url=job_url,
        company=job_info.get("company"),
        position=job_info.get("position"),
    )
    db.add(session)
    db.flush()

    for q in questions_data:
        question = models.Question(
            session_id=session.id,
            category=q.get("category", "기타"),
            question_text=q.get("question", ""),
            model_answer=q.get("answer"),
            tip=q.get("tip"),
            difficulty=q.get("difficulty"),
            specificity=q.get("specificity"),
        )
        db.add(question)

    db.commit()
    db.refresh(session)
    return session

def generate_cover_letter(resume_text: str, job_info: dict, match_result: dict, length: int = 500, custom_format: str = "") -> dict:
    if custom_format:
        format_guide = f"""
아래 자소서 형식에 맞게 작성해줘. 각 항목명을 JSON 키로 그대로 사용해줘. 번호는 제거해줘.
형식:
{custom_format}
"""
    else:
        format_guide = """아래 세 가지 항목으로 작성해줘. JSON 키는 반드시 한글로 사용해줘. - 지원동기 - 직무경험 - 입사후포부"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
이력서, 채용공고, 매칭 결과를 바탕으로 자소서 초안을 작성해줘.
{format_guide}
각 항목 {length}자 내외로 작성해줘.
채용공고: {json.dumps(job_info, ensure_ascii=False)}
매칭결과: {json.dumps(match_result, ensure_ascii=False)}
이력서: {resume_text[:3000]}
JSON만 반환해.
"""}],
        temperature=0.7
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(result)


def evaluate_cover_letter(cover_letter: dict, job_info: dict) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
아래 자소서를 채용공고 기준으로 평가해줘.
평가 항목:
- specificity: 구체성 (0~10)
- relevance: 직무 연관성 (0~10)
- structure: 구조/논리성 (0~10)
- total: 총점 (0~30)
- feedback: 한 줄 피드백

채용공고: {json.dumps(job_info, ensure_ascii=False)}
자소서: {json.dumps(cover_letter, ensure_ascii=False)}
JSON만 반환해.
"""}],
        temperature=0
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(result)