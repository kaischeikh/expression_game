from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import ollama
from ollama import ResponseError


DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
DEFAULT_SYSTEM_PROMPT = """
        You are the playful host of a game about enigmas.
        You will give an enigma and then give the user 5 trials before giving the right answer.
        The difficulty would be {}.
    """


class OllamaNotAvailable(RuntimeError):
    """Raised when the Ollama API cannot be reached."""


@dataclass
class ExpressionGame:
    model: str = DEFAULT_MODEL
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    def build_messages(self, answer: str | None = None) -> list[dict[str, str]]:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if answer:
            messages.append({"role": "user", "content": answer})
        else:
            messages.append({"role": "user", "content": "Generate first enigma."})
        return messages
    
    def generate_enigma(self) -> str:
        try:
            response = ollama.chat(
                model=self.model,
                messages=self.build_messages()
            )
        except ResponseError as exc:  # pragma: no cover - requires Ollama runtime
            raise OllamaNotAvailable(str(exc)) from exc

        message = response.get("message")
        if not message or "content" not in message:
            raise OllamaNotAvailable("Unexpected response from Ollama service.")

        return message["content"].strip()

    def validate_response(
        self, answer: str
    ) -> str:
        try:
            response = ollama.chat(
                model=self.model,
                messages=self.build_messages(answer),
            )
        except ResponseError as exc:  # pragma: no cover - requires Ollama runtime
            raise OllamaNotAvailable(str(exc)) from exc
       
        message = response.get("message")
        if not message or "content" not in message:
            raise OllamaNotAvailable("Unexpected response from Ollama service.")

        return message["content"].strip()

    def list_models(self) -> Iterable[str]:
        try:
            available = ollama.list()
        except ResponseError as exc:  # pragma: no cover
            raise OllamaNotAvailable(str(exc)) from exc

        for item in available.get("models", []):
            name = item.get("name")
            if name:
                yield name
