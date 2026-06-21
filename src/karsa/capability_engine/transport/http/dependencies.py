"""Dependency providers -- Sprint-12. Wave-4.

FastAPI Depends() providers for command and query facades.
Resolved from bootstrap wiring. No global singletons.
"""

from typing import Optional

from karsa.capability_engine.integration.capability_command_facade import (
    CapabilityCommandFacade,
)
from karsa.capability_engine.integration.capability_query_facade import (
    CapabilityQueryFacade,
)

# Module-level references set by bootstrap at app startup.
# These are NOT singletons -- they are set once per application
# lifecycle via set_dependencies() and cleared via clear_dependencies().
_command_facade: Optional[CapabilityCommandFacade] = None
_query_facade: Optional[CapabilityQueryFacade] = None


def set_dependencies(
    command_facade: CapabilityCommandFacade,
    query_facade: CapabilityQueryFacade,
) -> None:
    """Set dependency references. Called by bootstrap at app startup."""
    global _command_facade, _query_facade
    _command_facade = command_facade
    _query_facade = query_facade


def clear_dependencies() -> None:
    """Clear dependency references. Called at app shutdown."""
    global _command_facade, _query_facade
    _command_facade = None
    _query_facade = None


def get_command_facade() -> CapabilityCommandFacade:
    """FastAPI dependency provider for CapabilityCommandFacade.

    Raises RuntimeError if dependencies not initialized.
    """
    if _command_facade is None:
        raise RuntimeError(
            "Command facade not initialized. Call set_dependencies() first."
        )
    return _command_facade


def get_query_facade() -> CapabilityQueryFacade:
    """FastAPI dependency provider for CapabilityQueryFacade.

    Raises RuntimeError if dependencies not initialized.
    """
    if _query_facade is None:
        raise RuntimeError(
            "Query facade not initialized. Call set_dependencies() first."
        )
    return _query_facade
