from __future__ import annotations

import json
import logging
import os
import random
import sqlite3
from pathlib import Path
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import ollama
from ollama import ResponseError

from games.games._host import DEFAULT_MODEL, OllamaNotAvailable
from games.games._question import Question, QuestionGenerator

DEFAULT_QUESTION_BANK: list[Question] = [
    Question(
        category="History",
        question="Which empire built the Machu Picchu complex in Peru?",
        options=("Aztec Empire", "Inca Empire", "Maya Civilization", "Toltec Empire"),
        answer="Inca Empire",
        explanation="Machu Picchu was constructed by the Inca Empire in the 15th century.",
    ),
    Question(
        category="Science",
        question="What is the heaviest naturally occurring element on Earth?",
        options=("Uranium", "Osmium", "Plutonium", "Lead"),
        answer="Uranium",
        explanation="Uranium (atomic number 92) is the heaviest stable element found in significant quantities.",
    ),
    Question(
        category="Geography",
        question="Which African country has the largest population?",
        options=("Nigeria", "Egypt", "Ethiopia", "South Africa"),
        answer="Nigeria",
        explanation="Nigeria has the largest population on the African continent, exceeding 200 million people.",
    ),
    Question(
        category="Sports",
        question="How many players are on the field for one team in a standard rugby union match?",
        options=("11", "13", "15", "18"),
        answer="15",
        explanation="Rugby union features 15 players per side on the field at any one time.",
    ),
    Question(
        category="Entertainment",
        question="Who composed the film score for 'Star Wars: A New Hope'?",
        options=("John Williams", "Hans Zimmer", "James Horner", "Danny Elfman"),
        answer="John Williams",
        explanation="John Williams composed the score, earning an Academy Award for Best Original Score.",
    ),
    Question(
        category="Literature",
        question="Which novel begins with the line, 'Call me Ishmael'?",
        options=("Moby-Dick", "Great Expectations", "Invisible Man", "The Old Man and the Sea"),
        answer="Moby-Dick",
        explanation="Herman Melville opens his novel 'Moby-Dick' with the iconic line, 'Call me Ishmael.'",
    ),
    Question(
        category="Technology",
        question="What does the acronym 'HTTP' stand for?",
        options=(
            "HyperText Transfer Protocol",
            "High Transmission Text Process",
            "Hyperlink Transfer Program",
            "Host Transfer Text Protocol",
        ),
        answer="HyperText Transfer Protocol",
        explanation="HTTP stands for HyperText Transfer Protocol, the foundation of data communication on the web.",
    ),
    Question(
        category="Art",
        question="Which painter created the artwork 'The Persistence of Memory'?",
        options=("Salvador Dalí", "Pablo Picasso", "Frida Kahlo", "Henri Matisse"),
        answer="Salvador Dalí",
        explanation="Salvador Dalí painted 'The Persistence of Memory' in 1931, featuring melting clocks.",
    ),
    Question(
        category="Science",
        question="What is the most abundant gas in Earth's atmosphere?",
        options=("Oxygen", "Nitrogen", "Carbon Dioxide", "Argon"),
        answer="Nitrogen",
        explanation="Nitrogen makes up about 78% of Earth's atmosphere.",
        difficulty="easy",
    ),
    Question(
        category="History",
        question="Who was the first woman to win a Nobel Prize?",
        options=("Marie Curie", "Rosalind Franklin", "Jane Addams", "Ada Lovelace"),
        answer="Marie Curie",
        explanation="Marie Curie won the Nobel Prize in Physics in 1903 and Chemistry in 1911.",
        difficulty="easy",
    ),
    Question(
        category="Geography",
        question="Which river flows through the city of Paris?",
        options=("Seine", "Danube", "Rhine", "Loire"),
        answer="Seine",
        explanation="Paris is situated on the banks of the River Seine.",
        difficulty="easy",
    ),
    Question(
        category="Entertainment",
        question="Which actor played the character of Jack Dawson in 'Titanic'?",
        options=("Leonardo DiCaprio", "Brad Pitt", "Matt Damon", "Johnny Depp"),
        answer="Leonardo DiCaprio",
        explanation="Leonardo DiCaprio portrayed Jack Dawson alongside Kate Winslet in the 1997 film.",
        difficulty="easy",
    ),
    Question(
        category="Sports",
        question="What is the only country to have played in every FIFA World Cup tournament?",
        options=("Brazil", "Germany", "Italy", "Argentina"),
        answer="Brazil",
        explanation="Brazil has qualified for every FIFA World Cup since the tournament began in 1930.",
    ),
    Question(
        category="Technology",
        question="Which company developed the video game console 'Switch'?",
        options=("Nintendo", "Sony", "Microsoft", "Sega"),
        answer="Nintendo",
        explanation="Nintendo launched the hybrid console 'Switch' in 2017.",
        difficulty="easy",
    ),
    Question(
        category="Literature",
        question="Who wrote the fantasy series 'A Song of Ice and Fire'?",
        options=(
            "George R.R. Martin",
            "J.R.R. Tolkien",
            "Patrick Rothfuss",
            "C.S. Lewis",
        ),
        answer="George R.R. Martin",
        explanation="George R.R. Martin authored the series that inspired HBO's 'Game of Thrones.'",
        difficulty="easy",
    ),
]

class QuestionsBank:
    bank: list[Question] = []
    categories: list[str] = []
    difficulties: list[str] = []

    def __init__(self, bank: list[Question] | None = None) -> None:
        if bank is None:
            bank = DEFAULT_QUESTION_BANK
        self.bank = bank
        self.categories = list(
            set(
                map(lambda question: question.category, bank)
            )
        )
        self.difficulties = list(
            set(
                map(lambda question: question.difficulty, bank)
            )
        )

    def append(self, question: Question) -> None:
        self.bank.append(question)
        self.categories.append(question.category)
        self.difficulties.append(question.difficulty)

    def extend(self, questions: Iterable[Question]) -> None:
        self.bank.extend(questions)
        self.categories.extend([q.category for q in questions])
        self.difficulties.extend([q.difficulty for q in questions])

    def load_from_db(self, db_path: str | None = None) -> int:
        db_path = _resolve_db_path(db_path)
        db_file = Path(db_path)
        if not db_file.exists():
            logging.getLogger(__name__).warning(
                "Question database not found: %s", db_file
            )
            return 0
        connection = sqlite3.connect(db_path)
        try:
            rows = connection.execute(
                """
                SELECT
                    category,
                    question,
                    options,
                    answer,
                    explanation,
                    difficulty,
                    asked
                FROM questions
                """
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc).lower():
                logging.getLogger(__name__).warning(
                    "Questions table not found in database: %s", db_file
                )
                return 0
            raise
        finally:
            connection.close()

        questions: list[Question] = []
        for row in rows:
            options = json.loads(row[2])
            questions.append(
                Question(
                    category=row[0],
                    question=row[1],
                    options=tuple(options),
                    answer=row[3],
                    explanation=row[4],
                    difficulty=row[5],
                    asked=bool(row[6]),
                )
            )
        self.extend(questions)
        return len(questions)

    def mark_asked(
        self,
        question: Question,
        *,
        asked: bool = True,
        db_path: str | None = None,
    ) -> int:
        db_path = _resolve_db_path(db_path)
        updates = 0
        for index, existing in enumerate(self.bank):
            if existing == question:
                self.bank[index] = existing.model_copy(
                    update={"asked": asked}
                )
                updates += 1
        connection = sqlite3.connect(db_path)
        try:
            cursor = connection.execute(
                """
                UPDATE questions
                SET asked = ?
                WHERE category = ?
                  AND question = ?
                  AND answer = ?
                  AND difficulty = ?
                """,
                (
                    int(asked),
                    question.category,
                    question.question,
                    question.answer,
                    question.difficulty,
                ),
            )
            connection.commit()
            updates = max(updates, cursor.rowcount)
        finally:
            connection.close()
        return updates

    @property
    def category_proportions(self):
        count = Counter(self.categories)
        return {key: value/len(self) for key, value in count.items()}

    @property
    def difficulties_proportions(self):
        count = Counter(self.difficulties)
        return {key: value/len(self) for key, value in count.items()}

    def __len__(self):
        return len(self.bank)

    def __iter__(self):
        return iter(self.bank)


def _resolve_db_path(db_path: str | None) -> str:
    if db_path is None:
        db_path = os.getenv("QUESTIONS_DB_PATH", "data/questions.db")
    path = Path(db_path).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path.as_posix()


class NotEnoughQuestionsError(RuntimeError):
    """Raised when there are not enough questions for the requested game settings."""


@dataclass
class TriviaGame:
    random_seed: int | None = None
    question_bank: QuestionsBank = QuestionsBank()
    _rng: random.Random = field(init=False, repr=False)
    _questions: list[Question] = field(default_factory=list, init=False, repr=False)
    _asked: list[Question] = field(default_factory=list, init=False, repr=False)
    _score: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.random_seed)

    @property
    def score(self) -> int:
        return self._score

    @property
    def asked_questions(self) -> Sequence[Question]:
        return tuple(self._asked)

    def available_categories(self) -> list[str]:
        categories = set(self.question_bank.categories)
        return sorted(categories)

    def start_game(
        self,
        *,
        rounds: int,
        categories: Iterable[str] | None = None,
        difficulties: Iterable[str] | None = None,
    ) -> None:
        selected_categories = {category.lower() for category in categories or []}
        selected_difficulties = {d.lower() for d in difficulties or []}

        def question_filter(question: Question) -> bool:
            category_ok = (
                not selected_categories
                or question.category.lower() in selected_categories
            )
            difficulty_ok = (
                not selected_difficulties
                or question.difficulty.lower() in selected_difficulties
            )
            return category_ok and difficulty_ok

        filtered = [q for q in self.question_bank if question_filter(q)]

        if len(filtered) < rounds:
            raise NotEnoughQuestionsError(
                "Not enough questions available for the chosen filters."
            )

        self._rng.shuffle(filtered)
        self._questions = filtered[:rounds]
        self._asked.clear()
        self._score = 0

    def next_question(self) -> Question | None:
        if not self._questions:
            return None

        question = self._questions.pop(0)
        self.question_bank.mark_asked(question, asked=True)
        asked_question = question.model_copy(update={"asked": True})
        self._asked.append(asked_question)
        return asked_question

    def questions_remaining(self) -> int:
        return len(self._questions)

    def total_rounds(self) -> int:
        return len(self._questions) + len(self._asked)

    def answer_question(self, question: Question, guess: str) -> bool:
        is_correct = question.normalized_answer() == guess.strip().lower()
        if is_correct:
            self._score += 1
        return is_correct
