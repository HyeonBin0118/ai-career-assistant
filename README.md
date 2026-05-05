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

Job Agent 시리즈에서 채용공고 분석과 면접 질문 생성을 만들었고, Mock Interview AI에서 음성 답변 평가를 만들었습니다. 두 프로젝트가 자연스럽게 이어지는 흐름임에도 따로 존재했고, 실제로 써보니 Job Agent에서 생성한 질문을 직접 복사해서 Mock Interview에 붙여넣어야 했습니다.

이번 프로젝트는 두 프로젝트를 하나의 서비스로 통합하고, 빠진 기능을 추가해 "공고 분석 → 자소서 작성 → 면접 연습 → 리포트"가 하나의 세션에서 완결되도록 만드는 것을 목표로 했습니다.

---

## "GPT한테 그냥 물어보면 되는 거 아닌가요?"

자소서 생성이나 면접 질문 생성만 보면 ChatGPT에 직접 요청하는 것과 기능적으로 비슷합니다. 차이는 기능이 아니라 파이프라인과 데이터에 있습니다.

- 채용공고 URL만 입력하면 크롤링부터 자동 처리
- 자소서 생성 → 품질 평가 → 면접 질문 생성 → 음성 답변 → 피드백 리포트까지 하나의 흐름으로 연결
- 연습 기록이 DB에 쌓여 반복 연습 추이를 추적 가능
- FastAPI + PostgreSQL + Redis + Docker 인프라 위에서 동작

ChatGPT에 같은 걸 시키려면 사용자가 공고 텍스트를 직접 복사해서 붙이고, 결과를 따로 저장하고, 면접 연습은 또 다른 곳에서 해야 합니다. 이 프로젝트의 가치는 LLM 호출 자체가 아니라 그걸 백엔드 아키텍처로 감싸고, 사용자 흐름을 설계하고, 데이터를 적재하는 경험에 있습니다.

---

## 사용 흐름
```
[경로 1 — 자소서 먼저]
공고 URL + 이력서 입력
↓
자소서 초안 생성 + 품질 평가 (수정 가능)
↓
이 자소서로 면접 보기 →[경로 2 — 바로 면접]
공고 URL + 이력서 입력
↓
맞춤 면접 질문 8개 생성
↓
음성 답변 (마이크 / mp3 업로드)
↓
Whisper 변환 + GPT 평가 + 모범 답안 비교
↓
면접 완료 리포트 (전체 점수 + 카테고리 분석 + 최고/최저 답변)
```

---

## 주요 화면

### 1. 시작 화면
![시작 화면](images/main_start.png)

> 자소서부터 준비하거나 바로 면접 연습으로 진입할 수 있는 두 가지 경로를 제공합니다.

### 2. 자소서 생성 및 품질 평가
![자소서 입력](images/cover_input.png)

![자소서 평가](images/cover_eval.png)

> 자소서 초안을 생성하고 구체성·직무연관성·구조/논리성 세 가지 지표로 품질을 평가합니다. 수정 후 재평가도 가능합니다.

### 3. 면접 질문 및 답변 평가
![면접 질문](images/interview_question.png)

![답변 평가](images/interview_feedback.png)

> GPT 평가 점수와 함께 모범 답안을 나란히 비교할 수 있습니다.

### 4. 면접 완료 리포트
![리포트](images/report.png)

> 전체 평균 점수, 카테고리별 차트, 가장 잘한 답변과 가장 부족한 답변을 한 화면에 요약합니다.

### 5. 연습 기록 및 점수 추이
![연습 기록 목록](images/history_list.png)

![연습 기록 상세](images/history_detail.png)

> 카테고리별 평균 점수 차트와 질문별 반복 연습 점수 추이를 확인할 수 있습니다.

---

## 주요 기능

**1. 자소서 생성 + 품질 평가**
채용공고 URL과 이력서를 입력하면 자소서 초안을 생성합니다. 길이(200-1000자)와 포맷을 직접 설정할 수 있고, 생성된 자소서를 구체성·직무연관성·구조/논리성 세 가지 지표(0-10점)로 자동 평가합니다. 수정 후 재평가도 가능합니다.

**2. 맞춤형 면접 질문 생성**
이력서와 채용공고를 분석해 보유 스킬, 부족 스킬, 직무, 인성 4개 카테고리로 면접 질문 8개를 생성합니다.

**3. 음성 답변 평가 + 모범 답안 비교**
마이크 녹음 또는 mp3 파일 업로드로 답변하면 Whisper API가 텍스트로 변환합니다. GPT가 논리성·구체성·시간 관리 3가지 지표로 평가하고, 모범 답안과 나란히 비교할 수 있습니다.

**4. 카테고리별 약점 분석**
세션별 답변 데이터를 카테고리 단위로 집계해 평균 점수를 가로 막대 차트로 표시합니다. 어떤 유형이 약한지 한눈에 파악할 수 있습니다.

**5. 반복 연습 점수 추이**
같은 질문에 여러 번 답변하면 시도별 점수 변화를 라인 차트로 추적합니다.

**6. 면접 완료 리포트**
면접이 끝나면 전체 평균 점수, 카테고리별 차트, 가장 잘한 답변과 가장 부족한 답변을 한 화면에 요약합니다.

**7. Redis 캐싱**
동일 공고 재요청 시 크롤링과 공고 분석을 건너뛰고 Redis에서 바로 반환합니다.

| 단계 | CACHE MISS | CACHE HIT |
|---|---|---|
| 크롤링 + 공고 분석 | 6,538ms | 0ms |
| 이력서 매칭 | 5,138ms | 4,483ms |
| 질문 생성 | 22,829ms | 21,254ms |
| **전체** | **34,514ms** | **25,737ms** |

캐싱으로 약 **8,800ms (25%) 단축**됩니다. 질문 생성이 전체의 65% 이상을 차지하는 병목이라는 것도 이 측정으로 확인했습니다.

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

## 아키텍처
```
┌─────────────────────────────────┐
│           Frontend              │
│   Vanilla JS + Web Audio API    │
│   Chart.js 차트 시각화           │
└────────────────┬────────────────┘
│ HTTP
┌────────────────▼────────────────┐
│     Backend · FastAPI           │
│  ─ 자소서 생성 + 품질 평가       │
│  ─ 질문 생성  (크롤링 + GPT)     │
│  ─ 음성 변환  (Whisper API)      │
│  ─ 답변 평가  (GPT-4o-mini)      │
│  ─ 리포트 생성                   │
└───────┬─────────────┬───────────┘
│             │
┌───────▼──────┐ ┌────▼──────────┐
│   Redis 7    │ │ PostgreSQL 16 │
│ 공고 캐시    │ │ SQLAlchemy ORM│
│ 1시간 TTL    │ │ 4개 테이블    │
└──────────────┘ └───────────────┘
```
전체 서비스는 Docker Compose로 컨테이너화되어 단일 명령으로 구동됩니다.

---

## DB 모델

```
InterviewSession  ->  Question  ->  Answer  ->  EvaluationResult
(공고 + 이력서)      (질문 8개)    (음성 답변)   (GPT 평가 결과)
```
세션 하나당 질문 여러 개, 질문 하나당 답변 여러 번 — 같은 질문을 반복 연습하면서 점수 변화를 추적할 수 있는 구조로 설계했습니다.

---

## API 명세

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/v1/sessions` | 세션 생성 (공고 크롤링 + 질문 생성) |
| GET | `/api/v1/sessions` | 세션 목록 조회 (최신순) |
| GET | `/api/v1/sessions/{id}` | 세션 조회 |
| GET | `/api/v1/sessions/{id}/history` | 세션 상세 + 질문별 답변 이력 |
| GET | `/api/v1/sessions/{id}/category-stats` | 카테고리별 평균 점수 |
| GET | `/api/v1/sessions/{id}/report` | 면접 완료 리포트 |
| POST | `/api/v1/questions/{id}/answers` | 음성 답변 제출 |
| GET | `/api/v1/questions/{id}/answers` | 특정 질문의 모든 답변 조회 |
| GET | `/api/v1/answers/{id}/feedback` | 답변 평가 결과 조회 |
| POST | `/api/v1/evaluate-text` | 수정된 텍스트로 재평가 |
| POST | `/api/v1/cover-letter/generate` | 자소서 생성 |
| POST | `/api/v1/cover-letter/evaluate` | 자소서 품질 평가 |

---

## 정량 평가

### 1. 답변 평가 일관성 테스트

동일한 질문("Redis를 사용한 경험에 대해 설명해 주세요.")에 품질이 다른 답변 3개를 10회씩 평가했습니다.

| 답변 유형 | 평균 점수 | 표준편차 | 최소 | 최대 |
|---|---|---|---|---|
| 좋은 답변 (구체적 수치 + 프로젝트 포함) | 15.0 | 0.0 | 15 | 15 |
| 보통 답변 (관련 있지만 추상적) | 12.0 | 0.0 | 12 | 12 |
| 나쁜 답변 (질문과 무관한 내용) | 7.0 | 0.0 | 7 | 7 |

`temperature=0` 환경에서 평가가 완전히 결정론적으로 작동함을 확인했습니다. 답변 품질에 따라 점수 차이가 명확하게 나타납니다(15점 vs 7점).

### 2. 프롬프트 개선 전/후 비교

질문과 무관한 답변을 1점으로 처리하는 기준을 프롬프트에 명시한 전/후를 비교했습니다.

| 답변 유형 | 개선 전 총점 | 개선 후 총점 | 차이 |
|---|---|---|---|
| 좋은 답변 | 15 | 15 | 0 |
| 보통 답변 | 10 | 11 | +1 |
| 나쁜 답변 | 7 | 7 | 0 |

점수 자체는 큰 차이가 없었으나 **피드백 품질이 개선**됐습니다.

- 개선 전: "구체적인 사례나 사용한 데이터의 종류를 추가하면 더 좋습니다."
- 개선 후: "답변이 질문과 전혀 관련이 없으므로 Redis에 대한 경험을 구체적으로 설명해야 합니다."

나쁜 답변에 대한 피드백이 문제의 핵심(질문과 무관)을 정확히 짚어내게 됐습니다.

### 3. 비동기 처리 성능 측정

Celery + Redis로 Whisper 음성 변환을 백그라운드 처리로 분리한 전/후를 비교했습니다.

| 측정 항목 | 결과 |
|---|---|
| 즉시 응답 평균 | 2.091초 |
| 즉시 응답 최소 | 2.070초 |
| 즉시 응답 최대 | 2.138초 |
| 기존 동기 처리 | 30초 이상 |

사용자 체감 대기시간이 **30초 이상에서 2.1초로 93% 단축**됐습니다.

기존에는 음성 파일 업로드 후 Whisper 변환과 GPT 평가가 모두 완료될 때까지 사용자가 대기해야 했습니다. Celery 워커가 백그라운드에서 처리하도록 분리하면서 서버는 파일 접수 즉시 응답을 반환하고, 프론트엔드가 0.5초 간격으로 완료 여부를 폴링하는 방식으로 개선했습니다. Redis가 캐시와 메시지 브로커 두 가지 역할을 동시에 수행합니다.

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

`http://localhost:8000` 접속 시 서비스가 열립니다.

### 정량 평가 실행

```bash
python evaluation/eval_consistency.py
python evaluation/eval_prompt_compare.py
```

---

## 개발 기록

#### Streamlit 대신 FastAPI + Vanilla JS를 선택한 이유

Job Agent 시리즈는 Streamlit으로 만들었습니다. 빠르게 UI를 붙이기 좋았지만 구조적인 한계가 있었습니다. UI와 비즈니스 로직이 한 파일에 섞여 있어 라우터, 서비스, 모델 레이어를 명확히 분리하기 어려웠고, 음성 처리나 실시간 캔버스 렌더링 같은 브라우저 API는 Streamlit 안에서 제어하기 까다로웠습니다.

이번 프로젝트에서는 백엔드를 FastAPI로 분리해 라우터-서비스-모델 구조를 명확히 나누고, 프론트는 Vanilla JS로 Web Audio API와 MediaRecorder API를 직접 다뤘습니다. 결과적으로 음파 시각화, 마이크 장치 선택, 녹음 상태 관리 같은 기능을 세밀하게 제어할 수 있었고, 기능 추가 시 영향 범위도 명확해졌습니다.

#### PostgreSQL과 Redis를 컨테이너로 분리한 이유

로컬에 직접 DB를 설치하면 OS 환경에 따라 설정이 달라지고, 프로젝트가 끝나도 잔여 프로세스가 남습니다. Docker Compose로 PostgreSQL과 Redis를 컨테이너로 띄우면 `docker-compose up -d` 한 줄로 동일한 환경을 재현할 수 있고, `docker-compose down`으로 깔끔하게 정리됩니다. 이번 프로젝트에서 처음 멀티 컨테이너 환경을 직접 설계했고, 로컬과 Docker 컨테이너 간 네트워크 호스트명 차이(`localhost` vs `db`)를 실수로 겪으면서 컨테이너 네트워킹 개념을 직접 확인했습니다.

#### 시간 점수를 GPT에 맡기지 않고 코드로 직접 계산했다

초기에는 GPT한테 시간 점수까지 판단하게 했습니다. 그런데 같은 녹음 시간이라도 GPT가 매번 다른 점수를 주는 문제가 있었습니다. 시간 점수는 "60~120초면 5점"처럼 규칙이 명확하기 때문에 GPT에 맡길 필요가 없었습니다. Python 코드로 직접 계산하고 GPT 프롬프트에 고정값으로 주입하도록 바꿨더니 시간 점수 일관성이 100%가 됐습니다. LLM에 맡길 것과 코드로 처리할 것을 구분하는 게 중요하다는 걸 직접 겪으면서 배웠습니다.

#### 답변 평가 프롬프트를 개선했다

초기 프롬프트는 "답변이 논리적인가"만 평가했습니다. 테스트해보니 질문과 전혀 무관한 답변을 정성스럽게 해도 높은 점수가 나왔습니다. 논리성 기준에 "질문과 무관한 경우 1점"을 명시하자 피드백이 "구체적 사례를 추가하세요" 수준에서 "답변이 질문과 전혀 관련이 없습니다"로 바뀌었습니다. 프롬프트에 평가 기준을 얼마나 구체적으로 정의하느냐가 결과 품질에 직접 영향을 준다는 것을 확인했습니다.

#### Redis 캐싱 효과를 구간별로 측정했다

"캐싱을 붙이면 빠르다"는 막연한 기대 대신, 각 처리 단계의 응답 시간을 직접 측정했습니다. 측정 결과 질문 생성 GPT 호출이 전체의 65% 이상을 차지하는 병목이었고, 캐싱이 절약하는 구간은 크롤링+공고 분석 6,538ms였습니다. 전체 34,514ms에서 25,737ms로 약 25% 단축됐습니다. 캐싱 범위를 공고 분석으로 한정한 이유도 이 측정에서 나왔습니다. 질문은 이력서와 공고의 조합마다 달라져야 하기 때문에 캐싱 대상이 아닙니다.

#### GPT 평가의 한계는 여전히 존재한다

평가자도 GPT, 생성자도 GPT인 구조라 관대한 경향이 있습니다. 정량 테스트에서 답변 품질에 따른 점수 차이는 확인했지만(15점 vs 7점), 절대적인 평가 신뢰도는 사람 평가와 비교 검증이 필요합니다. job-agent v3에서도 같은 한계를 확인했고, 이번 프로젝트에서도 해결하지 못한 문제입니다.

---

## 한계 및 향후 개선

### 현재 한계
- **답변 평가 신뢰도** — GPT 자체 평가의 한계, 사람 평가와 교차 검증 필요
- **이력서 유효성 검증 없음** — 아무 텍스트나 입력해도 자소서가 생성됨
- **실시간 스트리밍 미적용** — 현재는 전체 녹음 후 일괄 처리 방식

### 향후 개선
- WebSocket 기반 실시간 답변 분석
- 이력서 유효성 검증 (GPT 기반)
- 답변 평가 모델 다양화

---

## 관련 프로젝트

- [Mock Interview AI](https://github.com/HyeonBin0118/mock-interview-ai) — 이 프로젝트의 출발점 (음성 평가 파이프라인)
- [Job Agent v3](https://github.com/HyeonBin0118/job-agent-v3) — 채용공고 분석 + 자소서 생성

---

License: MIT

