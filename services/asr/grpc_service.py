import asyncio, tempfile, wave
import grpc
from voxa.speech.v1 import asr_pb2, asr_pb2_grpc, audio_pb2

class AsrService(asr_pb2_grpc.ASRServicer):
    def __init__(self, engine):
        self.engine = engine

    async def StreamingRecognize(self, request_iterator, context):
        # 1) Init on first valid frame
        session = None
        sr = 16000

        try:
            async for req in request_iterator:
                fr = req.frame
                if fr.format != audio_pb2.AUDIO_FORMAT_PCM16:
                    continue

                if session is None:
                    if fr.sample_rate_hz:
                        sr = fr.sample_rate_hz
                    # Start a streaming session with your engine
                    # (adjust args to your engine)
                    session = self.engine.start_stream(sample_rate_hz=sr, channels=1)

                # 2) Feed PCM16 bytes to engine
                session.add_audio(bytes(fr.data))

                # 3) Drain any partial hypotheses without blocking
                # Return 0..N partials per chunk, marked as non-final
                for hyp in session.drain_partials():   # e.g., [{"text": "..."}]
                    if context.is_active():
                        yield asr_pb2.StreamingRecognizeResponse(
                            text=hyp["text"], is_final=False
                        )

                # Optional: respect client cancellation early
                if context.cancelled():
                    return

            # 4) Stream ended: finalize and emit one last result
            if session:
                final = session.finish()               # e.g., [{"text": "..."}]
                text = " ".join(p["text"] for p in final).strip()
                if text:
                    yield asr_pb2.StreamingRecognizeResponse(text=text, is_final=True)

        finally:
            # 5) Always release engine resources
            if session:
                session.close()

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
