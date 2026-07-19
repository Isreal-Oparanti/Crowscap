import pytest

from app.services.safety_service import CaptureSafetyError, guard_capture_content


def test_guard_capture_content_rejects_luhn_credit_card_number() -> None:
    with pytest.raises(CaptureSafetyError) as exc:
        guard_capture_content(
            "Save this billing note with card 4242 4242 4242 4242 for later reference."
        )

    assert "credit card" in str(exc.value)


def test_guard_capture_content_allows_public_health_research_language() -> None:
    result = guard_capture_content(
        "This public health article studies malaria surveillance trends and case reporting quality."
    )

    assert result.safe_text.startswith("This public health article")
    assert result.redactions == []


def test_guard_capture_content_rejects_private_medical_record_details() -> None:
    with pytest.raises(CaptureSafetyError) as exc:
        guard_capture_content(
            "Patient name: Ada Lovelace\nDOB: 1991-04-10\nDiagnosis: malaria with complications"
        )

    assert "private patient" in str(exc.value)


def test_guard_capture_content_masks_email_phone_and_government_id() -> None:
    result = guard_capture_content(
        "Contact ada@example.com or +234 801 234 5678. Passport number A1234567."
    )

    assert result.safe_text == "Contact [email] or [phone number]. [government id]."
    assert result.redactions == ["email", "government id", "phone number"]
