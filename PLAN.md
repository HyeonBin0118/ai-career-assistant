# 🗺️ AI Career Assistant — 개발 계획

## 현재 완료된 것

- [x] FastAPI + PostgreSQL + Redis + Docker Compose 기반 백엔드 구조
- [x] 채용공고 크롤링 + GPT 질문 생성 + Whisper 음성 평가 파이프라인
- [x] 자소서 생성 + 품질 평가 + 면접 연결 흐름
- [x] 카테고리별 약점 분석, 반복 연습 점수 추이, 면접 완료 리포트
- [x] Redis 캐싱 성능 측정 (25% 응답시간 단축 확인)
- [x] 평가 일관성 및 프롬프트 개선 효과 정량 테스트

---

## Phase 1 — CI/CD (GitHub Actions)

**목표:** 코드를 push하면 테스트와 빌드가 자동으로 실행되도록 구성

**할 것:**
- `.github/workflows/ci.yml` 작성
- push 시 pytest 자동 실행
- Docker 이미지 자동 빌드 확인

**기대 효과:** 매번 수동으로 테스트하던 과정 자동화, 배포 파이프라인의 시작점

---

## Phase 2 — AWS 배포

**목표:** localhost:8000을 실제 URL로 공개

**할 것:**
- AWS EC2 프리티어 인스턴스 생성
- EC2에 Docker + Docker Compose 설치
- GitHub Actions와 연결해 push 시 EC2 자동 배포
- HTTPS 설정 (Let's Encrypt)

**기대 효과:** "배포된 서비스"로 포트폴리오에 라이브 데모 링크 추가 가능

---

## Phase 3 — 비동기 처리 (Celery + Redis)

**목표:** Whisper 음성 변환을 백그라운드 작업으로 분리

**현재 문제:** 음성 파일 업로드 시 변환이 완료될 때까지 사용자가 대기
**개선 후:** 업로드 즉시 응답, 백그라운드에서 변환 진행, 완료 시 결과 조회

**할 것:**
- Celery 워커 설정
- Redis를 메시지 브로커로 활용 (현재 캐시 용도 → 큐 용도 추가)
- Docker Compose에 Celery 워커 컨테이너 추가
- 비동기 전/후 응답시간 측정 및 README에 결과 기록

**기대 효과:** Redis를 캐시 + 메시지 큐 두 가지 용도로 활용한 경험, 비동기 아키텍처 이해

---

## 참고

- Phase 1 → 2는 순서대로 진행 (Actions가 배포 자동화의 기반)
- Phase 3은 독립적으로 진행 가능
- 각 Phase 완료 후 README 업데이트 및 정량 측정 결과 기록