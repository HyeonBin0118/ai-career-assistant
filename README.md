# 🤖 AI Career Assistant

채용공고 분석 · 맞춤 면접 질문 생성 · 음성 답변 평가 · 피드백 리포트까지 — AI 기반 취업 준비 올인원 플랫폼

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-blue?logo=docker&logoColor=white)

> [Job Agent v3](https://github.com/HyeonBin0118/job-agent-v3)과 [Mock Interview AI](https://github.com/HyeonBin0118/mock-interview-ai)를 통합하고 기능을 확장한 최종 프로젝트입니다.

---

## 시작 배경

Job Agent 시리즈에서 채용공고 분석과 면접 질문 생성을 만들었고, Mock Interview AI에서 음성 답변 평가를 만들었습니다. 두 프로젝트가 자연스럽게 이어지는 흐름임에도 따로 존재했고, 실제 취준생이 쓰려면 두 곳을 오가며 결과를 복사해야 했습니다.

이번 프로젝트에서는 두 프로젝트를 하나로 통합하고, 빠진 기능을 추가해 완결된 서비스로 만드는 것을 목표로 합니다.

---

## 사용 흐름
```
STEP 1 · 입력            STEP 2 · 질문 생성
채용공고 URL + 이력서 ──▶  맞춤 면접 질문 8개
GPT-4o-mini · 4개 카테고리
│
▼
STEP 4 · 평가            STEP 3 · 답변
GPT 점수 + 피드백   ◀──  마이크 녹음 또는 mp3 업로드
모범 답안 비교            Whisper API 변환
│
▼
STEP 5 · 분석
카테고리별 약점 분석
반복 연습 점수 추이
```

---

## 주요 기능

**1. 맞춤형 질문 생성**
채용공고 URL과 이력서를 입력하면 보유 스킬, 부족 스킬, 직무, 인성 4개 카테고리로 면접 질문 8개를 자동 생성합니다.

**2. 음성 답변 평가**
마이크 녹음 또는 mp3 파일 업로드로 답변하면 Whisper API가 텍스트로 변환하고, GPT가 논리성·구체성·시간 관리 3가지 지표로 평가합니다.

**3. 모범 답안 비교**
피드백 화면에서 내 답변과 GPT가 생성한 모범 답안을 나란히 비교합니다. 어떤 내용이 빠졌는지 바로 확인할 수 있습니다.

**4. 카테고리별 약점 분석**
세션별 답변 데이터를 카테고리(보유 스킬/부족 스킬/직무/인성) 단위로 집계해 평균 점수를 가로 막대 차트로 표시합니다. 어떤 유형이 약한지 한눈에 파악할 수 있습니다.

**5. 반복 연습 점수 추이**
같은 질문에 여러 번 답변하면 시도별 점수 변화를 라인 차트로 추적합니다.

**6. Redis 캐싱**
동일 공고 재요청 시 크롤링과 공고 분석을 건너뛰고 Redis에서 바로 반환합니다.

| 단계 | CACHE MISS | CACHE HIT |
|---|---|---|
| 크롤링 + 공고 분석 | 6,538ms | 0ms |
| 이력서 매칭 | 5,138ms | 4,483ms |
| 질문 생성 | 22,829ms | 21,254ms |
| **전체** | **34,514ms** | **25,737ms** |

캐싱으로 약 **8,800ms (25%) 단축**됩니다.

---

## 기술 스택

| 분류 | 기술 |
|---|---|
| Backend | FastAPI, Python 3.11 |
| Database | PostgreSQL 16 + SQLAlchemy ORM |
| Cache | Redis 7 |
| AI | GPT-4o-mini, Whisper API |
| Container | Docker Compose |
| Frontend | Vanilla JS, Web Audio API, Chart.js |

---

## 프로젝트 구조
```
ai-career-assistant/
├── app/
│   ├── api/v1/
│   │   ├── sessions.py       # 세션 관련 엔드포인트
│   │   └── answers.py        # 답변 및 평가 엔드포인트
│   ├── core/
│   │   └── config.py         # 환경변수 설정
│   ├── services/
│   │   ├── interview.py      # 크롤링, 질문 생성 로직
│   │   ├── evaluation.py     # Whisper 변환, GPT 평가 로직
│   │   └── cache.py          # Redis 캐싱
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── main.py
├── alembic/
├── frontend/
│   └── index.html
├── tests/
├── docker-compose.yml
└── requirements.txt
```

---

## 설치 및 실행

```bash
# 1. 레포 클론
git clone https://github.com/HyeonBin0118/ai-career-assistant.git
cd ai-career-assistant

# 2. 가상환경 설정
conda create -n mock_interview python=3.11
conda activate mock_interview
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력
# DATABASE_URL을 localhost로 변경

# 4. Docker Compose 실행
docker-compose up -d

# 5. DB 마이그레이션
alembic upgrade head

# 6. 서버 실행
uvicorn app.main:app --reload
```

`http://localhost:8000` 접속 시 면접 UI가 열립니다.

---

## 관련 프로젝트

- [Mock Interview AI](https://github.com/HyeonBin0118/mock-interview-ai) — 이 프로젝트의 출발점 (Phase 1~4)
- [Job Agent v3](https://github.com/HyeonBin0118/job-agent-v3) — 채용공고 분석 + 자소서 생성

---

License: MIT