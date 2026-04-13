"""
Windows Application Discovery Module

Implements Stage 2 & 3 of the architectural remediation:
- Scans Windows Registry (HKLM/HKCU Uninstall keys) to build an app manifest
- Phonetic matching using Double Metaphone algorithm for brand-name repair
  (e.g. "what's up" → "WhatsApp", "spot if i" → "Spotify")
- Fuzzy entity resolution using token_sort_ratio (RapidFuzz if available,
  else falls back to built-in difflib)
- Registry-aware path resolution via App Paths key

References:
  - Paper: "Phonetic Algorithm Taxonomy" — Double Metaphone for OOV repair
  - Paper: "Leveraging the Windows Registry for App Resolution"
    HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths
    HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall
"""

import logging
import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("panda.app_discovery")

# ── Double Metaphone (pure Python, no dependencies) ──────────────────────────
# Simplified implementation covering the most common English phoneme rules.

_VOWELS = set("AEIOU")

def _double_metaphone(word: str) -> Tuple[str, str]:
    """
    Compute primary and secondary Double Metaphone codes for a word.
    Returns (primary, secondary) — secondary may equal primary.
    """
    word = word.upper().strip()
    if not word:
        return ("", "")

    # Remove non-alpha
    word = re.sub(r"[^A-Z]", "", word)
    if not word:
        return ("", "")

    primary = []
    secondary = []
    i = 0
    length = len(word)

    def add(p: str, s: str = "") -> None:
        primary.append(p)
        secondary.append(s if s else p)

    def at(pos: int, *chars: str) -> bool:
        if pos < 0 or pos >= length:
            return False
        return word[pos] in chars

    def substr(pos: int, n: int) -> str:
        return word[pos:pos+n]

    # Handle initial silent letters
    if substr(0, 2) in ("AE", "GN", "KN", "PN", "WR"):
        i = 1

    # Initial vowel → A
    if word[0] in _VOWELS:
        add("A")
        i = 1

    while i < length:
        c = word[i]

        if c in _VOWELS:
            if i == 0:
                add("A")
            i += 1
            continue

        if c == "B":
            add("P")
            i += 2 if at(i+1, "B") else 1
        elif c == "C":
            if substr(i, 4) in ("CHIA",):
                add("K")
                i += 2
            elif substr(i, 2) == "CH":
                add("X", "K")
                i += 2
            elif at(i+1, "I", "E", "Y"):
                add("S")
                i += 2
            else:
                add("K")
                i += 1
        elif c == "D":
            if substr(i, 2) == "DG" and at(i+2, "I", "E", "Y"):
                add("J")
                i += 3
            elif substr(i, 2) in ("DT", "DD"):
                add("T")
                i += 2
            else:
                add("T")
                i += 1
        elif c == "F":
            add("F")
            i += 2 if at(i+1, "F") else 1
        elif c == "G":
            if at(i+1, "H"):
                if i > 0 and word[i-1] not in _VOWELS:
                    add("K")
                    i += 2
                else:
                    i += 2
            elif at(i+1, "N"):
                i += 1
            elif at(i+1, "I", "E", "Y"):
                add("K", "J")
                i += 2
            else:
                add("K")
                i += 1
        elif c == "H":
            if word[i-1] not in _VOWELS if i > 0 else True:
                if at(i+1, *_VOWELS):
                    add("H")
            i += 1
        elif c == "J":
            add("J")
            i += 1
        elif c == "K":
            if at(i+1, "K"):
                i += 2
            else:
                add("K")
                i += 1
        elif c == "L":
            add("L")
            i += 2 if at(i+1, "L") else 1
        elif c == "M":
            add("M")
            i += 2 if at(i+1, "M") else 1
        elif c == "N":
            add("N")
            i += 2 if at(i+1, "N") else 1
        elif c == "P":
            if at(i+1, "H"):
                add("F")
                i += 2
            else:
                add("P")
                i += 2 if at(i+1, "P") else 1
        elif c == "Q":
            add("K")
            i += 2 if at(i+1, "Q") else 1
        elif c == "R":
            add("R")
            i += 2 if at(i+1, "R") else 1
        elif c == "S":
            if substr(i, 2) == "SH" or substr(i, 3) in ("SIO", "SIA"):
                add("X")
                i += 2
            elif substr(i, 2) == "SC":
                if at(i+2, "H"):
                    add("SK")
                    i += 3
                elif at(i+2, "I", "E", "Y"):
                    add("S")
                    i += 3
                else:
                    add("SK")
                    i += 3
            else:
                add("S")
                i += 2 if at(i+1, "S", "Z") else 1
        elif c == "T":
            if substr(i, 2) == "TH":
                add("0", "T")
                i += 2
            elif substr(i, 3) in ("TIA", "TCH"):
                add("X")
                i += 3
            else:
                add("T")
                i += 2 if at(i+1, "T", "D") else 1
        elif c == "V":
            add("F")
            i += 2 if at(i+1, "V") else 1
        elif c == "W":
            if at(i+1, *_VOWELS):
                add("A")
            i += 1
        elif c == "X":
            add("S")
            i += 1
        elif c == "Y":
            if at(i+1, *_VOWELS):
                add("Y")
            i += 1
        elif c == "Z":
            add("S")
            i += 2 if at(i+1, "Z") else 1
        else:
            i += 1

    p = "".join(primary)[:6]
    s = "".join(secondary)[:6]
    return (p, s if s != p else p)


def _metaphone_distance(a: str, b: str) -> float:
    """
    Phonetic similarity score 0.0–1.0 using Double Metaphone.
    1.0 = identical codes, 0.0 = completely different.
    """
    pa, sa = _double_metaphone(a)
    pb, sb = _double_metaphone(b)
    best = 0.0
    for ca in (pa, sa):
        for cb in (pb, sb):
            if not ca or not cb:
                continue
            # Longest common prefix ratio
            common = sum(1 for x, y in zip(ca, cb) if x == y)
            ratio = common / max(len(ca), len(cb))
            best = max(best, ratio)
    return best


# ── Fuzzy string matching ─────────────────────────────────────────────────────

def _fuzzy_ratio(a: str, b: str) -> float:
    """Token-sort ratio, 0.0–1.0. Uses RapidFuzz if available."""
    try:
        from rapidfuzz import fuzz
        return fuzz.token_sort_ratio(a, b) / 100.0
    except ImportError:
        pass
    # Fallback: difflib SequenceMatcher
    from difflib import SequenceMatcher
    a_sorted = " ".join(sorted(a.lower().split()))
    b_sorted = " ".join(sorted(b.lower().split()))
    return SequenceMatcher(None, a_sorted, b_sorted).ratio()


# ── Windows Registry app manifest ────────────────────────────────────────────

class AppManifest:
    """
    Builds and queries a local manifest of installed Windows applications
    by scanning the Windows Registry Uninstall keys.

    Also resolves app names to executable paths via the App Paths key.
    """

    UNINSTALL_KEYS = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    APP_PATHS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"

    def __init__(self):
        self._apps: Dict[str, str] = {}        # display_name_lower → display_name
        self._paths: Dict[str, str] = {}       # display_name_lower → exe_path
        self._metaphone_cache: Dict[str, Tuple[str, str]] = {}
        self._built = False

    def build(self) -> int:
        """
        Scan the registry and populate the manifest.
        Returns the number of apps found.
        """
        self._apps.clear()
        self._paths.clear()

        try:
            import winreg
        except ImportError:
            log.warning("winreg not available — app discovery disabled (non-Windows?)")
            return 0

        hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]

        for hive in hives:
            for key_path in self.UNINSTALL_KEYS:
                try:
                    key = winreg.OpenKey(hive, key_path)
                    i = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(key, i)
                            sub_key  = winreg.OpenKey(key, sub_name)
                            try:
                                name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                                if name and isinstance(name, str) and len(name) > 1:
                                    lower = name.lower().strip()
                                    self._apps[lower] = name
                                    # Try to get install location
                                    try:
                                        loc, _ = winreg.QueryValueEx(sub_key, "InstallLocation")
                                        if loc:
                                            self._paths[lower] = loc
                                    except OSError:
                                        pass
                            except OSError:
                                pass
                            finally:
                                winreg.CloseKey(sub_key)
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except OSError:
                    pass

        # Also scan App Paths for direct exe mappings
        for hive in hives:
            try:
                key = winreg.OpenKey(hive, self.APP_PATHS_KEY)
                i = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(key, i)
                        sub_key  = winreg.OpenKey(key, sub_name)
                        try:
                            exe_path, _ = winreg.QueryValueEx(sub_key, "")
                            app_name = os.path.splitext(sub_name)[0].lower()
                            if app_name and exe_path:
                                self._apps.setdefault(app_name, sub_name)
                                self._paths[app_name] = exe_path
                        except OSError:
                            pass
                        finally:
                            winreg.CloseKey(sub_key)
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except OSError:
                pass

        self._built = True
        log.info(f"App manifest built: {len(self._apps)} applications found")
        return len(self._apps)

    def resolve(self, query: str, threshold: float = 0.72) -> Optional[str]:
        """
        Resolve a (possibly mis-transcribed) app name to the best matching
        installed application name.

        Uses a hybrid score:
          score = 0.6 * fuzzy_ratio + 0.4 * metaphone_similarity

        Returns the canonical DisplayName if score >= threshold, else None.
        """
        if not self._built:
            self.build()

        if not self._apps:
            return None

        query_lower = query.lower().strip()
        best_score  = 0.0
        best_name   = None

        for lower, display in self._apps.items():
            fuzzy = _fuzzy_ratio(query_lower, lower)
            phon  = _metaphone_distance(query_lower, lower)
            score = 0.6 * fuzzy + 0.4 * phon
            if score > best_score:
                best_score = score
                best_name  = display

        if best_score >= threshold:
            log.info(f"App resolved: '{query}' → '{best_name}' (score={best_score:.2f})")
            return best_name
        return None

    def get_exe_path(self, display_name: str) -> Optional[str]:
        """Return the executable path for a resolved display name, if known."""
        return self._paths.get(display_name.lower().strip())

    def get_whisper_prompt(self, top_n: int = 50) -> str:
        """
        Return a comma-separated list of the top N app names for use as
        a Whisper initial_prompt (contextual biasing).
        """
        names = list(self._apps.values())[:top_n]
        return ", ".join(names)

    @property
    def app_count(self) -> int:
        return len(self._apps)


# Singleton — built once at startup
_manifest: Optional[AppManifest] = None


def get_manifest() -> AppManifest:
    global _manifest
    if _manifest is None:
        _manifest = AppManifest()
        _manifest.build()
    return _manifest


def repair_app_name(transcribed: str) -> str:
    """
    Attempt to repair a mis-transcribed application name using the
    Windows app manifest + phonetic matching.

    Returns the corrected name if a high-confidence match is found,
    otherwise returns the original string unchanged.
    """
    manifest = get_manifest()
    resolved = manifest.resolve(transcribed)
    if resolved:
        return resolved
    return transcribed
