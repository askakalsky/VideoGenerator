"""
ElevenLabs Speech-to-Text transcription with Whisper-compatible output format.
Replaces stable-whisper/torch dependency for GitHub Actions compatibility.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

PAUSE_THRESHOLD = 1.0  # seconds gap that triggers a new segment


# ---------------------------------------------------------------------------
# Whisper-compatible result dataclasses.
# SubtitleGenerator.generate() in tiktok_subs.py accesses via safe_getattr:
#   result.segments[i].start / end
#   result.segments[i].words[j].word   ← attribute name MUST be 'word'
#   result.segments[i].words[j].start / end
# ---------------------------------------------------------------------------

@dataclass
class WordTiming:
    word: str      # Must be named 'word' — used by SubtitleGenerator
    start: float
    end: float


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: List[WordTiming] = field(default_factory=list)


@dataclass
class WhisperCompatibleResult:
    segments: List[Segment] = field(default_factory=list)


class ElevenLabsTranscriber:
    """
    Transcribes audio using ElevenLabs STT API (scribe_v1).
    Returns a result object compatible with SubtitleGenerator.generate().
    """

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self.api_key = api_key
        else:
            raw = os.getenv("ELEVENLABS_API_KEYS", "")
            keys = [k.strip() for k in raw.split(",") if k.strip()]
            # fallback: old numbered format
            if not keys:
                for i in range(1, 10):
                    k = os.getenv(f"ELEVENLABS_API_KEY_{i}")
                    if k:
                        keys.append(k)
            if not keys:
                raise ValueError(
                    "No ElevenLabs API key found. Set ELEVENLABS_API_KEYS in .env"
                )
            self.api_key = keys[0]

    def transcribe(self, audio_path: Path) -> WhisperCompatibleResult:
        """
        Transcribe audio and return a Whisper-compatible result.

        Args:
            audio_path: Path to the audio file (MP3, WAV, etc.)

        Returns:
            WhisperCompatibleResult with .segments containing word timings.
        """
        from elevenlabs.client import ElevenLabs

        audio_path = Path(audio_path)
        logger.info(f"🎙️  ElevenLabs STT: {audio_path.name}")

        client = ElevenLabs(api_key=self.api_key)

        with open(audio_path, "rb") as f:
            raw = client.speech_to_text.convert(
                file=f,
                model_id="scribe_v1",
                timestamps_granularity="word",
            )

        word_items = [
            w for w in (raw.words or [])
            if getattr(w, "type", None) == "word"
            and getattr(w, "start", None) is not None
            and getattr(w, "end", None) is not None
            and getattr(w, "text", "").strip()
        ]

        logger.info(f"   └─ Получено слов: {len(word_items)}")

        segments = self._group_into_segments(word_items)
        logger.info(f"   └─ Сегментов: {len(segments)}")

        return WhisperCompatibleResult(segments=segments)

    def _group_into_segments(self, word_items: list) -> List[Segment]:
        """Group flat word list into segments separated by pauses > PAUSE_THRESHOLD."""
        if not word_items:
            return []

        segments: List[Segment] = []
        current_words: List[WordTiming] = []

        for i, w in enumerate(word_items):
            wt = WordTiming(
                word=getattr(w, "text", "").strip(),
                start=float(getattr(w, "start", 0.0)),
                end=float(getattr(w, "end", 0.0)),
            )
            current_words.append(wt)

            is_last = i == len(word_items) - 1
            if not is_last:
                next_start = getattr(word_items[i + 1], "start", None)
                if next_start is not None:
                    gap = float(next_start) - wt.end
                    if gap >= PAUSE_THRESHOLD:
                        segments.append(_make_segment(current_words))
                        current_words = []

        if current_words:
            segments.append(_make_segment(current_words))

        return segments


def _make_segment(words: List[WordTiming]) -> Segment:
    return Segment(
        start=words[0].start,
        end=words[-1].end,
        text=" ".join(w.word for w in words),
        words=words,
    )
