import asyncio, tempfile, wave
import grpc
from voxa.speech.v1 import asr_pb2, asr_pb2_grpc, audio_pb2

class AsrService(asr_pb2_grpc.ASRServicer):
    def __init__(self, engine):
        self.engine = engine

    async def StreamingRecognize(self, request_iterator, context):
        pcm = []
        sr = 16000
        async for req in request_iterator:
            fr = req.frame
            if fr.format != audio_pb2.AUDIO_FORMAT_PCM16:
                continue
            if fr.sample_rate_hz:
                sr = fr.sample_rate_hz
            pcm.append(bytes(fr.data))

        if not pcm:
            return
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
                for b in pcm: wf.writeframes(b)
            # final-only stub; add partials later
            parts = self.engine.recognize(tmp.name)
        text = " ".join(p["text"] for p in parts).strip()
        yield asr_pb2.StreamingRecognizeResponse(text=text, is_final=True)

    async def Recognize(self, request, context):
        sr = request.frames[0].sample_rate_hz if request.frames else 16000
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
                for fr in request.frames:
                    if fr.format == audio_pb2.AUDIO_FORMAT_PCM16:
                        wf.writeframes(fr.data)
            parts = self.engine.recognize(tmp.name)
        return asr_pb2.RecognizeResponse(
            transcript=" ".join(p["text"] for p in parts).strip(),
            tokens=[asr_pb2.Token(text=p["text"], is_final=True) for p in parts],
        )
