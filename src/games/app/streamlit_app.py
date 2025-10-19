from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from games.games.riddle_game import (
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    OllamaNotAvailable,
    RiddleGame,
)


@dataclass
class GameState:
    game: RiddleGame
    max_rounds: int
    difficulty: str
    round: int = 0
    hints: list[str] | None = None
    responses: list[dict[str, str]] | None = None
    answer_revealed: bool = False
    answer: str | None = None

    def __post_init__(self) -> None:
        if self.hints is None:
            self.hints = []
        if self.responses is None:
            self.responses = []


def _format_system_prompt(
    custom_prompt: str | None, rounds: int, difficulty: str
) -> str:
    if custom_prompt:
        return custom_prompt.strip()
    return DEFAULT_SYSTEM_PROMPT.format(rounds, difficulty).strip()


def _load_models() -> list[str]:
    try:
        return list(RiddleGame.list_models())
    except OllamaNotAvailable as exc:
        st.sidebar.warning(f"Could not reach Ollama to list models: {exc}")
        return []


def _ensure_state() -> None:
    if "ui_state" not in st.session_state:
        st.session_state.ui_state: dict[str, Any] = {"game_state": None}


def start_new_game(
    model: str, rounds: int, difficulty: str, system_prompt: str
) -> None:
    game = RiddleGame(model=model, system_prompt=system_prompt)
    try:
        game.start_sentence()
        first_hint = game.hint()
    except OllamaNotAvailable as exc:
        st.error(f"Could not reach Ollama: {exc}")
        return

    state = GameState(
        game=game,
        max_rounds=rounds,
        difficulty=difficulty,
        round=0,
    )
    if first_hint:
        state.hints.append(first_hint)
    st.session_state.ui_state["game_state"] = state
    st.toast("New riddle ready! Scroll down to play.")


def handle_answer_submission(state: GameState, answer: str) -> None:
    answer = answer.strip()
    if not answer:
        return

    if answer.lower() == "answer":
        reveal_answer(state)
        return

    try:
        feedback = state.game.validate_answer(answer)
    except OllamaNotAvailable as exc:
        st.error(f"Could not reach Ollama: {exc}")
        return

    state.round += 1
    state.responses.append({"guess": answer, "feedback": feedback})


def request_additional_hint(state: GameState) -> None:
    try:
        hint = state.game.hint()
    except OllamaNotAvailable as exc:
        st.error(f"Could not reach Ollama: {exc}")
        return

    state.hints.append(hint)


def reveal_answer(state: GameState) -> None:
    try:
        solution = state.game.give_answer()
    except OllamaNotAvailable as exc:
        st.error(f"Could not reach Ollama: {exc}")
        return

    state.answer = solution
    state.answer_revealed = True


def main() -> None:
    st.set_page_config(page_title="Expression Game", page_icon="🧩")
    st.title("Expression Game")
    st.caption("Play a riddle game powered by your local Ollama models.")

    _ensure_state()

    available_models = _load_models()
    if available_models and DEFAULT_MODEL in available_models:
        default_index = available_models.index(DEFAULT_MODEL)
    elif available_models:
        default_index = 0
    else:
        available_models = [DEFAULT_MODEL]
        default_index = 0

    with st.sidebar.form("settings"):
        st.subheader("Game Settings")
        model = st.selectbox(
            "Model", options=available_models, index=default_index
        )
        rounds = st.slider(
            "Number of attempts", min_value=3, max_value=10, value=5
        )
        difficulty = st.selectbox(
            "Difficulty", options=["easy", "medium", "hard"], index=1
        )
        custom_prompt = st.text_area(
            "Custom system prompt (optional)",
            placeholder="Leave empty to use the default host persona.",
        )
        start = st.form_submit_button("Start new game")

    if start:
        system_prompt = _format_system_prompt(
            custom_prompt, rounds, difficulty
        )
        start_new_game(
            model=model,
            rounds=rounds,
            difficulty=difficulty,
            system_prompt=system_prompt,
        )

    state: GameState | None = st.session_state.ui_state.get("game_state")

    if not state:
        st.info(
            "Configure your settings in the sidebar and start the game to receive a riddle."
        )
        return

    st.subheader("Riddle")
    st.write(state.game.enigma)

    if state.hints:
        st.subheader("Hints")
        for idx, hint in enumerate(state.hints, start=1):
            st.markdown(f"**Hint {idx}:** {hint}")

    if not state.answer_revealed:
        remaining = state.max_rounds - state.round
        st.write(f"You have {max(remaining, 0)} attempts remaining.")

        need_hint = st.button("Need another hint?", key="another_hint")
        if need_hint:
            request_additional_hint(state)

        with st.form("answer_form", clear_on_submit=True):
            guess = st.text_input(
                "Your guess", placeholder="Type your answer here..."
            )
            submitted = st.form_submit_button("Submit guess")

        if submitted:
            handle_answer_submission(state, guess)

        reveal = st.button("Reveal answer", type="primary")
        if reveal:
            reveal_answer(state)
    else:
        st.success("Answer revealed!")

    if state.responses:
        st.subheader("Host Feedback")
        for entry in state.responses:
            st.markdown(f"**You:** {entry['guess']}")
            st.markdown(entry["feedback"])

    if state.answer_revealed and state.answer:
        st.subheader("Solution")
        st.markdown(state.answer)

    if state.round >= state.max_rounds and not state.answer_revealed:
        st.warning(
            "You've used all attempts. Reveal the answer or start a new game from the sidebar."
        )


if __name__ == "__main__":
    main()
