"""Test helpers."""

from typing import Any

from app.settings import Settings


def build_settings(**overrides: Any) -> Settings:
    """Build settings without reading a developer's local ``.env``.

    pydantic-settings accepts ``_env_file`` at runtime, but the ``__init__``
    signature it generates for type checkers does not advertise it. The
    resulting ignore is confined to this one function rather than repeated at
    every call site.
    """
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]
