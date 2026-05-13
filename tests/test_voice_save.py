import requests

payload = {
    "name": "테스트",
    "role": "AI 백엔드 개발자",
    "job_url": "",
    "company": "테스트 회사",
    "position": "AI 백엔드 개발자",
    "conversation": [
        {"role": "assistant", "content": "자기소개 해주세요."},
        {"role": "user", "content": "안녕하세요. 저는 FastAPI와 LangGraph를 활용한 AI 에이전트를 개발한 경험이 있습니다."},
        {"role": "assistant", "content": "LangGraph를 선택한 이유가 있나요?"},
        {"role": "user", "content": "상태 기반 파이프라인 설계가 용이하고 복잡한 워크플로우를 표현하기 좋아서 선택했습니다."},
        {"role": "assistant", "content": "Redis를 어떻게 활용하셨나요?"},
        {"role": "user", "content": "캐시와 Celery 메시지 브로커 두 가지 용도로 활용했습니다."},
        {"role": "assistant", "content": "비동기 처리 경험이 있나요?"},
        {"role": "user", "content": "Celery로 Whisper 음성 변환을 백그라운드 처리해서 응답시간을 30초에서 2초로 줄였습니다."},
        {"role": "assistant", "content": "Docker 사용 경험은요?"},
        {"role": "user", "content": "Docker Compose로 4개 서비스를 컨테이너화해서 환경 재현성을 확보했습니다."},
    ],
    "report": {
        "tech": 8,
        "specificity": 7,
        "logic": 8,
        "communication": 9,
        "total": 80,
        "strengths": ["구체적인 수치로 성과를 설명함", "기술 선택 이유를 명확히 설명함"],
        "improvements": ["더 깊은 기술 원리 설명 필요", "실패 경험도 언급하면 좋음"],
        "summary": "전반적으로 기술 이해도가 높고 프로젝트 경험이 풍부함"
    }
}

res = requests.post("http://localhost:8000/api/v1/sessions/voice", json=payload)
print(res.status_code)
print(res.json())