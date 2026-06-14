from __future__ import annotations

import logging
import os
import sqlite3
import sys
from pathlib import Path

from games.games.trivia_game import QuestionGenerator


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    _load_env_file(root / ".env")

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)
    logger = logging.getLogger("check_question_bank")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False

    db_path = os.getenv("QUESTIONS_DB_PATH", "./data/questions.db")
    db_file = Path(db_path)
    if not db_file.is_absolute():
        db_file = (root / db_file).resolve()
    if not db_file.exists():
        logger.error("Database not found: %s", db_file)
        return 1

    minimum_required = _get_env_int("MINIMAL_NUMBER_OF_QUESTIONS", 0)
    connection = sqlite3.connect(str(db_file))
    try:
        rows = connection.execute(
            """
            SELECT
                category,
                difficulty,
                SUM(CASE WHEN asked = 0 THEN 1 ELSE 0 END) AS remaining,
                COUNT(*) AS total
            FROM questions
            GROUP BY category, difficulty
            ORDER BY category, difficulty
            """
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        logger.info("No questions found in the database.")
        return 0

    logger.info("Database: %s", db_file)
    logger.info("Minimum required per category/difficulty: %s", minimum_required)
    logger.info("Category | Difficulty | Remaining | Total | Needed")
    logger.info("-" * 56)
    generator = QuestionGenerator()
    new_questions = []
    for category, difficulty, remaining, total in rows:
        needed = max(0, minimum_required - (remaining or 0))
        logger.info(
            "%s | %s | %s | %s | %s", category, difficulty, remaining, total, needed
        )
        if needed > 0:
            new_questions.append(
                generator.generate_questions(
                    count=needed,
                    categories=[category],
                    difficulties=[difficulty],
                    retry_on_invalid=True,
                    max_attempts=5,
                )
            )
    logger.info("Export New Questions")
    new_count = generator.export_questions_to_db(
        new_questions,
        db_path=db_file,
    )
    logger.info("Total number of added questions %d", new_count)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
