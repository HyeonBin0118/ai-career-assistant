import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import os

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01   # 이 이하면 무음으로 판단
SILENCE_DURATION = 2.0     # 무음 2초 지속되면 녹음 종료
MAX_DURATION = 60.0        # 최대 60초 녹음

def record_until_silence(device_index: int = None) -> str:
    """
    마이크로 녹음 시작, silence 2초 감지되면 자동 종료.
    녹음된 오디오를 임시 wav 파일 경로로 반환.
    """
    print("[녹음 중... 말을 마치면 자동으로 종료됩니다]")

    recorded_frames = []
    silence_counter = 0
    speech_detected = False

    # silence 판단 기준: SILENCE_DURATION초 / chunk 크기
    chunk_duration = 0.1  # 100ms 단위로 체크
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)
    chunk_size = int(SAMPLE_RATE * chunk_duration)

    def callback(indata, frames, time, status):
        nonlocal silence_counter, speech_detected
        recorded_frames.append(indata.copy())

        volume = np.abs(indata).mean()

        if volume > SILENCE_THRESHOLD:
            speech_detected = True
            silence_counter = 0
        else:
            if speech_detected:
                silence_counter += 1

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32',
        blocksize=chunk_size,
        callback=callback,
        device=device_index
    ):
        max_chunks = int(MAX_DURATION / chunk_duration)
        for _ in range(max_chunks):
            sd.sleep(int(chunk_duration * 1000))
            if speech_detected and silence_counter >= silence_chunks_needed:
                break

    if not recorded_frames:
        return None

    audio_data = np.concatenate(recorded_frames, axis=0)

    # 임시 파일로 저장
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio_data, SAMPLE_RATE)
    print(f"[녹음 완료: {len(audio_data)/SAMPLE_RATE:.1f}초]")

    return tmp.name


def cleanup_audio_file(filepath: str):
    """임시 오디오 파일 삭제"""
    if filepath and os.path.exists(filepath):
        os.remove(filepath)