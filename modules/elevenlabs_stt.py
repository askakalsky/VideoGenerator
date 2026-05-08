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
MAX_SEGMENT_WORDS = 4  # max words per subtitle line (TikTok style)


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
            self.api_keys = [api_key]
        else:
            raw = os.getenv("ELEVENLABS_API_KEYS", "").replace('﻿', '')
            self.api_keys = [k.strip() for k in raw.split(",") if k.strip()]
            # fallback: old numbered format
            if not self.api_keys:
                for i in range(1, 10):
                    k = os.getenv(f"ELEVENLABS_API_KEY_{i}")
                    if k:
                        self.api_keys.append(k.strip())
            if not self.api_keys:
                raise ValueError(
                    "No ElevenLabs API key found. Set ELEVENLABS_API_KEYS in .env"
                )

    def transcribe(self, audio_path: Path) -> WhisperCompatibleResult:
        """
        Transcribe audio and return a Whisper-compatible result.
        Tries all API keys in rotation if one fails.
        """
        from elevenlabs.client import ElevenLabs

        audio_path = Path(audio_path)
        logger.info(f"🎙️  ElevenLabs STT: {audio_path.name}")

        last_error = None
        for i, key in enumerate(self.api_keys):
            try:
                client = ElevenLabs(api_key=key)
                with open(audio_path, "rb") as f:
                    raw = client.speech_to_text.convert(
                        file=f,
                        model_id="scribe_v1",
                        timestamps_granularity="word",
                    )
                break
            except Exception as e:
                logger.warning(f"STT key_{i+1} failed: {e}")
                last_error = e
        else:
            raise RuntimeError(f"All ElevenLabs STT keys failed. Last error: {last_error}")

        word_items = [
            w for w in (raw.words or [])
            if getattr(w, "type", None) == "word"
            and getattr(w, "start", None) is not None
            and getattr(w, "end", None) is not None
            and getattr(w, "text", "").strip()
        ]

        logger.info(f"   └─ Получено слов: {len(word_items)}")

        segments = self._group_into_segments(word_items)
        segments = self._split_long_segments(segments)
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

    def _split_long_segments(self, segments: List[Segment]) -> List[Segment]:
        """Split segments longer than MAX_SEGMENT_WORDS into smaller chunks."""
        result: List[Segment] = []
        for seg in segments:
            if len(seg.words) <= MAX_SEGMENT_WORDS:
                result.append(seg)
            else:
                for i in range(0, len(seg.words), MAX_SEGMENT_WORDS):
                    chunk = seg.words[i:i + MAX_SEGMENT_WORDS]
                    result.append(_make_segment(chunk))
        return result


def _make_segment(words: List[WordTiming]) -> Segment:
    return Segment(
        start=words[0].start,
        end=words[-1].end,
        text=" ".join(w.word for w in words),
        words=words,
    )
