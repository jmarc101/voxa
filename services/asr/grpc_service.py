#!/usr/bin/env python3
"""
Minimal gRPC **bi‑di streaming** server+client using an **asyncio.Queue** (single FIFO).

- Server uses a background **reader()** to `q.put(...)` inbound messages in order.
- Main handler loop does `ev = await q.get()` and `yield`s responses when it wants.
- No partials; only FINAL on FLUSH/END + ACKs to keep it super tiny.

Run:
  # terminal 1
  python grpc_stream_queue_minimal.py server

  # terminal 2
  python grpc_stream_queue_minimal.py client

Prereqs:
  • Generated stubs for your proto (voxa.speech.v1.asr.proto)
  • `audio_sliding_window.py` present (from earlier)
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from enum import Enum, auto
import contextlib

import numpy as np
from grpc import aio
from google.protobuf.timestamp_pb2 import Timestamp

from voxa.speech.v1 import asr_pb2 as pb
from voxa.speech.v1 import asr_pb2_grpc as pb_grpc
from core.sliding_window import AudioSlidingWindow

SAMPLE_RATE = 16000


# ----------------------------- small helpers ---------------------------------
class Ev(Enum):
    AUDIO = auto()
    CONTROL = auto()


@dataclass
class Event:
    """
    Event is a single event in the event queue.
    """
    kind: Ev  # AUDIO or CONTROL
    data: bytes | None = None  # for AUDIO
    ctrl: pb.ControlType | None = None  # for CONTROL
    utt_id: str = ""  # Utterance ID


class AsrService(pb_grpc.AsrServicer):
    async def StreamingRecognize(self, request_iterator, context: aio.ServicerContext):
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=512)  # single FIFO preserves order
        win = AudioSlidingWindow(window_size_ms=3000, sample_rate_hz=SAMPLE_RATE)
        current_utt = ""

        async def reader():
            try:
                async for req in request_iterator:                 # receive ONE message at a time
                    if not current_utt and req.utterance_id:
                        # capture first seen utterance id
                        nonlocal current_utt
                        current_utt = req.utterance_id
                    if req.HasField("audio"):
                        await q.put(Event(Ev.AUDIO, data=req.audio.data, utt=current_utt))
                    elif req.HasField("control"):
                        await q.put(Event(Ev.CONTROL, ctrl=req.control.type, utt=current_utt))
            finally:
                # If client disconnects, finalize once
                await q.put(Event(Ev.CONTROL, ctrl=pb.ControlType.END, utt=current_utt))

        reader_task = asyncio.create_task(reader())

        try:
            while True:
                ev = await q.get()                              # wait for next enqueued event
                if ev.kind is Ev.AUDIO and ev.data:
                    win.append(ev.data)                         # update rolling window
                    continue                                    # no response yet (no partials)

                # CONTROL
                if ev.ctrl == pb.ControlType.FLUSH:
                    text = win.full(as_float=True).tobytes().decode("utf-8")
                    # FINAL
                    yield pb.StreamingRecognizeResponse(
                        utterance_id=ev.utt,
                        type=pb.ResponseType.FINAL,
                        final_transcript=pb.Transcript(text=text),
                    )
                    # ACK
                    yield pb.StreamingRecognizeResponse(
                        utterance_id=ev.utt,
                        type=pb.ResponseType.CONTROL_ACK,
                        control_ack=pb.ControlAck(type=pb.ControlType.FLUSH, message="flushed"),
                    )
                    win.clear()

                elif ev.ctrl == pb.ControlType.END:
                    text = await decode_stub_f32(win.full(as_float=True))
                    if text:
                        yield pb.StreamingRecognizeResponse(
                            utterance_id=ev.utt,
                            type=pb.ResponseType.FINAL,
                            final_transcript=pb.Transcript(text=text),
                        )
                    yield pb.StreamingRecognizeResponse(
                        utterance_id=ev.utt,
                        type=pb.ResponseType.CONTROL_ACK,
                        control_ack=pb.ControlAck(type=pb.ControlType.END, message="ended"),
                    )
                    break  # close RPC

                else:
                    # optional ACK for other controls (noop)
                    yield pb.StreamingRecognizeResponse(
                        utterance_id=ev.utt,
                        type=pb.ResponseType.CONTROL_ACK,
                        control_ack=pb.ControlAck(type=ev.ctrl or 0, message="noop"),
                    )
        finally:
            reader_task.cancel()
            with contextlib.suppress(Exception):
                await reader_task

