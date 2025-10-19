from dataclasses import dataclass
from abc import ABC, abstractmethod
import ollama
from ollama import ResponseError
from typing import Iterable

@dataclass
class HostGame(ABC):
    model: str
    system_prompt: str

    @classmethod
    def list_models(cls) -> Iterable[str]:
        try:
            available = ollama.list()
        except ResponseError as exc:  # pragma: no cover
            raise OllamaNotAvailable(str(exc)) from exc

        for item in available.get("models", []):
            name = item.get("name")
            if name:
                yield name 
    
    def build_messages(self, answer: str | None = None) -> list[dict[str, str]]:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if answer:
            messages.append({"role": "user", "content": answer})
        
        return messages

    @abstractmethod
    def start_sentence(self) -> None:
        raise NotImplementedError    



class OllamaNotAvailable(RuntimeError):
    """Raised when the Ollama API cannot be reached."""