from __future__ import annotations

import argparse
import os
import sys
from textwrap import dedent

from games.games.riddle_game import (
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    OllamaNotAvailable,
    RiddleGame,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expression-game",
        description="Play a creative expression game powered by your local Ollama models.",
    )
    parser.add_argument(
        "--rounds",
        default=5,
        type=int,
        help="Number of rounds.",
    )
    parser.add_argument(
        "--difficulty",
        default="medium",
        choices=["easy", "medium", "hard"],
        help="Difficulty of the games.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OLLAMA_MODEL", DEFAULT_MODEL),
        help="Ollama model to use (defaults to the OLLAMA_MODEL env var or 'llama3').",
    )
    parser.add_argument(
        "--system-prompt",
        default=None,
        help="Custom system prompt. If omitted a playful default prompt is used.",
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available Ollama models and exit.",
    )
    return parser


def print_banner() -> None:
    banner = dedent(
        """
        Expression Game
        The Ollama model would give an enigma and you will have N turns to solve it.
        Type 'quit' or press Ctrl+C to exit.
        If you want to get the answer directly just type ANSWER.
        """
    ).strip()
    print(banner)


def interactive_mode(game: RiddleGame, rounds: int) -> int:
    print_banner()
    while True:
        game.start_sentence()
        hint = game.hint()
        print(f"\n{hint}")
        for round in range(rounds):
            try:
                answer = input("\nAnswer> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                return 0

            if not answer:
                continue
            if answer.lower() in {"quit", "exit"}:
                print("Thanks for playing!")
                return 0
            if answer.lower() == "answer":
                print("Here's your answer")
                final_answer = game.give_answer()
                print(f"\n{final_answer}")
                break
            if answer.lower() == "continue":
                print("We will continue playing.")
                break

            try:
                creative_prompt = game.validate_answer(answer)
            except OllamaNotAvailable as exc:
                print(f"\nCould not reach Ollama: {exc}", file=sys.stderr)
                return 2

            print(f"\n{creative_prompt}")


def list_models(game: RiddleGame) -> int:
    try:
        models = list(game.list_models())
    except OllamaNotAvailable as exc:
        print(f"Could not reach Ollama: {exc}", file=sys.stderr)
        return 2

    if not models:
        print("No models found. Use `ollama pull <name>` to add one.")
        return 1

    for name in models:
        print(name)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    game = RiddleGame(
        model=args.model,
        system_prompt=args.system_prompt
        or DEFAULT_SYSTEM_PROMPT.format(args.rounds, args.difficulty),
    )

    if args.list_models:
        return list_models(game)

    return interactive_mode(game, args.rounds)


if __name__ == "__main__":
    sys.exit(main())
