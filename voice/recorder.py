import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import os

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 2.0
MAX_DURATION = 60.0

def record_until_silence(device_index: int = None, shared_state: dict = None, silence_threshold: float = 0.02) -> str:
    recorded_frames = []
    silence_counter = 0
    speech_detected = False

    chunk_duration = 0.1
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)
    chunk_size = int(SAMPLE_RATE * chunk_duration)

    def callback(indata, frames, time, status):
        nonlocal silence_counter, speech_detected
        recorded_frames.append(indata.copy())
        volume = float(np.abs(indata).mean())

        if shared_state is not None:
            shared_state["level"] = volume

        if volume > silence_threshold:
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
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio_data, SAMPLE_RATE)
    return tmp.name


def cleanup_audio_file(filepath: str):
    if filepath and os.path.exists(filepath):
        os.remove(filepath)