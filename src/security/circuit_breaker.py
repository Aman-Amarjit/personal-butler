"""
Circuit Breaker for Recursive Loops

Detects and prevents recursive loops and infinite iterations.
"""

import logging
from typing import Optional, Callable, Dict, Any
from enum import Enum


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Broken, rejecting calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Detects and prevents recursive loops.
    
    Features:
    - Recursion depth tracking (max 10)
    - Iteration counting (max 100)
    - Circuit breaker state management
    - User notification on circuit break
    - Circuit reset functionality
    """

    def __init__(
        self,
        max_recursion_depth: int = 10,
        max_iterations: int = 100
    ):
        """
        Initialize circuit breaker.

        Args:
            max_recursion_depth: Maximum recursion depth
            max_iterations: Maximum iterations allowed
        """
        self.max_recursion_depth = max_recursion_depth
        self.max_iterations = max_iterations

        self.state = CircuitState.CLOSED
        self.recursion_depth = 0
        self.iteration_count = 0
        self.break_reason: Optional[str] = None

        self.on_circuit_break: Optional[Callable] = None
        self.on_circuit_reset: Optional[Callable] = None

        logger.info(
            f"Circuit breaker initialized: "
            f"max_depth={max_recursion_depth}, "
            f"max_iterations={max_iterations}"
        )

    def enter_recursion(self) -> bool:
        """
        Enter a recursive call.

        Returns:
            True if allowed, False if circuit broken
        """
        if self.state == CircuitState.OPEN:
            logger.warning("Circuit is OPEN, rejecting recursion")
            return False

        self.recursion_depth += 1

        if self.recursion_depth > self.max_recursion_depth:
            self._break_circuit(
                f"Max recursion depth exceeded: {self.recursion_depth}"
            )
            return False

        logger.debug(f"Recursion depth: {self.recursion_depth}")
        return True

    def exit_recursion(self) -> None:
        """Exit a recursive call"""
        if self.recursion_depth > 0:
            self.recursion_depth -= 1
            logger.debug(f"Recursion depth: {self.recursion_depth}")

    def increment_iteration(self) -> bool:
        """
        Increment iteration counter.

        Returns:
            True if allowed, False if circuit broken
        """
        if self.state == CircuitState.OPEN:
            logger.warning("Circuit is OPEN, rejecting iteration")
            return False

        self.iteration_count += 1

        if self.iteration_count > self.max_iterations:
            self._break_circuit(
                f"Max iterations exceeded: {self.iteration_count}"
            )
            return False

        if self.iteration_count % 10 == 0:
            logger.debug(f"Iteration count: {self.iteration_count}")

        return True

    def reset_iteration_count(self) -> None:
        """Reset iteration counter"""
        self.iteration_count = 0
        logger.debug("Iteration count reset")

    def _break_circuit(self, reason: str) -> None:
        """
        Break the circuit.

        Args:
            reason: Reason for breaking
        """
        self.state = CircuitState.OPEN
        self.break_reason = reason

        logger.error(f"Circuit BROKEN: {reason}")

        if self.on_circuit_break:
            try:
                self.on_circuit_break(reason)
            except Exception as e:
                logger.error(f"Error in circuit break callback: {e}")

    def reset_circuit(self) -> None:
        """Reset the circuit"""
        self.state = CircuitState.CLOSED
        self.recursion_depth = 0
        self.iteration_count = 0
        self.break_reason = None

        logger.info("Circuit RESET to CLOSED state")

        if self.on_circuit_reset:
            try:
                self.on_circuit_reset()
            except Exception as e:
                logger.error(f"Error in circuit reset callback: {e}")

    def is_circuit_open(self) -> bool:
        """Check if circuit is open"""
        return self.state == CircuitState.OPEN

    def is_circuit_closed(self) -> bool:
        """Check if circuit is closed"""
        return self.state == CircuitState.CLOSED

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self.state.value,
            "recursion_depth": self.recursion_depth,
            "max_recursion_depth": self.max_recursion_depth,
            "iteration_count": self.iteration_count,
            "max_iterations": self.max_iterations,
            "break_reason": self.break_reason,
            "recursion_percentage": (
                self.recursion_depth / self.max_recursion_depth * 100
            ),
            "iteration_percentage": (
                self.iteration_count / self.max_iterations * 100
            )
        }

    def __enter__(self):
        """Context manager entry"""
        if not self.enter_recursion():
            raise RuntimeError("Circuit breaker: recursion limit exceeded")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.exit_recursion()
        return False


class LoopProtector:
    """
    Protects against infinite loops in iterations.
    
    Usage:
        with LoopProtector(max_iterations=100) as protector:
            while condition:
                if not protector.can_continue():
                    break
                # loop body
    """

    def __init__(self, max_iterations: int = 100):
        """
        Initialize loop protector.

        Args:
            max_iterations: Maximum iterations allowed
        """
        self.circuit_breaker = CircuitBreaker(
            max_recursion_depth=1,
            max_iterations=max_iterations
        )

    def can_continue(self) -> bool:
        """
        Check if loop can continue.

        Returns:
            True if allowed, False if limit exceeded
        """
        return self.circuit_breaker.increment_iteration()

    def reset(self) -> None:
        """Reset the protector"""
        self.circuit_breaker.reset_circuit()

    def get_status(self) -> Dict[str, Any]:
        """Get protector status"""
        return self.circuit_breaker.get_status()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        return False
