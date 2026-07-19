from __future__ import annotations

import re
from dataclasses import dataclass


class CaptureSafetyError(ValueError):
    """Raised when content is too sensitive or unsafe to store as memory."""


@dataclass(frozen=True)
class CaptureSafetyResult:
    safe_text: str
    redactions: list[str]


_SECRET_RE = re.compile(
    r"(?im)\b("
    r"password|passwd|pwd|api[_ -]?key|secret|client[_ -]?secret|"
    r"access[_ -]?token|auth[_ -]?token|refresh[_ -]?token|bearer\s+token|"
    r"private[_ -]?key"
    r")\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=:@-]{8,}"
)
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_FINANCIAL_ACCOUNT_RE = re.compile(
    r"(?im)\b(bank account|account number|routing number|iban|swift|sort code)\b"
    r"\s*[:#-]?\s*[A-Z0-9 -]{6,}"
)
_PERSONAL_MEDICAL_RE = re.compile(
    r"(?im)\b("
    r"patient name|medical record|mrn|date of birth|dob|diagnosis\s*:|"
    r"prescription for|lab result|test result for|hiv status"
    r")\b"
)
_HARMFUL_INSTRUCTION_RE = re.compile(
    r"(?im)\b("
    r"how to make a bomb|build a bomb|make malware|write malware|steal passwords|"
    r"carding|credit card dump|bypass authentication|phishing kit"
    r")\b"
)

_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_GOV_ID_RE = re.compile(
    r"(?im)\b("
    r"ssn|social security|nin|bvn|passport(?:\s+number)?|national id|"
    r"driver'?s license"
    r")\b\s*(?:number|no\.?|id)?\s*[:#-]?\s*[A-Z0-9-]{5,}"
)
_ADDRESS_LABEL_RE = re.compile(r"(?im)\b(home address|residential address)\b\s*[:#-]?\s*[^\n]{8,}")


def guard_capture_content(text: str) -> CaptureSafetyResult:
    """Reject secrets/high-risk private data and mask contact identifiers.

    This is intentionally deterministic. It is not a full moderation system,
    but it catches the kinds of accidental sensitive pastes that would be most
    damaging to persist, embed, and surface later.
    """

    if _SECRET_RE.search(text) or _PRIVATE_KEY_RE.search(text):
        raise CaptureSafetyError(
            "This looks like it contains passwords, API keys, tokens, or private keys. "
            "I did not save it. Remove the secret first, then try again."
        )

    if _contains_credit_card_number(text) or _FINANCIAL_ACCOUNT_RE.search(text):
        raise CaptureSafetyError(
            "This looks like it contains credit card or financial account details. "
            "I did not save it because Crowscap is for ideas and learning, not sensitive account data."
        )

    if _PERSONAL_MEDICAL_RE.search(text):
        raise CaptureSafetyError(
            "This looks like it contains private patient or medical-record details. "
            "I did not save it. Public health research is fine, but private medical identifiers should stay out of memory."
        )

    if _HARMFUL_INSTRUCTION_RE.search(text):
        raise CaptureSafetyError(
            "This looks like operational harmful or illegal material. I did not save it."
        )

    return _mask_personal_identifiers(text)


def _mask_personal_identifiers(text: str) -> CaptureSafetyResult:
    redactions: set[str] = set()

    def replace_email(_: re.Match[str]) -> str:
        redactions.add("email")
        return "[email]"

    def replace_phone(match: re.Match[str]) -> str:
        value = match.group(0)
        digits = re.sub(r"\D", "", value)
        if not 10 <= len(digits) <= 15:
            return value
        if _looks_like_date_or_range(value):
            return value
        redactions.add("phone number")
        return "[phone number]"

    def replace_gov_id(_: re.Match[str]) -> str:
        redactions.add("government id")
        return "[government id]"

    def replace_address(_: re.Match[str]) -> str:
        redactions.add("address")
        return "[address]"

    safe = _EMAIL_RE.sub(replace_email, text)
    safe = _PHONE_RE.sub(replace_phone, safe)
    safe = _GOV_ID_RE.sub(replace_gov_id, safe)
    safe = _ADDRESS_LABEL_RE.sub(replace_address, safe)

    return CaptureSafetyResult(safe_text=safe, redactions=sorted(redactions))


def _contains_credit_card_number(text: str) -> bool:
    for match in re.finditer(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text):
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19 and _passes_luhn(digits):
            return True
    return False


def _passes_luhn(digits: str) -> bool:
    total = 0
    reverse_digits = [int(char) for char in reversed(digits)]
    for index, digit in enumerate(reverse_digits):
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _looks_like_date_or_range(value: str) -> bool:
    compact = value.strip()
    return bool(
        re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", compact)
        or re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", compact)
        or re.fullmatch(r"\d{4}\s*-\s*\d{4}", compact)
    )
