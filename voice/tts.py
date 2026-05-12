import edge_tts
import asyncio
import tempfile
import os
import sounddevice as sd
import soundfile as sf

# 한국어 면접관 목소리 (남성: InJoonNeural, 여성: SunHiNeural)
KO_VOICE = "ko-KR-InJoonNeural"


async def _synthesize(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, KO_VOICE)
    await communicate.save(output_path)


def speak(text: str):
    """
    텍스트 → 음성 변환 후 즉시 재생
    """
    print(f"[면접관]: {text}")

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        asyncio.run(_synthesize(text, tmp_path))

        # mp3 재생
        data, samplerate = sf.read(tmp_path)
        sd.play(data, samplerate)
        sd.wait()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)