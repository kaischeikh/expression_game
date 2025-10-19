"""
An interactive CLI that turns local Ollama models into a lightweight
creative writing game.
"""

from importlib.metadata import version, PackageNotFoundError


try:
    __version__ = version("expression-game")
except PackageNotFoundError:  # pragma: no cover - fallback during local dev
    __version__ = "0.0.0"


__all__ = ["__version__"]
