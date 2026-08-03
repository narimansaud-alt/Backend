from collections.abc import Generator

import pytest


@pytest.fixture(scope="session", autouse=True)
def load_initial_data() -> Generator[None]:
    """Pure domain tests do not start the integration-test containers."""
    yield
