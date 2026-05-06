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

### POST /sessions

Request:
```json
{
  "job_url": "https://...",
  "resume": "본인의 이력서 내용"
}
```

Response:
```json
{
  "session_id": 1,
  "questions": [
    {
      "id": 1,
      "content": "본인의 강점을 말씀해 주세요.",
      "category": "인성",
      "difficulty": 3
    }
  ]
}
```

---

## 답변

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/questions/{id}/answers` | 음성 답변 제출 |
| GET | `/questions/{id}/answers` | 특정 질문의 모든 답변 조회 |
| GET | `/answers/{id}/feedback` | 답변 평가 결과 조회 |
| GET | `/answers/{id}/status` | 비동기 처리 상태 확인 |
| POST | `/evaluate-text` | 수정된 텍스트로 재평가 |

### POST /questions/{id}/answers

Request: `multipart/form-data`
```
audio: <audio file>  (mp3, wav, webm, m4a)
```

Response (즉시 반환):
```json
{
  "answer_id": 1,
  "status": "processing"
}
```

### GET /answers/{id}/status

Response:
```json
{
  "answer_id": 1,
  "status": "completed",
  "score": 15,
  "feedback": "답변이 질문과 관련성이 높고 구체적인 사례를 포함하고 있습니다.",
  "transcript": "저는 문제 해결 능력이 강점입니다..."
}
```

status 값: `processing` | `completed` | `failed`

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
  "job_url": "https://...",
  "resume": "본인의 이력서 내용",
  "length": "medium"
}
```

Response:
```json
{
  "cover_letter": "생성된 자소서 내용..."
}
```

### POST /cover-letter/evaluate

Request:
```json
{
  "cover_letter": "평가할 자소서 내용...",
  "job_description": "공고 내용..."
}
```

Response:
```json
{
  "specificity": 4,
  "relevance": 5,
  "structure": 3,
  "overall": 4,
  "feedback": "구체적인 수치와 성과를 더 강조하면 좋을 것 같습니다."
}
```