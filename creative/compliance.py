"""Illustrative ad-compliance checks. Real programs need legal review against each platform's current policy."""
import re

CLAIMS = [r"\bcure[sd]?\b", r"\bguarantee[sd]?\b", r"\bmiracle\b", r"\bfda[- ]approved\b", r"\brisk[- ]free\b",
          r"\btreat(s|ed|ing|ment)?\b", r"\bprevent(s|ed|ing)?\b", r"\bclinically proven\b",
          r"\bbefore and after\b", r"\bbefore/after\b", r"\blose \d+ ?(lbs|pounds)\b"]
IMAGE_AVOID = [r"\bbefore and after\b", r"\bbefore/after\b", r"\bpills?\b", r"\bsyringe\b", r"\bweight scale\b",
               r"\bcelebrity\b", r"\blogo\b", r"\bwatermark\b"]


def _hits(patterns: list[str], text: str) -> list[str]:
    low = text.lower()
    return [m.group(0) for p in patterns if (m := re.search(p, low))]


def check_copy(text: str) -> list[str]:
    return [f"prohibited claim: '{h}'" for h in _hits(CLAIMS, text)]


def check_image_prompt(text: str) -> list[str]:
    return [f"avoid in imagery: '{h}'" for h in _hits(IMAGE_AVOID, text)]
