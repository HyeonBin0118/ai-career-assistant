"""Edge-TTS 모듈 - 면접관 음성 출력"""

import os
import asyncio
import tempfile
import edge_tts
import sounddevice as sd
import soundfile as sf

# 한국어 면접관 목소리 (남성)
VOICE = "ko-KR-InJoonNeural"


async def _synthesize(text: str, output_path: str):
    """텍스트를 음성 파일로 변환 (비동기)"""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)


def speak(text: str):
    """
    텍스트를 음성으로 변환 후 즉시 재생.
    
    Args:
        text: 면접관이 말할 텍스트
    """
    print(f"[면접관]: {text}")

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        asyncio.run(_synthesize(text, tmp_path))
        data, samplerate = sf.read(tmp_path)
        sd.play(data, samplerate)
        sd.wait()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)