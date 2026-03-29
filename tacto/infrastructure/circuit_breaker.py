"""
Circuit Breaker Pattern — Infrastructure Layer.

Prevents cascading failures by temporarily blocking requests to failing services.
Zero external dependencies — pure Python + structlog.

States:
    CLOSED  → Normal operation, requests pass through
    OPEN    → Failures exceeded threshold, requests blocked immediately
    HALF_OPEN → Recovery test, limited requests allowed

Async-safe: asyncio is single-threaded, no lock needed.
"""

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Optional

import structlog


logger = structlog.get_logger()


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker for external service calls.

    Usage:
        cb = CircuitBreaker(name="join_api")

        if cb.is_open():
            raise Exception("Circuit open — service unavailable")

        try:
            response = await external_call()
            cb.record_success()
        except Exception:
            cb.record_failure()
            raise

    Attributes:
        name: Identifier for logging
        failure_threshold: Failures before opening circuit (default: 5)
        recovery_timeout: Seconds before testing recovery (default: 30.0)
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: Optional[float] = field(default=None, init=False)
    _half_open_allowed: bool = field(default=False, init=False)

    @property
    def state(self) -> CircuitState:
        """Current circuit state (may transition to HALF_OPEN if timeout elapsed)."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    def is_open(self) -> bool:
        """
        Check if circuit is blocking requests.

        Returns True if circuit is OPEN and recovery timeout hasn't elapsed.
        In HALF_OPEN state, allows ONE test request.
        """
        current = self.state  # triggers potential HALF_OPEN transition

        if current == CircuitState.CLOSED:
            return False

        if current == CircuitState.HALF_OPEN:
            if self._half_open_allowed:
                self._half_open_allowed = False  # consume the test slot
                return False
            return True

        # OPEN
        return True

    def record_success(self) -> None:
        """Record successful request — resets failure count, closes circuit."""
        if self._state != CircuitState.CLOSED:
            logger.info(
                "circuit_breaker_closed",
                name=self.name,
                previous_state=self._state.value,
            )
        self._failure_count = 0
        self._last_failure_time = None
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record failed request — increments counter, may open circuit."""
        self._failure_count += 1
        self._last_failure_time = monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery test — reopen
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                "circuit_breaker_reopened",
                name=self.name,
                failure_count=self._failure_count,
            )
            return

        if self._failure_count >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                "circuit_breaker_opened",
                name=self.name,
                failure_count=self._failure_count,
                recovery_timeout=self.recovery_timeout,
            )

    def reset(self) -> None:
        """Manually reset circuit to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_allowed = False
        logger.info("circuit_breaker_reset", name=self.name)

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return False
        elapsed = monotonic() - self._last_failure_time
        return elapsed >= self.recovery_timeout

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state with proper initialization."""
        self._state = new_state
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_allowed = True


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and blocking requests."""

    def __init__(self, circuit_name: str) -> None:
        self.circuit_name = circuit_name
        super().__init__(f"Circuit breaker '{circuit_name}' is open — service unavailable")
