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
- [x] Streamlit 통합 앱 (자소서 + 면접연습 + 음성면접 + 기록)
- [x] 사이드바 설정 (마이크 선택 / STT 모델 / 무음 감지 임계값)
- [x] 실시간 스펙트럼 시각화 + 답변 시간 측정
- [x] 채용공고 URL 연동 맞춤 꼬리질문
- [x] 음성 면접 평가 리포트 (항목별 점수 + 피드백)
- [x] 면접 대화 기록 DB 저장 + 기록 조회 페이지
- [x] 텍스트 답변 DB 저장 버그 수정
- [x] 코드 리팩토링 (함수 분리, 주석 추가)
- [x] README 전면 개편 + 스크린샷 교체
- [x] API.md 최신화
- [x] 데모 영상 제작 (YouTube)
- [x] AWS EC2 인스턴스 생성 + Docker 설치

---

## Phase 2 — AWS 배포 (진행 중)

**목표:** localhost를 실제 URL로 공개

**할 것:**
- [ ] EC2에 코드 배포 + 환경변수 설정
- [ ] docker-compose up + 서비스 확인
- [ ] 포트 열기 (8000, 8501)
- [ ] HTTPS 설정 (Let's Encrypt)
- [ ] GitHub Actions 자동 배포 연결

---

## Phase 3 — 고도화

**목표:** 포트폴리오 차별화 요소 추가

**할 것:**
- [ ] 블루투스 마이크 호환성 개선
- [ ] WebSocket 기반 실시간 진행률 전송
- [ ] Rubric 기반 평가 체계 명시화
- [ ] Human Evaluation 실험

---

## 참고

- Phase 2 배포 완료 후 README에 라이브 데모 링크 추가
- 각 Phase 완료 후 정량 측정 결과 기록
