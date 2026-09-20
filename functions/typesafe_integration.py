# TypeSafe integration for AutoAnimeBot
# Applies cookbook patterns:
#   - pre_parsed_value_extraction (anime filename parsing)
#   - classification_using_confidence (upload mode selection)
#   - function_calling style dispatcher (Executors routing)
#
# Requires:  pip install "typesafe-sdk>=0.5.7"
# Env:        TYPESAFE_API_KEY

import asyncio
import os
import re
from typesafe_sdk import Choice, Noul, TypeSafeClient

# ------------------------------------------------------------------
# Config / client (cached for replay without live calls)
# ------------------------------------------------------------------

TYPESAFE_MODEL = os.environ.get("TYPESAFE_MODEL", "jev-1.12")

# Gate every call on a real API key: without one the client would send
# requests with a placeholder credential and burn a 30s timeout per call.
TYPESAFE_ENABLED = bool(os.environ.get("TYPESAFE_API_KEY"))

client = TypeSafeClient(
    api_key=os.environ.get("TYPESAFE_API_KEY", "cache-only"),
    base_url=os.environ.get("TYPESAFE_BASE_URL"),
    timeout=30.0,
)

# ------------------------------------------------------------------
# 1. Pre-parsed value extraction  (cookbook: pre_parsed_value_extraction)
#    Regex finds candidates from the parsed anitopy text; TypeSafe picks.
# ------------------------------------------------------------------

EPISODE_RE = re.compile(r"(?:EP?|E)\s*(\d{1,3})", re.IGNORECASE)
QUALITY_RE = re.compile(r"\b(480p|720p|1080p|2160p)\b")
TITLE_RE = re.compile(r"([A-Z][A-Za-z0-9\s\-:]+?)\s*(?:\[|S\d+|EP?\d+|480p|720p|1080p)")

NONE_LABEL = "none"


def find_candidates(pattern: re.Pattern, text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in pattern.finditer(text):
        span = match.group(1) if match.lastindex else match.group(0)
        span = span.strip()
        if span and span not in seen:
            seen.add(span)
            out.append(span)
    return out


def pick_episode(document_text: str, candidates: list[str]) -> dict:
    """TypeSafe selects which candidate is the episode number."""
    criteria = {c: None for c in candidates} | {NONE_LABEL: "No episode number in this title"}
    answer = client.system_one(
        state={"filename": document_text},
        questions={
            "episode": Choice(
                instructions=(
                    "Which of these spans is the episode number for this anime file? "
                    "Pick the numeric episode identifier, not a season or quality tag."
                ),
                criteria=criteria,
            )
        },
        model=TYPESAFE_MODEL,
    ).answers["episode"]
    return {"choice": answer.choice, "confidence": answer.confidence}


def pick_quality(document_text: str, candidates: list[str]) -> dict:
    criteria = {c: None for c in candidates} | {NONE_LABEL: "No quality tag found"}
    answer = client.system_one(
        state={"filename": document_text},
        questions={
            "quality": Choice(
                instructions="Which of these spans is the video resolution (quality) of this anime file?",
                criteria=criteria,
            )
        },
        model=TYPESAFE_MODEL,
    ).answers["quality"]
    return {"choice": answer.choice, "confidence": answer.confidence}


async def pick_episode_async(document_text: str, candidates: list[str]) -> dict:
    """Run pick_episode off the event loop (SDK call is blocking, 30s timeout)."""
    return await asyncio.to_thread(pick_episode, document_text, candidates)


async def pick_quality_async(document_text: str, candidates: list[str]) -> dict:
    """Run pick_quality off the event loop."""
    return await asyncio.to_thread(pick_quality, document_text, candidates)


# ------------------------------------------------------------------
# 2. Classification using confidence  (cookbook: classification_using_confidence)
#    Upload mode selection with a confidence threshold so uncertain
#    decisions fall back to manual review instead of making wrong calls.
# ------------------------------------------------------------------

CONFIDENT_THRESHOLD = 0.85  # below this = send to admin review


async def classify_upload_mode_async(
    document_text: str, is_original_config: bool, is_button_config: bool
) -> dict:
    """Run classify_upload_mode off the event loop."""
    return await asyncio.to_thread(
        classify_upload_mode, document_text, is_original_config, is_button_config
    )


def classify_upload_mode(document_text: str, is_original_config: bool, is_button_config: bool) -> dict:
    """Classify the upload strategy and report whether to trust the answer."""
    # Build options from the DB configurations (same logic as bot.py)
    options = []
    descriptions: dict[str, str] = {}
    if is_original_config:
        options.append("original_rename")
        descriptions["original_rename"] = "Rename to season-episode format and upload as original (no compression)."
    if is_button_config:
        options.append("button_upload")
        descriptions["button_upload"] = "Compress and upload with a button linking back to the bot."
    if not is_button_config and not is_original_config:
        options.append("default_compress")
        descriptions["default_compress"] = "Default: compress without button or original rename."
    options.append("manual_review")
    descriptions["manual_review"] = "Send to admin review — configuration is ambiguous or low confidence."

    answer = client.system_one(
        state={
            "filename": document_text,
            "original_upload": is_original_config,
            "button_upload": is_button_config,
        },
        questions={
            "mode": Choice(
                instructions=(
                    "What upload mode should apply to this anime file? "
                    "Match against the configuration flags and the filename evidence."
                ),
                criteria=descriptions,
            )
        },
        model=TYPESAFE_MODEL,
    ).answers["mode"]

    sure = answer.confidence >= CONFIDENT_THRESHOLD
    label = answer.choice if sure else "manual_review"
    return {
        "label": label,
        "group": answer.choice,  # the raw model choice
        "confidence": answer.confidence,
        "level": "action" if sure else "review",
    }

# ------------------------------------------------------------------
# 3. Function-calling dispatcher  (cookbook: function_calling)
#    Maps a user/config description to typed arguments the code consumes.
# ------------------------------------------------------------------

# These mirror the arguments in core/executors.py and bot.py
UPLOAD_SPEC = {
    "original_rename": {
        "question": "Should the file be renamed to the season-episode format (original upload)?",
        "stated": "Does the configuration or filename indicate an original upload?",
    },
    "button_upload": {
        "question": "Should the upload include a button back to the bot?",
        "stated": "Is button_upload enabled in the DB config?",
    },
    "compress_first": {
        "question": "Should the file be compressed before upload?",
        "stated": "Is this not an original upload?",
    },
}


def build_executor_questions(configurations: dict) -> dict:
    """Build the speculative fan-out of questions the dispatcher needs."""
    questions: dict = {}
    for arg_key, spec in UPLOAD_SPEC.items():
        # Noul: does the evidence support this argument?
        questions[arg_key] = Noul(
            instructions=spec["question"],
            criteria=f"Yes if the evidence (filename/config) supports {arg_key}; no otherwise.",
        )
    return questions


# ------------------------------------------------------------------
# Example usage (not called automatically — called from bot.py / info.py)
# ------------------------------------------------------------------

def example_usage():
    # Pre-parsed extraction on an anime filename
    filename_text = "[SubsPlease] Attack on Titan - S04E14 (1080p) [ABCDEF].mkv"
    ep_candidates = find_candidates(EPISODE_RE, filename_text)
    quality_candidates = find_candidates(QUALITY_RE, filename_text)
    print("episode candidates:", ep_candidates)
    print("quality candidates:", quality_candidates)
    # In production: pass the parsed anitopy result as the text state instead

    # Classification of upload mode
    mode_result = classify_upload_mode(
        filename_text,
        is_original_config=True,
        is_button_config=False,
    )
    print("upload mode classification:", mode_result)
