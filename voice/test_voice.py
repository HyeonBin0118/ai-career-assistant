from tts import speak
from recorder import record_until_silence
from stt import transcribe
from recorder import cleanup_audio_file

# TTS 테스트
speak("안녕하세요. 면접을 시작하겠습니다. 자기소개를 부탁드립니다.")

# STT 테스트
audio_path = record_until_silence()
if audio_path:
    text = transcribe(audio_path)
    print(f"인식된 텍스트: {text}")
    cleanup_audio_file(audio_path)