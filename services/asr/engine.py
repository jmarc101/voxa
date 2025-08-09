import math
from faster_whisper import WhisperModel

DEFAULT_MODEL = "small.en"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

class AsrEngine:
    def __init__(self,
                 model: str = DEFAULT_MODEL,
                 device: str = DEVICE,
                 compute_type: str = COMPUTE_TYPE):
        self._model = WhisperModel(
            model, device=device, compute_type=compute_type)

    def recognize(self, audio_path: str):
        segments, info = self._model.transcribe(audio_path, language="en", word_timestamps=False)

        result = []
        for i, seg in enumerate(segments, start=1):
            result.append({
                "id": f"Seg#{i}-id:{seg.id}",
                "start_time": seg.start,
                "end_time": seg.end,
                "text": seg.text.strip(),
                "avg_logprob": float(seg.avg_logprob),
                "confidence": math.exp(float(seg.avg_logprob)),
                "language": info.language,
            })

        return result
