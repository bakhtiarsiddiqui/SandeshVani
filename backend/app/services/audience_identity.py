from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from app.models.audience_member import AudienceMember

EMAIL_IDENTITY_INDEX = "uq_audience_members_org_email_identity"
PHONE_IDENTITY_INDEX = "uq_audience_members_org_phone_identity"


def classify_identity_match(
    matches: Sequence[AudienceMember],
    *,
    email: str | None,
    phone: str | None,
) -> dict[str, str | None] | None:
    """Classify exact tenant-scoped identity matches without exposing PII."""
    normalized_email = email.strip().lower() if email else None
    normalized_phone = phone.strip() if phone else None

    email_matches = [
        member
        for member in matches
        if normalized_email
        and member.email
        and member.email.strip().lower() == normalized_email
    ]
    phone_matches = [
        member
        for member in matches
        if normalized_phone
        and member.phone
        and member.phone.strip() == normalized_phone
    ]

    if len(email_matches) > 1 or len(phone_matches) > 1:
        return {"field_name": None, "error_code": "IDENTITY_CONFLICT"}

    email_match = email_matches[0] if email_matches else None
    phone_match = phone_matches[0] if phone_matches else None
    if email_match is not None and phone_match is not None:
        if email_match.id == phone_match.id:
            return {"field_name": None, "error_code": "DUPLICATE_CONTACT"}
        return {"field_name": None, "error_code": "IDENTITY_CONFLICT"}
    if email_match is not None:
        return {"field_name": "email", "error_code": "DUPLICATE_EMAIL"}
    if phone_match is not None:
        return {"field_name": "phone", "error_code": "DUPLICATE_PHONE"}
    return None


def is_identity_unique_violation(error: IntegrityError) -> bool:
    """Recognize only the two identity indexes; re-raise other integrity errors."""
    original = error.orig
    constraint_name = getattr(getattr(original, "diag", None), "constraint_name", None)
    if constraint_name in {EMAIL_IDENTITY_INDEX, PHONE_IDENTITY_INDEX}:
        return True
    message = str(original)
    return EMAIL_IDENTITY_INDEX in message or PHONE_IDENTITY_INDEX in message
