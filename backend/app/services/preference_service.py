from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import UserPreference
from app.schemas.preference import UserPreferenceResponse

logger = get_logger("services.preference")

DEFAULT_PROFILE_KEY = "default"


@dataclass(frozen=True)
class PreferenceLearningResult:
    profile: UserPreference
    updates: list[str]


def get_or_create_user_preferences(*, db: Session, user_id: str | None = None) -> UserPreference:
    profile_key = _profile_key(user_id)
    profile = db.scalar(select(UserPreference).where(UserPreference.profile_key == profile_key))
    if profile is not None:
        return profile

    profile = UserPreference(
        user_id=user_id,
        profile_key=profile_key,
        evidence_strictness="balanced",
        challenge_style="balanced",
        topics_of_interest=[],
        source_preferences={},
        metadata_json={"created_by": "preference_service"},
    )
    db.add(profile)
    db.flush()
    logger.info("\U0001f9ed preference.profile.created profile_key=%s", profile_key)
    return profile


def preference_response(profile: UserPreference) -> UserPreferenceResponse:
    return UserPreferenceResponse(
        id=profile.id,
        user_id=profile.user_id,
        preferred_review_time=profile.preferred_review_time,
        recall_frequency=profile.recall_frequency,
        answer_style=profile.answer_style,
        evidence_strictness=profile.evidence_strictness or "balanced",
        challenge_style=profile.challenge_style or "balanced",
        memory_density=profile.memory_density,
        notification_preference=profile.notification_preference,
        topics_of_interest=list(profile.topics_of_interest or []),
        source_preferences=dict(profile.source_preferences or {}),
        updated_from_message_id=profile.updated_from_message_id,
        updated_at=profile.updated_at.isoformat(),
    )


def learn_preferences_from_message(
    *,
    db: Session,
    message: str,
    message_id: str | None,
    user_id: str | None = None,
) -> PreferenceLearningResult:
    profile = get_or_create_user_preferences(db=db, user_id=user_id)
    updates = _extract_preference_updates(message)
    if not updates:
        return PreferenceLearningResult(profile=profile, updates=[])

    labels: list[str] = []
    source_preferences = dict(profile.source_preferences or {})
    topics = list(profile.topics_of_interest or [])

    for field_name, value, label in updates:
        if field_name == "topics_of_interest":
            for topic in value:
                if topic not in topics:
                    topics.append(topic)
            topics = topics[:20]
            labels.append(label)
            continue

        if field_name == "source_preferences":
            source_preferences = _merge_source_preferences(source_preferences, value)
            labels.append(label)
            continue

        setattr(profile, field_name, value)
        labels.append(label)

    profile.topics_of_interest = topics
    profile.source_preferences = source_preferences
    profile.updated_from_message_id = message_id
    existing_meta = dict(profile.metadata_json or {})
    profile.metadata_json = {
        **existing_meta,
        "last_detected_preferences": labels,
    }
    db.flush()
    logger.info("\U0001f9ed preference.learned updates=%s profile_key=%s", len(labels), profile.profile_key)
    return PreferenceLearningResult(profile=profile, updates=labels)


def format_preference_context(profile: UserPreference | None) -> str:
    if profile is None:
        return "No explicit user preferences have been learned yet."

    parts: list[str] = []
    if profile.answer_style:
        parts.append(f"Answer style: {profile.answer_style}.")
    if profile.evidence_strictness and profile.evidence_strictness != "balanced":
        parts.append(f"Evidence strictness: {profile.evidence_strictness}.")
    if profile.challenge_style and profile.challenge_style != "balanced":
        parts.append(f"Challenge style: {profile.challenge_style}.")
    if profile.memory_density:
        parts.append(f"Memory density preference: {profile.memory_density}.")
    if profile.preferred_review_time:
        parts.append(f"Preferred review time: {profile.preferred_review_time}.")
    if profile.recall_frequency:
        parts.append(f"Recall frequency preference: {profile.recall_frequency}.")
    if profile.notification_preference:
        parts.append(f"Notification preference: {profile.notification_preference}.")
    topics = list(profile.topics_of_interest or [])
    if topics:
        parts.append(f"Topics the user explicitly cares about: {', '.join(topics[:10])}.")
    source_preferences = dict(profile.source_preferences or {})
    if source_preferences:
        parts.append(f"Source preferences: {source_preferences}.")

    if not parts:
        return "No explicit user preferences have been learned yet."
    return "\n".join(parts)


def is_explicit_preference_statement(message: str) -> bool:
    return bool(_extract_preference_updates(message))


def _extract_preference_updates(message: str) -> list[tuple[str, object, str]]:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    if not normalized:
        return []

    has_preference_marker = any(
        marker in normalized
        for marker in (
            "i prefer",
            "i like",
            "i want",
            "i need",
            "please",
            "don't",
            "dont",
            "do not",
            "remind me",
            "review",
            "recall",
            "challenge me",
            "push back",
            "call me out",
            "i care",
            "i'm focusing",
            "i am focusing",
            "my main topics",
            "i'm interested",
            "i am interested",
        )
    )
    if not has_preference_marker:
        return []

    updates: list[tuple[str, object, str]] = []

    if _has_any(normalized, ("short answers", "brief answers", "concise answers", "straight to the point")):
        updates.append(("answer_style", "concise", "Answer style: concise"))
    elif _has_any(normalized, ("detailed answers", "deep answers", "in-depth", "thorough", "explain deeply")):
        updates.append(("answer_style", "detailed", "Answer style: detailed"))
    elif "balanced answers" in normalized:
        updates.append(("answer_style", "balanced", "Answer style: balanced"))

    if _has_any(
        normalized,
        (
            "evidence-heavy",
            "evidence heavy",
            "strong evidence",
            "verify claims",
            "fact-check",
            "fact check",
            "don't let me believe false",
            "dont let me believe false",
            "source-backed",
            "source backed",
            "public evidence",
            "before accepting claims",
            "unless there is evidence",
            "unless it has evidence",
            "without evidence",
        ),
    ):
        updates.append(("evidence_strictness", "strict", "Evidence strictness: strict"))
    elif _has_any(normalized, ("less evidence", "not too much evidence", "lighter evidence")):
        updates.append(("evidence_strictness", "relaxed", "Evidence strictness: relaxed"))

    if _has_any(
        normalized,
        ("challenge me", "challenge my assumptions", "push back", "call me out", "be direct", "debate me"),
    ):
        updates.append(("challenge_style", "direct", "Challenge style: direct"))
    elif _has_any(normalized, ("be gentle", "gentle coaching", "don't be harsh", "dont be harsh", "less direct")):
        updates.append(("challenge_style", "gentle", "Challenge style: gentle"))

    if _has_any(normalized, ("fewer memory cards", "less memory cards", "less cards", "don't split too much", "dont split too much")):
        updates.append(("memory_density", "compact", "Memory density: compact"))
    elif _has_any(normalized, ("more atomic", "split more", "more memory cards", "detailed memory cards")):
        updates.append(("memory_density", "rich", "Memory density: rich"))

    review_time = _review_time(normalized)
    if review_time is not None:
        updates.append(("preferred_review_time", review_time, f"Preferred review time: {review_time}"))

    recall_frequency = _recall_frequency(normalized)
    if recall_frequency is not None:
        updates.append(("recall_frequency", recall_frequency, f"Recall frequency: {recall_frequency}"))

    notification_preference = _notification_preference(normalized)
    if notification_preference is not None:
        updates.append(
            (
                "notification_preference",
                notification_preference,
                f"Notification preference: {notification_preference}",
            )
        )

    topics = _topics_of_interest(normalized)
    if topics:
        updates.append(("topics_of_interest", topics, f"Topics of interest: {', '.join(topics[:6])}"))

    source_preferences = _source_preferences(normalized)
    if source_preferences:
        updates.append(("source_preferences", source_preferences, "Source preferences updated"))

    return _dedupe_updates(updates)


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _review_time(normalized: str) -> str | None:
    if "morning" in normalized and _has_any(normalized, ("review", "recall", "remind")):
        return "morning"
    if "afternoon" in normalized and _has_any(normalized, ("review", "recall", "remind")):
        return "afternoon"
    if "evening" in normalized and _has_any(normalized, ("review", "recall", "remind")):
        return "evening"
    if "night" in normalized and _has_any(normalized, ("review", "recall", "remind")):
        return "night"
    return None


def _recall_frequency(normalized: str) -> str | None:
    if _has_any(normalized, ("daily recall", "recall daily", "every day", "each day")):
        return "daily"
    if _has_any(normalized, ("weekly recall", "recall weekly", "once a week")):
        return "weekly"
    if _has_any(normalized, ("less often", "not too often", "less recall")):
        return "low"
    if _has_any(normalized, ("more often", "more recall", "recall me more")):
        return "high"
    return None


def _notification_preference(normalized: str) -> str | None:
    if _has_any(normalized, ("don't notify me", "dont notify me", "do not notify me")):
        return "none"
    if "in-app only" in normalized or "inside the app" in normalized:
        return "in_app_only"
    if "push notification" in normalized or "push notifications" in normalized:
        return "push"
    if "email me" in normalized or "email notification" in normalized:
        return "email"
    return None


def _topics_of_interest(normalized: str) -> list[str]:
    patterns = (
        r"\bi care mostly about ([^.?!]+)",
        r"\bi care about ([^.?!]+)",
        r"\bmy main topics are ([^.?!]+)",
        r"\bi(?:'m| am) focusing on ([^.?!]+)",
        r"\bi(?:'m| am) interested in ([^.?!]+)",
    )
    topics: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        raw = match.group(1)
        raw = re.sub(r"\b(and stuff|right now|for now|mostly)\b", "", raw).strip()
        for topic in re.split(r",|/|\band\b", raw):
            cleaned = _clean_topic(topic)
            if cleaned and cleaned not in topics:
                topics.append(cleaned)
    return topics[:10]


def _source_preferences(normalized: str) -> dict[str, object]:
    preferences: dict[str, object] = {}
    preferred_sources: list[str] = []
    avoided_sources: list[str] = []

    for label, markers in {
        "research_papers": ("research papers", "papers", "studies"),
        "books": ("books", "book excerpts"),
        "articles": ("articles", "blogs"),
        "youtube": ("youtube", "videos"),
        "podcasts": ("podcasts",),
    }.items():
        if any(f"prefer {marker}" in normalized or f"trust {marker}" in normalized for marker in markers):
            preferred_sources.append(label)
        if any(
            f"don't show me weak {marker}" in normalized
            or f"dont show me weak {marker}" in normalized
            or f"avoid {marker}" in normalized
            for marker in markers
        ):
            avoided_sources.append(label)

    if preferred_sources:
        preferences["prefer"] = preferred_sources
    if avoided_sources:
        preferences["avoid_weak"] = avoided_sources
    if avoided_sources and _has_any(normalized, ("unless there is evidence", "unless it has evidence", "without evidence")):
        preferences["rule"] = "avoid weak sources unless corroborated by stronger evidence"

    return preferences


def _merge_source_preferences(existing: dict[str, object], incoming: dict[str, object]) -> dict[str, object]:
    merged = dict(existing)
    for key, value in incoming.items():
        if isinstance(value, list):
            existing_values = list(merged.get(key) or [])
            for item in value:
                if item not in existing_values:
                    existing_values.append(item)
            merged[key] = existing_values
        else:
            merged[key] = value
    return merged


def _clean_topic(topic: str) -> str:
    cleaned = re.sub(r"[^a-z0-9 +#.-]", " ", topic.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-")
    stop_tails = ("and product", "and learning", "and business")
    return cleaned[:80]


def _dedupe_updates(updates: list[tuple[str, object, str]]) -> list[tuple[str, object, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, object, str]] = []
    for field_name, value, label in updates:
        key = (field_name, str(value))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((field_name, value, label))
    return deduped


def _profile_key(user_id: str | None) -> str:
    return user_id or DEFAULT_PROFILE_KEY
