# 🗺️ AI Career Assistant — 개발 계획

## 현재 완료된 것

- [x] FastAPI + PostgreSQL + Redis + Docker Compose 기반 백엔드 구조
- [x] 채용공고 크롤링 + GPT 질문 생성 + Whisper 음성 평가 파이프라인
- [x] 자소서 생성 + 품질 평가 + 면접 연결 흐름
- [x] 카테고리별 약점 분석, 반복 연습 점수 추이, 면접 완료 리포트
- [x] Redis 캐싱 성능 측정 (25% 응답시간 단축 확인)
- [x] 평가 일관성 및 프롬프트 개선 효과 정량 테스트
- [x] Celery 비동기 처리 (30초 → 2.1초, 93% 단축)
- [x] GitHub Actions CI 구성
- [x] Edge-TTS 기반 면접관 음성 출력
- [x] Whisper STT 한국어 음성 인식
- [x] GPT-4o-mini 꼬리질문 대화 루프
- [x] Streamlit 음성 면접 UI (streamlit_voice.py)
- [x] 사이드바 설정 (마이크 선택 / STT 모델 선택 / 무음 감지 임계값)
- [x] 실시간 스펙트럼 시각화 + 답변 시간 측정

---

## Phase 1 — 음성 면접 고도화 (진행 중)

**목표:** 음성 대화형 면접 시뮬레이터 완성도 높이기

**할 것:**

- [ ] 에어팟/블루투스 마이크 인식 문제 해결
- [ ] STT 정확도 검증 (Whisper medium 모델 — 마이크 문제 해결 후 검증 필요)
- [ ] 채용공고 URL 연동 → 공고 맞춤 질문 생성
- [ ] 면접 종료 후 평가 리포트 (항목별 점수 + 피드백)
- [ ] 대화 기록 PostgreSQL 저장

**기대 효과:** 실사용 가능한 음성 면접 시뮬레이터 완성

---

## Phase 2 — AWS 배포

**목표:** localhost를 실제 URL로 공개

**할 것:**

- [ ] AWS EC2 프리티어 인스턴스 생성
- [ ] EC2에 Docker + Docker Compose 설치
- [ ] GitHub Actions와 연결해 push 시 EC2 자동 배포
- [ ] HTTPS 설정 (Let's Encrypt)

**기대 효과:** 포트폴리오에 라이브 데모 링크 추가 가능

---

## Phase 3 — 고도화

**목표:** 포트폴리오 차별화 요소 추가

**할 것:**

- [ ] async SQLAlchemy 전환 (동시 요청 처리 개선)
- [ ] WebSocket 기반 실시간 진행률 전송 (현재 0.5초 폴링 → 서버 푸시)
- [ ] Rubric 기반 평가 체계 명시화 (질문 연관성 / 구체성 / 논리 구조 / 시간 안배)
- [ ] Human Evaluation 실험 (GPT 평가와 실제 평가 상관계수 측정)

---

## 참고

- Phase 1 음성 면접 완성 → Phase 2 배포 순으로 진행
- Phase 3은 배포 이후 독립적으로 추가
- 각 Phase 완료 후 README 업데이트 및 정량 측정 결과 기록
