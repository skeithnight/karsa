"""Tests for dependency providers -- Sprint-12. Wave-4.

Covers:
- set_dependencies / clear_dependencies
- get_command_facade raises when not initialized
- get_query_facade raises when not initialized
- providers return correct facades
"""

import pytest
from unittest.mock import MagicMock

from karsa.capability_engine.transport.http.dependencies import (
    set_dependencies,
    clear_dependencies,
    get_command_facade,
    get_query_facade,
)
from karsa.capability_engine.integration.capability_command_facade import (
    CapabilityCommandFacade,
)
from karsa.capability_engine.integration.capability_query_facade import (
    CapabilityQueryFacade,
)


@pytest.fixture(autouse=True)
def cleanup():
    """Clear dependencies after each test."""
    yield
    clear_dependencies()


class TestDependencyProviders:
    """Dependency provider resolution."""

    def test_get_command_facade_raises_when_not_initialized(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            get_command_facade()

    def test_get_query_facade_raises_when_not_initialized(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            get_query_facade()

    def test_set_dependencies_enables_providers(self):
        cmd = MagicMock(spec=CapabilityCommandFacade)
        qry = MagicMock(spec=CapabilityQueryFacade)

        set_dependencies(command_facade=cmd, query_facade=qry)

        assert get_command_facade() is cmd
        assert get_query_facade() is qry

    def test_clear_dependencies_disables_providers(self):
        cmd = MagicMock(spec=CapabilityCommandFacade)
        qry = MagicMock(spec=CapabilityQueryFacade)

        set_dependencies(command_facade=cmd, query_facade=qry)
        clear_dependencies()

        with pytest.raises(RuntimeError):
            get_command_facade()
        with pytest.raises(RuntimeError):
            get_query_facade()

    def test_set_dependencies_replaces_previous(self):
        cmd1 = MagicMock(spec=CapabilityCommandFacade)
        cmd2 = MagicMock(spec=CapabilityCommandFacade)
        qry = MagicMock(spec=CapabilityQueryFacade)

        set_dependencies(command_facade=cmd1, query_facade=qry)
        set_dependencies(command_facade=cmd2, query_facade=qry)

        assert get_command_facade() is cmd2
