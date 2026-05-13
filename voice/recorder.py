"""마이크 녹음 모듈 - silence detection 기반 자동 종료"""

import os
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf

# 기본 설정값
SAMPLE_RATE = 16000
SILENCE_DURATION = 2.0   # 무음 지속 시간 (초)
MAX_DURATION = 60.0      # 최대 녹음 시간 (초)
CHUNK_DURATION = 0.1     # 음량 체크 주기 (초)


def record_until_silence(
    device_index: int = None,
    shared_state: dict = None,
    silence_threshold: float = 0.02
) -> str:
    """
    마이크 녹음 시작, 무음이 일정 시간 지속되면 자동 종료.
    
    Args:
        device_index: 마이크 장치 인덱스 (None이면 기본 장치)
        shared_state: UI와 오디오 레벨 공유용 딕셔너리 {"level": float}
        silence_threshold: 무음 판단 임계값 (높을수록 쉽게 무음 판단)
    
    Returns:
        녹음된 wav 파일 경로 (실패 시 None)
    """
    recorded_frames = []
    silence_counter = 0
    speech_detected = False

    chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
    silence_chunks_needed = int(SILENCE_DURATION / CHUNK_DURATION)

    def callback(indata, frames, time, status):
        """오디오 스트림 콜백 - 프레임 저장 및 음량 측정"""
        nonlocal silence_counter, speech_detected
        recorded_frames.append(indata.copy())
        volume = float(np.abs(indata).mean())

        # UI 스펙트럼 표시용 레벨 공유
        if shared_state is not None:
            shared_state["level"] = volume

        # 발화 감지 및 무음 카운트
        if volume > silence_threshold:
            speech_detected = True
            silence_counter = 0
        elif speech_detected:
            silence_counter += 1

    # 녹음 시작
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=chunk_size,
        callback=callback,
        device=device_index,
    ):
        max_chunks = int(MAX_DURATION / CHUNK_DURATION)
        for _ in range(max_chunks):
            sd.sleep(int(CHUNK_DURATION * 1000))
            if speech_detected and silence_counter >= silence_chunks_needed:
                break

    if not recorded_frames:
        return None

    # 임시 wav 파일로 저장
    audio_data = np.concatenate(recorded_frames, axis=0)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio_data, SAMPLE_RATE)
    return tmp.name


def cleanup_audio_file(filepath: str):
    """임시 오디오 파일 삭제"""
    if filepath and os.path.exists(filepath):
        os.remove(filepath)