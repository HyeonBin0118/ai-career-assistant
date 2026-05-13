"""Whisper STT 모듈 - 음성 파일을 한국어 텍스트로 변환"""

import os
import whisper

_model = None
_model_size = None


def get_model(model_size: str = "medium") -> whisper.Whisper:
    """
    Whisper 모델 로드 (싱글톤).
    모델 크기가 변경되면 새로 로드함.
    """
    global _model, _model_size
    if _model is None or _model_size != model_size:
        print(f"[Whisper 모델 로딩: {model_size}]")
        _model = whisper.load_model(model_size)
        _model_size = model_size
    return _model


def transcribe(audio_path: str, model_size: str = "medium") -> str:
    """
    wav 파일을 한국어 텍스트로 변환.
    
    Args:
        audio_path: 오디오 파일 경로
        model_size: Whisper 모델 크기 (base/medium/large)
    
    Returns:
        인식된 텍스트 (실패 시 빈 문자열)
    """
    if not audio_path or not os.path.exists(audio_path):
        return ""

    model = get_model(model_size)
    result = model.transcribe(audio_path, language="ko", fp16=False)
    text = result["text"].strip()
    print(f"[STT 결과]: {text}")
    return text