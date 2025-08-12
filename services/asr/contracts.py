from typing import AsyncIterator, TypedDict, Protocol

# --------- Types ---------
class TranscriptEvent(TypedDict):
    utterance_id: str
    """
    Unique identifier for the utterance.
    """
    rev: int
    """
    Revision number of the transcript.
    """
    text: str
    """
    Full-replace hypothesis.
    """
    is_final: bool
    """
    Whether the transcript is final.
    """


# --------- Protocols ---------
class ASRStream(Protocol):
    async def add_audio(self, data: bytes) -> None: ...
    """
    Add audio data to the stream. This should be called with the raw audio data.
    """
    async def end_input(self) -> None: ...
    """
    End the input stream. This should be called when the utterance is complete.
    """
    async def events(self) -> AsyncIterator[TranscriptEvent]: ...
    """
    Stream transcript events. This is a generator that yields TranscriptEvent objects.
    """
    async def aclose(self) -> None: ...
    """
    Close the stream. This should be called when the stream is no longer needed.
    This is a good place to clean up any resources used by the stream.
    """


class ASREngine(Protocol):
    """
    ASR engine interface.
    """
    sample_rate_hz: int
    """
    The sample rate of the audio data.
    """
    async def start_stream(self, *, utterance_id: str) -> ASRStream: ...
