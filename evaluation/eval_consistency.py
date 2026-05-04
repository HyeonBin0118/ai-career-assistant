import json
import os
import statistics
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

QUESTION = "Redis를 사용한 경험에 대해 설명해 주세요."

TEST_ANSWERS = {
    "좋은 답변": "Mock Interview AI 프로젝트에서 Redis를 캐싱 용도로 활용했습니다. 채용공고 URL을 키로 하고 크롤링+GPT 분석 결과를 값으로 저장해 TTL을 1시간으로 설정했습니다. 동일 공고 재요청 시 크롤링 6,538ms가 제거되어 전체 응답시간이 34초에서 25초로 약 25% 단축됐습니다. Redis의 String 타입에 JSON 직렬화해서 저장했고, Docker Compose로 로컬 환경을 구성해 개발했습니다.",
    "보통 답변": "Redis는 캐싱 용도로 사용해봤습니다. 자주 조회되는 데이터를 Redis에 저장해두면 데이터베이스 부하를 줄일 수 있습니다. TTL을 설정해서 일정 시간이 지나면 자동으로 삭제되도록 했습니다.",
    "나쁜 답변": "저는 팀워크를 중요하게 생각합니다. 프로젝트에서 팀원들과 소통하며 협업하는 것을 즐깁니다. 어려운 상황에서도 포기하지 않고 끝까지 해결하려는 자세를 가지고 있습니다."
}

DURATION = 90.0  # 시간 점수 5점 구간


def evaluate_once(question, answer, duration):
    """개선된 프롬프트로 평가"""
    if duration < 30:
        time_score = 1
    elif duration < 60:
        time_score = 3
    elif duration <= 120:
        time_score = 5
    else:
        time_score = 2

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
면접 질문과 답변을 평가해줘.

**중요: 답변이 질문의 의도와 무관하거나 엉뚱한 내용이면 logic_score를 1점으로 준다.**

평가 기준:
- logic_score: 논리성 (1~5)
  * 1점: 질문과 전혀 무관한 답변이거나 의미없는 내용
  * 2점: 질문과 약간 관련있지만 핵심을 벗어남
  * 3점: 질문에 답하고 있으나 근거가 부족함
  * 4점: 질문에 잘 답하고 있고 근거가 있음
  * 5점: 질문 의도를 완벽히 파악하고 명확한 근거와 함께 답변
- specificity_score: 구체성 (1~5)
  * 1점: 구체적 사례/수치/기술명 전혀 없음
  * 3점: 일부 구체적 내용 포함
  * 5점: 구체적 수치, 사례, 기술명 풍부하게 포함
- total_score: logic_score + specificity_score + {time_score}
- feedback: 한 줄 개선 피드백

질문: {question}
답변: {answer}

JSON만 반환해. time_score는 반드시 {time_score}로 고정해.
"""}],
        temperature=0.3
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    data = json.loads(result)
    data['time_score'] = time_score
    data['total_score'] = data.get('logic_score', 0) + data.get('specificity_score', 0) + time_score
    return data


def run_consistency_test(n=10):
    print(f"=== 답변 평가 일관성 테스트 (n={n}) ===\n")
    results = {}

    for answer_type, answer_text in TEST_ANSWERS.items():
        print(f"[{answer_type}] 평가 중...", end="", flush=True)
        scores = []
        for i in range(n):
            result = evaluate_once(QUESTION, answer_text, DURATION)
            scores.append(result['total_score'])
            print(".", end="", flush=True)
        print()

        avg = statistics.mean(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 0
        results[answer_type] = {
            "scores": scores,
            "avg": round(avg, 2),
            "std": round(std, 2),
            "min": min(scores),
            "max": max(scores)
        }

    print("\n=== 결과 ===")
    print(f"{'답변 유형':<12} {'평균':>6} {'표준편차':>8} {'최소':>6} {'최대':>6} {'점수 목록'}")
    print("-" * 70)
    for answer_type, data in results.items():
        print(f"{answer_type:<12} {data['avg']:>6} {data['std']:>8} {data['min']:>6} {data['max']:>6}  {data['scores']}")

    print("\n=== 분석 ===")
    for answer_type, data in results.items():
        if data['std'] <= 0.5:
            consistency = "✅ 높음"
        elif data['std'] <= 1.0:
            consistency = "⚠️ 보통"
        else:
            consistency = "❌ 낮음"
        print(f"{answer_type}: 일관성 {consistency} (표준편차 {data['std']})")

    with open("evaluation/eval_consistency_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n결과 저장: evaluation/eval_consistency_results.json")


if __name__ == "__main__":
    run_consistency_test(n=10)