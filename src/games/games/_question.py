from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

import numpy as np
from ollama import ResponseError
from typing import Literal
import ollama
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator
)

from games.games._host import DEFAULT_MODEL, OllamaNotAvailable
from games.utils.error import GameError, InvalidQuestionFormat

CATEGORIES = [
    "History",
    "Science",
    "Geography",
    "Sports",
    "Entertainment",
    "Literature",
    "Technology",
    "Art",
]
VALID_DIFFICULTIES = ["easy", "medium", "hard"]


class Question(BaseModel):
    """Trivia question container validated by Pydantic."""

    category: str
    question: str
    options: tuple[str, ...]
    answer: str
    explanation: str | None = None
    difficulty: str = "medium"

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    def normalized_answer(self) -> str:
        return self.answer.strip().lower()

    @field_validator("category")
    @staticmethod
    def _validate_category(value: str) -> str:
        if value not in CATEGORIES:
            raise GameError(
                f"{value} is not admissible. It must be one of {CATEGORIES}."
            )
        return value

    @field_validator("question")
    @staticmethod
    def _validate_question(value: str) -> str:
        if not value:
            raise GameError("question cannot be empty.")
        return value

    @field_validator("options")
    @staticmethod
    def _validate_options(value: Iterable[str]) -> tuple[str, ...]:
        options = tuple(str(option).strip() for option in value)
        if len(options) < 2:
            raise GameError("at least two options are required.")
        if any(not option for option in options):
            raise GameError("options cannot contain empty strings.")
        return options

    @field_validator("answer")
    @staticmethod
    def _validate_answer(value: str) -> str:
        if not value:
            raise GameError("answer cannot be empty.")
        return value

    @field_validator("difficulty")
    @staticmethod
    def _normalize_difficulty(value: str) -> str:
        difficulty = value.lower() or "medium"
        if difficulty not in VALID_DIFFICULTIES:
            raise GameError(
                f"invalid difficulty '{value}'. "
                f"Expected one of {sorted(VALID_DIFFICULTIES)}."
            )
        return difficulty

    @model_validator(mode="after")
    def _ensure_answer_in_options(self) -> "Question":
        if self.answer not in self.options:
            raise GameError(
                "answer must exactly match one of the provided options."
            )
        return self

    def __repr__(self) -> str:
        question_preview = self.question
        if len(question_preview) > 60:
            question_preview = f"{question_preview[:57]}..."
        return (
            "Question(\n"
            f"\tcategory={self.category!r}, \n"
            f"\tdifficulty={self.difficulty!r}, \n"
            f"\tquestion={question_preview!r}\n"
            f"\toptions={self.options!r}\n"
            f"\tanswer={self.answer!r}, \n"
            f"\texplanation={self.explanation!r}\n"
            ")"
        )

    def to_dict(self) -> dict[str, Any]:
        payload = self.model_dump(by_alias=True)
        payload["options"] = list(self.options)
        return payload

    def to_json(self, *, indent: int | None = None) -> str:
        return self.model_dump_json(indent=indent, by_alias=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Question":
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise ValueError(exc.errors()) from exc

    @classmethod
    def from_json(cls, raw: str) -> "Question":
        payload = json.loads(raw)
        if not isinstance(payload, Mapping):
            raise TypeError("JSON payload must decode to a mapping.")
        return cls.from_dict(payload)

    @classmethod
    def question_template(cls) -> dict:
        valid_categories = ", ".join(CATEGORIES)
        valid_difficulties = "|".join(VALID_DIFFICULTIES)
        template = {
            "category": f"<one of: {valid_categories}>",
            "question": "<trivia question ending with a question mark>",
            "options": [
                "<answer option 1>",
                "<answer option 2>",
                "<answer option 3>",
                "<answer option 4>",
            ],
            "answer": "<must exactly match one of the options>",
            "explanation": "<short fact explaining why the answer is correct>",
            "difficulty": f"<{valid_difficulties}>",
        }

        return template


class QuestionGenerator:
    """This is a generator for questions based on the Ollama model.
    """
    model: str = DEFAULT_MODEL
    system_prompt: str = (
        "You are preparing questions for a Trivia game. "
        "Respond with a single JSON object that adheres to this schema:\n"
        f"{Question.question_template()}\n"
        "Guidelines:\n"
        "- JSON only. No markdown, code fences, or explanations outside the object.\n"
        "- Provide exactly four distinct answer options.\n"
        "- Ensure the answer string matches one option verbatim.\n"
        "- Explanations should be at most two sentences and factual.\n"
        "- Avoid sensitive, political, or adult-only subject matter.\n"
    )

    def generate_question(
        self,
        *,
        category: str | None = None,
        difficulty: str = "medium"
    ) -> Question:
        if category is None:
            category = f"any category among {CATEGORIES}"
        category = category.strip().lower()

        difficulty_value = difficulty.strip().lower()

        if difficulty_value not in VALID_DIFFICULTIES:
            raise GameError(
                f"Unsupported difficulty '{difficulty}'. "
                f"Expected one of {sorted(VALID_DIFFICULTIES)}."
            )

        user_prompt = (
            f"Generate one {difficulty_value} difficulty trivia question about {category}. "
            "Respond using the exact JSON schema described in the system prompt."
        )

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                format=Question.model_json_schema()
            )
        except ResponseError as exc:  # pragma: no cover - requires Ollama runtime
            raise OllamaNotAvailable(str(exc)) from exc

        message = response.get("message") or {}
        content = message.get("content", "").strip()
        if not content:
            raise InvalidQuestionFormat("Empty content received from Ollama.")

        try:
            payload_text = _extract_json_blob(content)
            question = Question.from_json(payload_text)
        except json.JSONDecodeError as exc:
            raise InvalidQuestionFormat(f"Malformed JSON payload: {exc}") from exc
        except (ValueError, TypeError, KeyError) as exc:
            raise InvalidQuestionFormat(f"Generated question invalid: {exc}") from exc

        return question

    def generate_questions(
        self,
        count: int = 10,
        *,
        categories: Iterable[str] | None = None,
        difficulties: Iterable[str] | None = None,
    ) -> list[Question]:
        if count < 1:
            raise ValueError("count must be at least 1.")
        if categories is None:
            categories = CATEGORIES
        if difficulties is None:
            difficulties = VALID_DIFFICULTIES
        random_categories = np.random.choice(categories, count)
        random_difficulties = np.random.choice(difficulties, count)
        questions: list[Question] = []
        for category, difficulty in zip(random_categories, random_difficulties):
            question = self.generate_question(
                category=category, difficulty=difficulty
            )
            questions.append(question)
        return questions



def _extract_json_blob(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start > end:
        raise InvalidQuestionFormat("Could not locate JSON object in response.")

    return text[start : end + 1]
