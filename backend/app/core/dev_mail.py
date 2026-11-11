from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class DevelopmentMail:
    recipient: str
    purpose: str
    body: str
    token: str | None
    expires_at: datetime


class DevelopmentMailSink:
    def __init__(self) -> None:
        self.messages: list[DevelopmentMail] = []

    def capture(
        self,
        recipient: str,
        purpose: str,
        token: str | None,
        lifetime_seconds: int,
    ) -> None:
        self._purge_expired()
        if token:
            body = f"{purpose} token: {token}"
        else:
            body = "If this address is eligible, instructions will be delivered."
        self.messages.append(
            DevelopmentMail(
                recipient=recipient.strip().lower(),
                purpose=purpose,
                body=body,
                token=token,
                expires_at=datetime.now(UTC) + timedelta(seconds=lifetime_seconds),
            )
        )

    def clear(self) -> None:
        self.messages.clear()

    def consume_latest(self, recipient: str, purpose: str) -> DevelopmentMail | None:
        self._purge_expired()
        normalized_recipient = recipient.strip().lower()
        for index in range(len(self.messages) - 1, -1, -1):
            message = self.messages[index]
            if message.recipient == normalized_recipient and message.purpose == purpose:
                return self.messages.pop(index)
        return None

    def _purge_expired(self) -> None:
        now = datetime.now(UTC)
        self.messages[:] = [
            message for message in self.messages if message.expires_at > now
        ]
