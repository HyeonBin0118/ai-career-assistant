# API 명세

Base URL: `http://localhost:8000/api/v1`

Swagger UI: `http://localhost:8000/docs`

---

## 세션

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/sessions` | 세션 생성 (공고 크롤링 + 질문 생성) |
| GET | `/sessions` | 세션 목록 조회 (최신순) |
| GET | `/sessions/{id}` | 세션 조회 |
| GET | `/sessions/{id}/history` | 세션 상세 + 질문별 답변 이력 |
| GET | `/sessions/{id}/category-stats` | 카테고리별 평균 점수 |
| GET | `/sessions/{id}/report` | 면접 완료 리포트 |
| POST | `/sessions/voice` | 음성 면접 대화 기록 저장 |

### POST /sessions

Request:
```json
{
  "job_url": "https://...",
  "resume_text": "본인의 이력서 내용"
}
```

Response:
```json
{
  "id": 1,
  "company": "위버스컴퍼니",
  "position": "백엔드 개발자",
  "questions": [
    {
      "id": 1,
      "question_text": "FastAPI를 사용한 경험에 대해 말씀해 주세요.",
      "category": "보유 스킬",
      "difficulty": 3,
      "specificity": 3,
      "model_answer": "모범 답안 내용...",
      "tip": "답변 시 주의할 점"
    }
  ]
}
```

### POST /sessions/voice

음성 대화형 면접 종료 후 대화 기록과 평가 리포트를 저장.

Request:
```json
{
  "name": "김현빈",
  "role": "AI 백엔드 개발자",
  "job_url": "https://...",
  "company": "지티원",
  "position": "AI Workbench 개발자",
  "conversation": [
    {"role": "assistant", "content": "자기소개 해주세요."},
    {"role": "user", "content": "안녕하세요. 저는 ..."}
  ],
  "report": {
    "tech": 8,
    "specificity": 7,
    "logic": 8,
    "communication": 9,
    "total": 80,
    "strengths": ["구체적인 수치로 설명", "기술 선택 이유 명확"],
    "improvements": ["초기 답변 불명확", "커뮤니케이션 개선 필요"],
    "summary": "전반적으로 기술 이해도가 높음"
  }
}
```

Response:
```json
{
  "session_id": 24,
  "message": "저장 완료"
}
```

---

## 답변

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/questions/{id}/answers` | 음성 파일 답변 제출 (Celery 비동기 처리) |
| GET | `/questions/{id}/answers` | 특정 질문의 모든 답변 조회 |
| GET | `/answers/{id}/status` | 비동기 처리 상태 확인 (폴링용) |
| GET | `/answers/{id}/feedback` | 답변 평가 결과 조회 |
| POST | `/evaluate-text` | 텍스트 답변 평가 + DB 저장 |

### POST /questions/{id}/answers

Request: `multipart/form-data`
```
audio: <audio file>  (mp3, wav, webm, m4a)
```

Response (즉시 반환):
```json
{
  "answer_id": 1,
  "question_id": 1,
  "status": "processing",
  "message": "음성 파일이 접수됐습니다. 잠시 후 결과를 확인하세요."
}
```

### GET /answers/{id}/status

Celery 비동기 처리 완료 여부 확인. 프론트엔드에서 0.5초 간격으로 폴링.

Response (처리 중):
```json
{
  "answer_id": 1,
  "status": "processing"
}
```

Response (완료):
```json
{
  "answer_id": 1,
  "status": "completed",
  "answer_text": "저는 FastAPI를 사용하여...",
  "logic_score": 4,
  "specificity_score": 5,
  "time_score": 5,
  "total_score": 14,
  "feedback": "구체적인 수치와 사례를 잘 활용했습니다."
}
```

status 값: `processing` | `completed`

### POST /evaluate-text

텍스트 입력 방식 답변 평가. 답변과 평가 결과를 DB에 저장.

Request:
```json
{
  "question_id": 1,
  "answer_text": "저는 Redis를 캐싱 용도로 활용했습니다...",
  "duration_seconds": 60.0
}
```

Response:
```json
{
  "answer_text": "저는 Redis를 캐싱 용도로 활용했습니다...",
  "logic_score": 4,
  "specificity_score": 5,
  "total_score": 9,
  "feedback": "구체적인 수치와 사례를 잘 포함했습니다."
}
```

---

## 자소서

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/cover-letter/generate` | 자소서 생성 |
| POST | `/cover-letter/evaluate` | 자소서 품질 평가 |

### POST /cover-letter/generate

Request:
```json
{
  "session_id": 1,
  "length": 500,
  "custom_format": "1. 지원동기\n2. 직무 관련 경험\n3. 입사 후 포부"
}
```

`custom_format` 비워두면 기본 형식(지원동기/직무경험/입사후포부)으로 생성.

Response:
```json
{
  "cover_letter": {
    "지원동기": "저는 AI 백엔드 개발자로서...",
    "직무 관련 경험": "FastAPI와 LangGraph를 활용하여...",
    "입사 후 포부": "입사 후에는..."
  }
}
```

### POST /cover-letter/evaluate

Request:
```json
{
  "session_id": 1,
  "cover_letter": {
    "지원동기": "저는 AI 백엔드 개발자로서...",
    "직무 관련 경험": "FastAPI와 LangGraph를 활용하여..."
  }
}
```

Response:
```json
{
  "specificity": 8,
  "relevance": 9,
  "structure": 7,
  "total": 24,
  "feedback": "구체적인 수치와 성과를 더 강조하면 좋을 것 같습니다."
}
```