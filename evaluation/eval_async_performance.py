import time
import requests
import statistics

API = "http://localhost:8000/api/v1"
TEST_FILE = "test_async.mp3"

# 테스트용 더미 mp3 파일 생성 (없으면)
import struct
import wave
import os

def create_test_audio(filename, duration_sec=5):
    """테스트용 더미 wav 파일 생성"""
    if os.path.exists(filename):
        return
    import math
    sample_rate = 16000
    num_samples = sample_rate * duration_sec
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for i in range(num_samples):
            value = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            f.writeframes(struct.pack('<h', value))
    print(f"테스트 파일 생성: {filename}")


def measure_sync_response(question_id: int, n: int = 3):
    """기존 방식: 업로드 후 feedback까지 대기하는 총 시간"""
    times = []
    for i in range(n):
        with open(TEST_FILE, "rb") as f:
            start = time.time()
            res = requests.post(
                f"{API}/questions/{question_id}/answers",
                files={"audio": ("test.wav", f, "audio/wav")}
            )
            data = res.json()
            answer_id = data["answer_id"]

            # 폴링으로 완료까지 대기
            while True:
                status_res = requests.get(f"{API}/answers/{answer_id}/status")
                status = status_res.json()
                if status["status"] == "completed":
                    break
                time.sleep(0.5)

            elapsed = time.time() - start
            times.append(elapsed)
            print(f"  {i+1}회: {elapsed:.2f}초")
        time.sleep(2)
    return times


def measure_async_response(question_id: int, n: int = 3):
    """비동기 방식: 업로드 후 즉시 응답 시간만 측정"""
    times = []
    for i in range(n):
        with open(TEST_FILE, "rb") as f:
            start = time.time()
            res = requests.post(
                f"{API}/questions/{question_id}/answers",
                files={"audio": ("test.wav", f, "audio/wav")}
            )
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"  {i+1}회: {elapsed:.3f}초")
        time.sleep(2)
    return times


if __name__ == "__main__":
    create_test_audio(TEST_FILE)

    sessions = requests.get(f"{API}/sessions").json()
    if not sessions:
        print("세션이 없습니다. 먼저 면접 세션을 생성해주세요.")
        exit()

    session_id = sessions[0]["id"]
    session = requests.get(f"{API}/sessions/{session_id}").json()
    question_id = session["questions"][0]["id"]
    print(f"테스트 질문 ID: {question_id}")

    print("\n=== 비동기 처리 즉시 응답시간 측정 (n=5) ===")
    async_times = measure_async_response(question_id, n=5)

    print("\n=== 결과 ===")
    print(f"즉시 응답 평균: {statistics.mean(async_times):.3f}초")
    print(f"즉시 응답 최소: {min(async_times):.3f}초")
    print(f"즉시 응답 최대: {max(async_times):.3f}초")
    print(f"\n기존 동기 처리 대비: 30초+ → {statistics.mean(async_times):.1f}초 (사용자 체감 대기시간)")