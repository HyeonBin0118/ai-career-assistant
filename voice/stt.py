import whisper
import os

_model = None

def get_model(model_size: str = "base"):
    """모델 한 번만 로드 (싱글톤)"""
    global _model
    if _model is None:
        print(f"[Whisper 모델 로딩: {model_size}]")
        _model = whisper.load_model(model_size)
    return _model


def transcribe(audio_path: str, model_size: str = "base") -> str:
    """
    wav 파일 → 한국어 텍스트 변환
    """
    if not audio_path or not os.path.exists(audio_path):
        return ""

    model = get_model(model_size)
    result = model.transcribe(audio_path, language="ko", fp16=False)
    text = result["text"].strip()
    print(f"[STT 결과]: {text}")
    return text