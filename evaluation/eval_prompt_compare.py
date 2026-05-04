import json
import os
import statistics
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

QUESTION = "Redis를 사용한 경험에 대해 설명해 주세요."
DURATION = 90.0
TIME_SCORE = 5

TEST_ANSWERS = {
    "좋은 답변": "Mock Interview AI 프로젝트에서 Redis를 캐싱 용도로 활용했습니다. 채용공고 URL을 키로 하고 크롤링+GPT 분석 결과를 값으로 저장해 TTL을 1시간으로 설정했습니다. 동일 공고 재요청 시 크롤링 6,538ms가 제거되어 전체 응답시간이 34초에서 25초로 약 25% 단축됐습니다.",
    "보통 답변": "Redis는 캐싱 용도로 사용해봤습니다. 자주 조회되는 데이터를 Redis에 저장해두면 데이터베이스 부하를 줄일 수 있습니다.",
    "나쁜 답변": "저는 팀워크를 중요하게 생각합니다. 프로젝트에서 팀원들과 소통하며 협업하는 것을 즐깁니다."
}


def evaluate_old_prompt(question, answer):
    """개선 전 프롬프트 — 질문 관련성 기준 없음"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
면접 질문과 답변을 평가해줘.

평가 기준:
- logic_score: 논리성 (1~5) — 답변이 논리적으로 구성되어 있는가
- specificity_score: 구체성 (1~5) — 구체적인 사례나 수치를 포함하는가
- total_score: logic_score + specificity_score + {TIME_SCORE}
- feedback: 한 줄 개선 피드백

질문: {question}
답변: {answer}
JSON만 반환해.
"""}],
        temperature=0
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    data = json.loads(result)
    data['time_score'] = TIME_SCORE
    data['total_score'] = data.get('logic_score', 0) + data.get('specificity_score', 0) + TIME_SCORE
    return data


def evaluate_new_prompt(question, answer):
    """개선 후 프롬프트 — 질문 무관 시 1점 명시"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
면접 질문과 답변을 평가해줘.

**중요: 답변이 질문의 의도와 무관하거나 엉뚱한 내용이면 logic_score를 1점으로 준다.**

평가 기준:
- logic_score: 논리성 (1~5)
  * 1점: 질문과 전혀 무관한 답변
  * 2점: 질문과 약간 관련있지만 핵심을 벗어남
  * 3점: 질문에 답하고 있으나 근거가 부족함
  * 4점: 질문에 잘 답하고 있고 근거가 있음
  * 5점: 질문 의도를 완벽히 파악하고 명확한 근거와 함께 답변
- specificity_score: 구체성 (1~5)
  * 1점: 구체적 사례/수치/기술명 전혀 없음
  * 3점: 일부 구체적 내용 포함
  * 5점: 구체적 수치, 사례, 기술명 풍부하게 포함
- total_score: logic_score + specificity_score + {TIME_SCORE}
- feedback: 한 줄 개선 피드백

질문: {question}
답변: {answer}
JSON만 반환해.
"""}],
        temperature=0
    )
    result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    data = json.loads(result)
    data['time_score'] = TIME_SCORE
    data['total_score'] = data.get('logic_score', 0) + data.get('specificity_score', 0) + TIME_SCORE
    return data


if __name__ == "__main__":
    print("=== 프롬프트 개선 전/후 비교 테스트 ===\n")
    print(f"{'답변 유형':<12} {'개선 전 총점':>12} {'개선 후 총점':>12} {'차이':>6}")
    print("-" * 50)

    for answer_type, answer_text in TEST_ANSWERS.items():
        old = evaluate_old_prompt(QUESTION, answer_text)
        new = evaluate_new_prompt(QUESTION, answer_text)
        diff = new['total_score'] - old['total_score']
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        print(f"{answer_type:<12} {old['total_score']:>12} {new['total_score']:>12} {diff_str:>6}")

    print("\n=== 상세 결과 ===")
    for answer_type, answer_text in TEST_ANSWERS.items():
        print(f"\n[{answer_type}]")
        old = evaluate_old_prompt(QUESTION, answer_text)
        new = evaluate_new_prompt(QUESTION, answer_text)
        print(f"  개선 전: 논리={old['logic_score']} 구체성={old['specificity_score']} 총점={old['total_score']}")
        print(f"  개선 후: 논리={new['logic_score']} 구체성={new['specificity_score']} 총점={new['total_score']}")
        print(f"  개선 전 피드백: {old['feedback']}")
        print(f"  개선 후 피드백: {new['feedback']}")