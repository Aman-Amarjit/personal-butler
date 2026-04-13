"""
Capability Gating & Trust Tiers

Manages trust-tiered access control with progressive capability unlocking.
"""

import logging
from typing import Dict, List, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class TrustLevel(Enum):
    """Trust levels"""
    UNTRUSTED = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Capability(Enum):
    """System capabilities"""
    # Basic capabilities (all levels)
    VOICE_INTERACTION = "voice_interaction"
    INFORMATION_RETRIEVAL = "information_retrieval"
    
    # Low trust (level 1+)
    APPLICATION_LAUNCH = "application_launch"
    FILE_READING = "file_reading"
    
    # Medium trust (level 2+)
    FILE_WRITING = "file_writing"
    FILE_DELETION = "file_deletion"
    SYSTEM_COMMANDS = "system_commands"
    
    # High trust (level 3)
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_RESTART = "system_restart"
    SECURITY_SETTINGS = "security_settings"


class CapabilityGate:
    """
    Manages trust-tiered access control.
    
    Features:
    - Trust level progression (0-3)
    - Operation permission checking
    - User confirmation for restricted operations
    - Trust level reset functionality
    """

    def __init__(self, initial_trust_level: TrustLevel = TrustLevel.UNTRUSTED):
        """
        Initialize capability gate.

        Args:
            initial_trust_level: Starting trust level
        """
        self.trust_level = initial_trust_level
        self.confirmed_operations: List[str] = []

        # Capability requirements
        self.capability_requirements: Dict[Capability, TrustLevel] = {
            Capability.VOICE_INTERACTION: TrustLevel.UNTRUSTED,
            Capability.INFORMATION_RETRIEVAL: TrustLevel.UNTRUSTED,
            Capability.APPLICATION_LAUNCH: TrustLevel.LOW,
            Capability.FILE_READING: TrustLevel.LOW,
            Capability.FILE_WRITING: TrustLevel.MEDIUM,
            Capability.FILE_DELETION: TrustLevel.MEDIUM,
            Capability.SYSTEM_COMMANDS: TrustLevel.MEDIUM,
            Capability.SYSTEM_SHUTDOWN: TrustLevel.HIGH,
            Capability.SYSTEM_RESTART: TrustLevel.HIGH,
            Capability.SECURITY_SETTINGS: TrustLevel.HIGH,
        }

        logger.info(f"Capability gate initialized with trust level: {initial_trust_level.name}")

    def can_execute(self, capability: Capability) -> bool:
        """
        Check if capability can be executed.

        Args:
            capability: Capability to check

        Returns:
            True if allowed, False otherwise
        """
        required_level = self.capability_requirements.get(capability)

        if required_level is None:
            logger.warning(f"Unknown capability: {capability}")
            return False

        can_execute = self.trust_level.value >= required_level.value

        if not can_execute:
            logger.warning(
                f"Capability denied: {capability.value} "
                f"(required: {required_level.name}, current: {self.trust_level.name})"
            )

        return can_execute

    def requires_confirmation(self, capability: Capability) -> bool:
        """
        Check if capability requires user confirmation.

        Args:
            capability: Capability to check

        Returns:
            True if confirmation required, False otherwise
        """
        # High trust operations always require confirmation
        if self.trust_level == TrustLevel.HIGH:
            if capability in [
                Capability.SYSTEM_SHUTDOWN,
                Capability.SYSTEM_RESTART,
                Capability.SECURITY_SETTINGS
            ]:
                return True

        # Medium trust operations require confirmation
        if self.trust_level == TrustLevel.MEDIUM:
            if capability in [
                Capability.FILE_DELETION,
                Capability.SYSTEM_COMMANDS
            ]:
                return True

        return False

    def confirm_operation(self, operation_id: str) -> None:
        """
        Confirm an operation.

        Args:
            operation_id: Operation identifier
        """
        self.confirmed_operations.append(operation_id)
        logger.info(f"Operation confirmed: {operation_id}")

    def increase_trust_level(self) -> None:
        """Increase trust level"""
        if self.trust_level.value < TrustLevel.HIGH.value:
            new_level = TrustLevel(self.trust_level.value + 1)
            self.trust_level = new_level
            logger.info(f"Trust level increased to: {new_level.name}")
        else:
            logger.warning("Already at maximum trust level")

    def decrease_trust_level(self) -> None:
        """Decrease trust level"""
        if self.trust_level.value > TrustLevel.UNTRUSTED.value:
            new_level = TrustLevel(self.trust_level.value - 1)
            self.trust_level = new_level
            logger.info(f"Trust level decreased to: {new_level.name}")
        else:
            logger.warning("Already at minimum trust level")

    def reset_trust_level(self) -> None:
        """Reset trust level to untrusted"""
        self.trust_level = TrustLevel.UNTRUSTED
        self.confirmed_operations.clear()
        logger.info("Trust level reset to UNTRUSTED")

    def get_available_capabilities(self) -> List[Capability]:
        """Get capabilities available at current trust level"""
        available = []
        for capability, required_level in self.capability_requirements.items():
            if self.trust_level.value >= required_level.value:
                available.append(capability)

        return available

    def get_status(self) -> Dict:
        """Get capability gate status"""
        return {
            "trust_level": self.trust_level.name,
            "trust_level_value": self.trust_level.value,
            "available_capabilities": [c.value for c in self.get_available_capabilities()],
            "confirmed_operations": len(self.confirmed_operations),
            "max_trust_level": TrustLevel.HIGH.value
        }

    # ------------------------------------------------------------------
    # Convenience aliases used by integration tests
    # ------------------------------------------------------------------

    def set_trust_level(self, level: int) -> None:
        """Set trust level by integer value (0-3)."""
        self.trust_level = TrustLevel(max(0, min(level, TrustLevel.HIGH.value)))
        logger.info(f"Trust level set to: {self.trust_level.name}")

    def check_permission(self, operation: str) -> bool:
        """
        Check if *operation* string is permitted at the current trust level.

        Maps common operation names to Capability enum values.
        """
        _op_map = {
            "voice_interaction": Capability.VOICE_INTERACTION,
            "information_retrieval": Capability.INFORMATION_RETRIEVAL,
            "application_launch": Capability.APPLICATION_LAUNCH,
            "file_reading": Capability.FILE_READING,
            "file_writing": Capability.FILE_WRITING,
            "file_deletion": Capability.FILE_DELETION,
            "system_command": Capability.SYSTEM_COMMANDS,
            "system_commands": Capability.SYSTEM_COMMANDS,
            "system_shutdown": Capability.SYSTEM_SHUTDOWN,
            "system_restart": Capability.SYSTEM_RESTART,
            "security_settings": Capability.SECURITY_SETTINGS,
        }
        capability = _op_map.get(operation.lower())
        if capability is None:
            logger.warning(f"Unknown operation for permission check: {operation}")
            return False
        return self.can_execute(capability)
