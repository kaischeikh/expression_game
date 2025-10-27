class GameError(Exception):
    """Raised when an Ollama response cannot be parsed into a Question."""

class InvalidQuestionFormat(RuntimeError):
    """Raised when an Ollama response cannot be parsed into a Question."""