from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input= "채용공고 크롤링 결과를 캐싱 대상으로 선택했습니다. 공고 내용은 단기간에 잘 바뀌지 않는 데이터라 캐싱 효과가 클 것이라고 판단했습니다.구현 방식은 요청이 들어오면 먼저 Redis에서 job:{url} 키를 확인합니다. 키가 있으면 바로 반환하고, 없으면 크롤링과 GPT 분석을 진행한 뒤 결과를 Redis에 저장합니다.TTL은 1시간으로 설정했는데, 채용공고가 하루 단위로 변경되는 경우가 많아서 1시간이 적절하다고 판단했습니다. TTL이 너무 짧으면 캐시 히트율이 낮아지고, 너무 길면 오래된 공고 내용을 반환할 수 있어서 균형을 고려했습니다.실제로 서버 로그에서 첫 번째 요청은 CACHE MISS, 두 번째 요청은 CACHE HIT가 찍히는 걸 직접 확인했고, 동일 공고 재요청 시 크롤링과 GPT 호출이 생략되면서 응답 속도가 크게 개선됐습니다."
)

response.stream_to_file("test_answer.mp3")
print("완료: 100 test_answer.mp3")