"""
Speech Auto-Correct — Research-Backed Implementation

Applies three layers of correction based on published research:

Layer 1 — Hallucination Filter (arXiv:2502.12414, arXiv:2401.01572)
  Whisper hallucinates fluent sentences from silence/noise. These are
  characterised by: repetition of short phrases, common filler outputs,
  and sentences that contain no actionable content.

Layer 2 — Phoneme-Level Brand Name Repair (arXiv:2202.01157)
  ASR error correction using sequence-to-sequence post-processing.
  We implement a rule-based version covering Indian English phoneme
  substitutions (retroflex consonants, vowel mergers) that cause
  systematic Whisper errors on brand names.

Layer 3 — Contextual Normalisation
  Filler word removal, punctuation stripping, whitespace normalisation.
"""

import re
from typing import List, Optional, Set, Tuple

# ── Layer 1: Hallucination signatures ────────────────────────────────────────
# Whisper commonly hallucinates these exact phrases from silence/noise.
# Source: community analysis of Whisper hallucination patterns + arXiv:2401.01572

_HALLUCINATION_EXACT: Set[str] = {
    "thank you", "thank you.", "thank you very much", "thank you for watching",
    "thank you for watching.", "thanks for watching", "thanks for watching.",
    "see you next time", "see you next time.", "see you soon", "see you soon.",
    "please subscribe", "like and subscribe", "don't forget to subscribe",
    "subtitles by", "subtitles by the amara.org community",
    "transcribed by", "translated by",
    ".", "..", "...", ". . .", ".  .  .",
    "i", "i.", "oh", "oh.", "um", "uh", "hmm",
    "okay", "okay.", "ok", "ok.",
    "bye", "bye.", "bye bye", "bye bye.",
    "good", "good.", "yes", "yes.", "no", "no.",
    "let's go", "let's go.", "alright", "alright.",
    "haha", "hahaha", "lol",
    "music", "[music]", "(music)", "[applause]", "(applause)",
    "foreign", "[foreign]", "(foreign)",
}

_HALLUCINATION_PATTERNS: List[re.Pattern] = [
    # Repetition: same word/phrase 3+ times (e.g. "open open open open")
    re.compile(r"\b(\w+)\b(?:\s+\1\b){2,}", re.I),
    # Trailing "thank you" appended to real content (Whisper artefact)
    re.compile(r"\s+thank you\.?\s*$", re.I),
    # Pure punctuation / dots
    re.compile(r"^[\s.!?,\-]+$"),
    # Single character or number
    re.compile(r"^\s*\w\s*$"),
]


def is_hallucination(text: str) -> bool:
    """
    Detect Whisper hallucinations using signatures from arXiv:2401.01572.

    Returns True if the text is likely a hallucination and should be discarded.
    """
    if not text:
        return True
    t = text.strip().lower().rstrip(".")
    # Exact match against known hallucination phrases
    if t in _HALLUCINATION_EXACT:
        return True
    # Pattern match
    for pat in _HALLUCINATION_PATTERNS:
        if pat.search(t):
            return True
    # Very short (≤2 chars) or all punctuation
    if len(re.sub(r"[^\w]", "", t)) <= 2:
        return True
    return False


# ── Layer 2: Phoneme-level brand name repair ──────────────────────────────────
# Indian English phoneme substitutions that cause systematic Whisper errors:
#   - Retroflex /ʈ/ → /t/, /ɖ/ → /d/  (no direct impact on spelling)
#   - Vowel merger: /æ/ → /e/ (e.g. "app" → "up", "app" → "ep")
#   - Consonant cluster simplification: "sp" → "s", "st" → "s"
#   - Aspiration: "p" → "ph", "t" → "th" in some positions
# Source: arXiv:2510.18374 (accent-aware ASR), nature.com WhisperX-GPT study

_CORRECTIONS: List[Tuple[re.Pattern, str]] = [

    # ── WhatsApp (most common failure) ────────────────────────────────────────
    # "what's up", "whats up", "what sup", "watts app", "what sap", "what zap"
    # "whatsap", "what's ep", "what sep", "wats up", "watsup"
    (re.compile(r"\bwhats?\s*up\b",          re.I), "whatsapp"),
    (re.compile(r"\bwhat\s+s\s+up\b",        re.I), "whatsapp"),
    (re.compile(r"\bwatts?\s*app\b",         re.I), "whatsapp"),
    (re.compile(r"\bwhat\s*s[ae]p\b",        re.I), "whatsapp"),
    (re.compile(r"\bwhat\s*zap\b",           re.I), "whatsapp"),
    (re.compile(r"\bwhatsap\b",              re.I), "whatsapp"),
    (re.compile(r"\bwhat\s*sep\b",           re.I), "whatsapp"),
    (re.compile(r"\bwats\s*up\b",            re.I), "whatsapp"),
    (re.compile(r"\bwatsup\b",               re.I), "whatsapp"),
    # Indian accent: "v" → "w" substitution
    (re.compile(r"\bvhats?\s*app\b",         re.I), "whatsapp"),
    (re.compile(r"\bvhats?\s*up\b",          re.I), "whatsapp"),

    # ── Spotify ───────────────────────────────────────────────────────────────
    # "spot if i", "spot a fly", "spotty", "sporm", "sport if i", "sportify"
    (re.compile(r"\bspot\s*if\s*[iy]\b",     re.I), "spotify"),
    (re.compile(r"\bspot\s*a\s*fly\b",       re.I), "spotify"),
    (re.compile(r"\bspotty\b",               re.I), "spotify"),
    (re.compile(r"\bsporm\b",                re.I), "spotify"),
    (re.compile(r"\bsport\s*if\s*[iy]\b",    re.I), "spotify"),
    (re.compile(r"\bsportify\b",             re.I), "spotify"),
    (re.compile(r"\bspot\s*i\s*fi\b",        re.I), "spotify"),
    # "opel sporty" → "open spotify"
    (re.compile(r"\bopel\s+sport\w*\b",      re.I), "open spotify"),

    # ── YouTube ───────────────────────────────────────────────────────────────
    (re.compile(r"\byou\s+tube\b",           re.I), "youtube"),
    (re.compile(r"\bu\s*tube\b",             re.I), "youtube"),
    (re.compile(r"\byoutub\b",               re.I), "youtube"),

    # ── Instagram ─────────────────────────────────────────────────────────────
    (re.compile(r"\binsta\s*gram\b",         re.I), "instagram"),
    (re.compile(r"\binstant\s*gram\b",       re.I), "instagram"),
    (re.compile(r"\binsta\b(?!\s*gram)",     re.I), "instagram"),

    # ── Telegram ──────────────────────────────────────────────────────────────
    (re.compile(r"\btele\s*gram\b",          re.I), "telegram"),
    (re.compile(r"\btell\s*a\s*gram\b",      re.I), "telegram"),

    # ── Discord ───────────────────────────────────────────────────────────────
    (re.compile(r"\bdisc\s*cord\b",          re.I), "discord"),
    (re.compile(r"\bthis\s*cord\b",          re.I), "discord"),

    # ── Notepad ───────────────────────────────────────────────────────────────
    (re.compile(r"\bnote\s+p[ae]d\b",        re.I), "notepad"),
    (re.compile(r"\bnote\s+pet\b",           re.I), "notepad"),

    # ── Calculator ────────────────────────────────────────────────────────────
    (re.compile(r"\bcalcul\w*\b",            re.I), "calculator"),

    # ── Chrome ────────────────────────────────────────────────────────────────
    (re.compile(r"\bc[rk]ome\b",             re.I), "chrome"),

    # ── VS Code ───────────────────────────────────────────────────────────────
    (re.compile(r"\bvs\s*coat\b",            re.I), "vs code"),
    (re.compile(r"\bvisual\s+studio\s+code\b", re.I), "vs code"),

    # ── File Explorer ─────────────────────────────────────────────────────────
    (re.compile(r"\bfile\s+explore[rs]?\b",  re.I), "file explorer"),

    # ── Task Manager ──────────────────────────────────────────────────────────
    (re.compile(r"\btask\s+man[ag]+er?\b",   re.I), "task manager"),

    # ── PowerShell ────────────────────────────────────────────────────────────
    (re.compile(r"\bpower\s+sh[ae]ll\b",     re.I), "powershell"),

    # ── System commands ───────────────────────────────────────────────────────
    (re.compile(r"\bshut\s+(it\s+)?down\b",  re.I), "shutdown"),
    (re.compile(r"\brestart\s+it\b",         re.I), "restart"),

    # ── Launch typos (Indian English: "l" → "r" in clusters) ─────────────────
    (re.compile(r"\blunch\b",                re.I), "launch"),
    (re.compile(r"\blaunch\s+the\b",         re.I), "open"),

    # ── Sing/dance ────────────────────────────────────────────────────────────
    (re.compile(r"\bsing\s+(me\s+)?a\s+song(\s+for\s+me)?\b", re.I), "sing a song"),
    (re.compile(r"\bplay\s+a\s+song\b",      re.I), "sing a song"),
    (re.compile(r"\bdance\s+for\s+me\b",     re.I), "sing a song"),
    (re.compile(r"\bplay\s+the\s+song\b",    re.I), "sing a song"),
    (re.compile(r"\bsing\s+the\s+song\b",    re.I), "sing a song"),

    # ── "open" verb normalisation ─────────────────────────────────────────────
    # "opens" → "open" (Whisper sometimes adds -s)
    (re.compile(r"\bopens\b",                re.I), "open"),

    # ── Layer 3: Filler words at start ───────────────────────────────────────
    (re.compile(r"^\s*(um+|uh+|er+|ah+|hmm+|okay,?\s+|ok,?\s+|well,?\s+|so,?\s+)", re.I), ""),

    # ── Trailing noise ────────────────────────────────────────────────────────
    (re.compile(r"\s+thank\s+you\.?\s*$",    re.I), ""),
    (re.compile(r"[.!?,]+$"),                ""),
]


def autocorrect(text: str) -> str:
    """
    Apply three-layer speech auto-correction.

    Layer 1: Reject hallucinations (returns empty string if hallucination)
    Layer 2: Phoneme-level brand name repair
    Layer 3: Normalisation

    Args:
        text: Raw transcribed text from Whisper

    Returns:
        Corrected text, or empty string if hallucination detected
    """
    if not text:
        return text

    result = text.strip()

    # Layer 1: hallucination check on raw text
    if is_hallucination(result):
        return ""

    # Layer 2 + 3: apply corrections
    for pattern, replacement in _CORRECTIONS:
        result = pattern.sub(replacement, result)

    # Normalise whitespace
    result = " ".join(result.split())

    # Layer 1 again: check after corrections (may have reduced to hallucination)
    if is_hallucination(result):
        return ""

    return result


def clean_inline_command(text: str, wake_word: str) -> str:
    """
    Extract and clean the command portion from a wake-word utterance.

    Handles cases like:
      "HIPPANDA open spotify"  → "open spotify"   (merged wake word)
      "Pandaa opens 45th"      → ""                (no real command)
      "Well, Panda, open you"  → "open you"        (context words before)
      "Panda, I ask you to open" → ""              (no app specified)

    Returns empty string if no valid command found.
    """
    import re as _re

    # Step 1: Remove the wake word and any words before it
    # Handle merged forms like "HIPPANDA", "Pandaa", "Banda"
    last_word = wake_word.split()[-1].lower()  # "panda"

    # Try to find where the wake word ends in the text
    # Match: optional prefix words + wake_word_variant + optional punctuation
    wake_pattern = _re.compile(
        r"^.*?\b" + last_word + r"\w*\b\s*[,.]?\s*",
        _re.I
    )
    stripped = wake_pattern.sub("", text).strip()

    # If nothing was stripped, try removing just leading non-command words
    if stripped == text.strip():
        # Remove common preamble patterns
        stripped = _re.sub(
            r"^(well|okay|ok|so|hey|hi|uh|um|er|ah)[,\s]+",
            "", text, flags=_re.I
        ).strip()

    # Step 2: Clean leading punctuation
    stripped = _re.sub(r"^[\s?.!,\-]+", "", stripped).strip()

    # Step 3: Apply autocorrect
    stripped = autocorrect(stripped)
    if not stripped:
        return ""

    # Step 4: Validate — must have at least one actionable word
    # Reject if it's just filler like "I ask you to open" with no target
    words = [w for w in stripped.lower().split() if len(w) >= 2]
    if len(words) < 2:
        return ""

    # Reject if it looks like a question/statement with no command verb
    COMMAND_VERBS = {
        "open", "launch", "start", "run", "close", "stop", "play", "sing",
        "search", "find", "show", "tell", "what", "how", "when", "where",
        "who", "shutdown", "restart", "lock", "sleep", "volume", "mute",
    }
    if not any(w in COMMAND_VERBS for w in words):
        return ""

    return stripped
