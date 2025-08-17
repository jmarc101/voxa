import asyncio, tempfile, wave
import grpc
from voxa.speech.v1 import asr_pb2, asr_pb2_grpc, audio_pb2

class AsrService(asr_pb2_grpc.AsrServicer):
    def __init__(self, engine):
        self.engine = engine

    async def StreamingRecognize(self, request_iterator, context):
        pass

    async def Recognize(self, request, context):
        pass
