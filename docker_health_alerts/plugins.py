from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

DeliveryStatus = Literal["success", "retryable_failure", "permanent_failure"]


@dataclass(frozen=True)
class DeliveryResult:
    status: DeliveryStatus
    message: str = ""
    retry_after_seconds: float | None = None

    @classmethod
    def success(cls, message: str = "delivered") -> DeliveryResult:
        return cls(status="success", message=message)

    @classmethod
    def retryable_failure(cls, message: str = "") -> DeliveryResult:
        return cls(status="retryable_failure", message=message)

    @classmethod
    def permanent_failure(cls, message: str = "") -> DeliveryResult:
        return cls(status="permanent_failure", message=message)


class Receiver(Protocol):
    name: str

    def deliver(self, alert: Mapping[str, Any]) -> DeliveryResult: ...
