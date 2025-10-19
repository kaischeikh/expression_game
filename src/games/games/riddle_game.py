import os
from dataclasses import dataclass, field

import ollama
from ollama import ResponseError

from games.games._host import HostGame, OllamaNotAvailable

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
DEFAULT_SYSTEM_PROMPT = """
    You are the playful host of a game about riddles.
    You will give a riddle and then give the user {} trials before giving the right answer.
    The difficulty would be {}.
"""


@dataclass
class RiddleGame(HostGame):
    model: str = DEFAULT_MODEL
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    enigma: str = ""
    _messages: list[dict[str, str]] = field(default_factory=list)

    def start_sentence(self) -> None:
        try:
            response = ollama.chat(
                model=self.model, messages=self.build_messages()
            )
        except ResponseError as exc:
            raise OllamaNotAvailable(str(exc)) from exc

        enigma = response.get("message")
        if not enigma or "content" not in enigma:
            raise OllamaNotAvailable(
                "Unexpected response from Ollama service."
            )

        self.enigma = enigma["content"].strip()
        if self._messages == []:
            self._messages = [
                {"role": "system", "content": self.system_prompt},
                response.get("message"),
            ]
        else:
            self._messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "assistant",
                    "content": "This is not the first game of the player. No need for an intro.",
                },
                response.get("message"),
            ]

    def hint(self):
        try:
            _messages = self._messages.copy()
            _messages.append({"role": "system", "content": "Provide a hint"})
            response = ollama.chat(model=self.model, messages=_messages)
        except (
            ResponseError
        ) as exc:  # pragma: no cover - requires Ollama runtime
            raise OllamaNotAvailable(str(exc)) from exc

        hint = response.get("message")
        if not hint or "content" not in hint:
            raise OllamaNotAvailable(
                "Unexpected response from Ollama service."
            )

        self._messages.append(hint)
        return hint["content"].strip()

    def validate_answer(self, answer: str):
        self._messages.append({"role": "user", "content": answer})
        try:
            response = ollama.chat(
                model=self.model,
                messages=self._messages,
            )
        except (
            ResponseError
        ) as exc:  # pragma: no cover - requires Ollama runtime
            raise OllamaNotAvailable(str(exc)) from exc

        message = response.get("message")
        if not message or "content" not in message:
            raise OllamaNotAvailable(
                "Unexpected response from Ollama service."
            )
        self._messages.append(message)
        return message["content"].strip()

    def give_answer(self) -> str:
        self._messages.append(
            {
                "role": "user",
                "content": "The player has decided to quit. Stop the game and give the answer, then explain the riddle.",
            }
        )
        try:
            response = ollama.chat(
                model=self.model,
                messages=self._messages,
            )
        except (
            ResponseError
        ) as exc:  # pragma: no cover - requires Ollama runtime
            raise OllamaNotAvailable(str(exc)) from exc

        message = response.get("message")
        if not message or "content" not in message:
            raise OllamaNotAvailable(
                "Unexpected response from Ollama service."
            )
        self._messages.append(message)
        return message["content"].strip()
