# 🤖 AI Career Assistant

![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-6BA539?style=flat-square&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis_7-DC382D?style=flat-square&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Whisper](https://img.shields.io/badge/Whisper_API-412991?style=flat-square&logo=openai&logoColor=white)
![GPT](https://img.shields.io/badge/GPT--4o--mini-412991?style=flat-square&logo=openai&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)


채용공고 분석부터 자소서 작성, 면접 연습, 결과 리포트까지 한 세션에서 완결되는 AI 백엔드 통합 플랫폼.

[Job Agent 시리즈](https://github.com/HyeonBin0118/job-agent-v3)와 [Mock Interview AI](https://github.com/HyeonBin0118/mock-interview-ai)를 하나의 백엔드로 통합하면서, FastAPI + 비동기 처리 구조로 재설계한 프로젝트

## 핵심 성과

| 항목 | 결과 |
|---|---|
| Redis 캐싱 적용 | 34.5초 → 25.7초 (25% 단축) |
| Celery 비동기 처리 | 30초+ → 2.1초 (93% 단축) |
| 평가 일관성 (temp=0) | 표준편차 0 (완전 결정론적) |
| 답변 변별력 | 좋은 답 15점 vs 나쁜 답 7점 |
| 시간 점수 일관성 | 100% (LLM → 코드 분리) |


## 시스템 아키텍처

```
[Browser]
    │
    ▼
[FastAPI]  ──────►  [PostgreSQL]   (세션/질문/답변/평가)
    │      ──────►  [Redis]        (캐시 + 메시지 브로커)
    │                  │
    │                  ▼
    │             [Celery Worker]  (Whisper 음성 변환)
    │                  │
    └─────────────► [OpenAI API]  ◄┘
```
- API 서버: FastAPI (uvicorn)
- DB: PostgreSQL (세션/질문/답변/평가 4개 테이블)
- 캐시 + 메시지 브로커: Redis 단일 인스턴스 (1인 2역)
- 비동기 워커: Celery (Whisper 음성 변환 처리)
- 컨테이너: Docker Compose로 4개 서비스 일괄 관리

---
## 프로젝트 구조
```
ai-career-assistant/
├── app/
│   ├── api/v1/
│   │   ├── sessions.py       # 세션 관련 엔드포인트
│   │   ├── answers.py        # 답변 및 평가 엔드포인트
│   │   └── cover_letter.py   # 자소서 생성/평가 엔드포인트
│   ├── core/
│   │   └── config.py
│   ├── services/
│   │   ├── interview.py      # 크롤링, 질문 생성, 자소서 생성 로직
│   │   ├── evaluation.py     # Whisper 변환, GPT 평가 로직
│   │   └── cache.py          # Redis 캐싱
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── main.py
├── alembic/
├── evaluation/
│   ├── eval_consistency.py   # 평가 일관성 테스트
│   ├── eval_prompt_compare.py # 프롬프트 개선 효과 비교
│   └── eval_consistency_results.json
├── frontend/
│   └── index.html
├── tests/
├── docker-compose.yml
└── requirements.txt
```

## DB모델
```
InterviewSession  ->  Question  ->  Answer  ->  EvaluationResult
(공고 + 이력서)      (질문 8개)    (음성 답변)   (GPT 평가 결과)
```
세션 하나당 질문 여러 개, 질문 하나당 답변 여러 번 — 같은 질문을 반복 연습하면서 점수 변화를 추적할 수 있는 구조

---

## API 명세: [API.md](./API.md)
---

## 기술 의사결정

| 기술 | 선택 이유 |
|---|---|
| FastAPI | Whisper/GPT 호출이 I/O bound → async 네이티브 지원, Swagger 자동 생성 |
| PostgreSQL | JSONB 지원, ACID 트랜잭션, pgvector 확장으로 Vector DB 통합 여지 확보 |
| SQLAlchemy (동기) | 병목은 DB가 아닌 Whisper(20초). 스레드풀로 기본 동시성 확보, 복잡도 최소화 |
| Redis | 캐시 + Celery 브로커 1인 2역. 인프라 추가 없이 두 역할 동시 처리 |
| Celery | BackgroundTasks와 달리 워커 스케일 아웃 가능, 작업 유실 없음 |
| GPT-4o-mini | 세션당 호출 10회+. GPT-4 대비 60배 저렴하면서 구조화 작업엔 충분한 품질 |
| Vanilla JS | 마이크 장치 선택 + 음파 시각화 → Streamlit 불가, React는 단일 페이지에 과함 |
| Docker Compose | PostgreSQL + Redis + Celery 4개 서비스를 1줄(`docker-compose up`)로 재현 |

## 정량 평가

### 1. Redis 캐싱 효과 (단계별 측정) - 같은 URL을 두 번 요청했을 때 단계별 응답 시간 비교

| 단계 | 캐시 적용 전 | 캐시 적용 후 |
|---|---|---|
| 크롤링 + 공고 분석 | 6,538ms | 0ms |
| 이력서 매칭 | 5,138ms | 4,483ms |
| 질문 생성 | 22,829ms | 21,254ms |
| **전체** | **34,514ms** | **25,737ms** |

>캐싱으로 약 **8,800ms (25%) 단축. 질문 생성이 전체의 65% 이상을 차지하는 병목으로 측정.

### 2. 답변 평가 일관성 (temperature=0, n=10)

| 답변 품질 | 평균 점수 | 표준편차 |
|---|---|---|
| 좋은 답변 (구체적 수치 + 프로젝트 포함) | 15.0 | 0.0 |
| 보통 답변 (관련 있지만 추상적) | 12.0 | 0.0 |
| 나쁜 답변 (질문과 무관한 내용) | 7.0 | 0.0 |

> temperature=0 환경에서 평가가 완전히 결정론적으로 작동함을 확인했습니다. 답변 품질에 따라 점수 차이가 명확하게 나타납니다(15점 vs 7점).
 
> 표준편차 0은 같은 입력에 대해 항상 같은 점수를 반환함을 의미.

### 3. 비동기 처리 성능 (n=5)

| 측정 항목 | 결과 |
|---|---|
| 즉시 응답 평균 | 2.091초 |
| 즉시 응답 최소 | 2.070초 |
| 즉시 응답 최대 | 2.138초 |
| 기존 동기 처리 | 30초 이상 |

> 사용자 체감 대기시간이 30초 이상에서 2.1초로 93% 단축.

> 기존 : 음성 파일 업로드 후 Whisper 변환과 GPT 평가가 모두 완료될 때까지 사용자 대기.
> 개선 : Celery 워커가 백그라운드에서 처리하도록 분리 -> 서버는 파일 접수 즉시 응답을 반환하고, 프론트엔드가 0.5초 간격으로 완료 여부를 폴링.

> Redis가 캐시와 메시지 브로커 두 가지 역할을 동시에 수행함.

## 사용 흐름

```
1. 채용공고 URL 입력 → 공고 자동 크롤링 + 분석
2. 이력서 입력 → 회사 맞춤형 자소서 생성
3. 자소서 품질 자동 평가 (구체성/관련성/구조)
4. 면접 시작 → 공고 기반 맞춤 질문 생성
5. 음성 답변 녹음 → Whisper 변환 → GPT 평가
6. 즉시 피드백 + 종합 리포트 제공
7. 모든 연습 기록 저장 + 재조회 가능
```

## 주요 화면

| | |
|---|---|
| ![시작 화면](images/main_start.png) | ![자소서 입력](images/cover_input.png) |
| 시작 화면 | 자소서 초안 생성 |
| ![자소서 결과](images/cover_result.png) | ![자소서 평가](images/cover_eval.png) |
| 자소서 생성 결과 | 자소서 품질 평가 |
| ![면접 질문](images/interview_question.png) | ![답변 평가](images/interview_feedback.png) |
| 면접 질문 진행 | 답변 피드백&모범답안 |
| ![리포트](images/report.png) | ![연습 기록](images/history_list.png) |
| 면접 완료 리포트 | 연습 기록 목록 |

| |
|---|
| ![연습 기록 상세](images/history_detail.png) |
|카테고리별 평균 점수 차트 & 질문별 반복 연습 점수 추이|

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
# .env 파일에서 OPENAI_API_KEY 입력
# DATABASE_URL 호스트 변경 (Docker 컨테이너 내부: db / 로컬 uvicorn 실행: localhost)
# 예시: postgresql://postgres:postgres@localhost:5432/mock_interview

# 4. Docker Compose 실행
docker-compose up -d

# 5. DB 마이그레이션
alembic upgrade head

# 6. 서버 실행
uvicorn app.main:app --reload
```

테스트:
```bash
pytest # 단위 테스트 (세션 생성, 질문 조회, 답변 제출, 캐시 MISS→HIT 검증
```
## 정량 평가 실행
```bash
python evaluation/eval_consistency.py      # GPT 평가 일관성 (표준편차 0 측정)
python evaluation/eval_prompt_compare.py   # 프롬프트 개선 전/후 비교
python evaluation/eval_async_performance.py # 비동기 처리 응답시간 측정
```
## 개발 환경

- OS: Windows 10
- Python: 3.11 (Anaconda)
- 컨테이너: Docker Compose 4개 서비스
- CI: GitHub Actions (push 시 자동 테스트)

## 향후 개선 과제

1. **async SQLAlchemy 도입**
동시 요청 100개 이상 환경에서 진짜 비동기 효과를 확보하기 위한 전환. 현재는 FastAPI 스레드풀로 기본 동시성을 확보한 상태.

2. **WebSocket 기반 실시간 진행률 전송**
현재 0.5초 폴링 방식을 서버 푸시로 전환. 서버 리소스 97% 절감(40번 폴링 → 1번 연결)과 진행률 세밀 표시 가능.

3. **Rubric 기반 평가 체계 명시화**
평가 항목 분리(질문 연관성 / 구체성 / 논리 구조 / 시간 안배). 사용자가 약점 항목을 명확히 파악 가능.

4. **Human Evaluation 실험**
실제 면접관 평가와 GPT 평가의 상관계수 측정. GPT 평가 신뢰도를 정량적으로 검증.

## 한계 인정

GPT 평가의 한계: 평가자도 GPT, 생성자도 GPT인 구조이므로 자기 평가에 관대해질 가능성이 있습니다. 답변 품질에 따라 점수 차이는 명확하지만(좋은 답 15점 vs 나쁜 답 7점), 절대적인 평가 신뢰도는 사람 평가와의 교차 검증이 필요합니다.

이 한계를 인지한 상태에서 첫 버전을 우선 완성하고, Human Evaluation을 향후 개선 과제로 두었습니다.

---
## 관련 프로젝트

- [Mock Interview AI](https://github.com/HyeonBin0118/mock-interview-ai) — 이 프로젝트의 출발점 (음성 평가 파이프라인)
- [Job Agent v3](https://github.com/HyeonBin0118/job-agent-v3) — 채용공고 분석 + 자소서 생성

---

License: MIT


