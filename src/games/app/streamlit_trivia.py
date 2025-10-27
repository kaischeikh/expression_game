from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import streamlit as st

from games.games.trivia_game import (
    NotEnoughQuestionsError,
    Question,
    TriviaGame,
)


@dataclass
class TriviaSession:
    game: TriviaGame
    rounds: int
    categories: list[str]
    difficulties: list[str]
    history: list[dict[str, Any]] = field(default_factory=list)
    current_question: Question | None = None
    current_selection: str | None = None
    question_number: int = 0
    answered: bool = False
    was_correct: bool | None = None

    def next_question(self) -> None:
        question = self.game.next_question()
        self.current_question = question
        if question:
            self.question_number = len(self.history) + 1
        else:
            self.question_number = len(self.history)
        self.current_selection = None
        self.answered = False
        self.was_correct = None

    def submit_answer(self, guess: str) -> bool:
        if not self.current_question:
            return False

        if self.answered:
            return bool(self.was_correct)

        self.answered = True
        self.current_selection = guess
        self.was_correct = self.game.answer_question(self.current_question, guess)
        self.history.append(
            {
                "question": self.current_question,
                "selected": guess,
                "correct": self.was_correct,
            }
        )
        return self.was_correct

    def questions_remaining(self) -> int:
        return self.game.questions_remaining()

    def total_rounds(self) -> int:
        return self.game.total_rounds()


def _ensure_session_state() -> None:
    if "trivia_session" not in st.session_state:
        st.session_state.trivia_session: TriviaSession | None = None


def _start_new_game(
    rounds: int,
    categories: Iterable[str],
    difficulties: Iterable[str],
    seed: int | None = None,
) -> None:
    game = TriviaGame(random_seed=seed)
    try:
        game.start_game(
            rounds=rounds, categories=categories, difficulties=difficulties
        )
    except NotEnoughQuestionsError as exc:
        st.error(
            f"{exc} Try reducing the number of rounds or broadening your filters."
        )
        return

    session = TriviaSession(
        game=game,
        rounds=rounds,
        categories=list(categories),
        difficulties=list(difficulties),
    )
    session.next_question()
    st.session_state.trivia_session = session
    st.toast("New trivia challenge ready! Scroll down to begin.")


def _render_header(session: TriviaSession | None) -> None:
    st.title("Trivia Pursuit")
    st.caption(
        "Race against your own knowledge. Lock in your answer, uncover explanations, "
        "and track your streak across categories."
    )

    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at top, #f7fbff, #eef3ff 45%, #e7ebff 100%);
        }
        .score-card {
            border-radius: 16px;
            padding: 1.4rem;
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid rgba(64, 106, 255, 0.15);
            box-shadow: 0 18px 40px -24px rgba(64, 106, 255, 0.6);
            backdrop-filter: blur(12px);
        }
        .question-card {
            border-radius: 18px;
            padding: 2rem;
            margin-top: 1rem;
            background: linear-gradient(135deg, #ffffff 0%, #f6f8ff 100%);
            box-shadow: 0 20px 35px -28px rgba(34, 40, 90, 0.55);
            border: 1px solid rgba(64, 106, 255, 0.12);
        }
        .option-pill {
            display: block;
            padding: 0.85rem 1.1rem;
            border-radius: 12px;
            border: 1px solid rgba(64, 106, 255, 0.15);
            margin-bottom: 0.6rem;
            color: #222958;
            background: rgba(255, 255, 255, 0.6);
        }
        .option-pill:hover {
            border-color: rgba(64, 106, 255, 0.3);
        }
        .history-card {
            border: 1px solid rgba(64, 106, 255, 0.1);
            border-radius: 14px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.8rem;
            background: rgba(255, 255, 255, 0.65);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    metrics_columns = st.columns(3)
    total_rounds = session.total_rounds() if session else 0
    with metrics_columns[0]:
        success_delta = (
            f"{(session.game.score / total_rounds * 100):.0f}% success"
            if session and total_rounds
            else None
        )
        st.metric(
            "Score",
            value=session.game.score if session else 0,
            delta=success_delta,
        )
    with metrics_columns[1]:
        round_delta = (
            f"{total_rounds} rounds"
            if session and total_rounds
            else "Configure and start"
        )
        st.metric(
            "Question",
            value=session.question_number if session else 0,
            delta=round_delta,
        )
    with metrics_columns[2]:
        remaining = session.questions_remaining() if session else 0
        if not session:
            remaining_delta = "Press start"
        elif remaining == 0:
            remaining_delta = "Session complete"
        else:
            remaining_delta = "Keep going!"

        st.metric(
            "Remaining",
            value=remaining,
            delta=remaining_delta,
        )


def _render_sidebar(
    default_rounds: int, categories: list[str], question_pool_size: int
) -> None:
    with st.sidebar:
        st.header("Game Setup")
        st.write("Choose your filters and spin up a new trivia pursuit.")

        max_rounds = min(12, question_pool_size)
        min_rounds = 3 if question_pool_size >= 3 else question_pool_size

        rounds = st.slider(
            "Rounds",
            min_value=min_rounds,
            max_value=max_rounds,
            value=default_rounds,
            help="How many questions should this session include?",
        )
        selected_categories = st.multiselect(
            "Categories",
            options=categories,
            help="Leave empty to include every category in the bank.",
        )
        difficulties = st.select_slider(
            "Difficulty",
            options=["easy", "medium", "hard"],
            value=("easy", "hard"),
            help="Pick a range to challenge yourself.",
        )

        seed = st.number_input(
            "Seed (optional)",
            min_value=0,
            step=1,
            value=0,
            help="Use a seed for reproducible question order. Leave at 0 to randomize.",
        )

        start = st.button("Start new game", use_container_width=True, type="primary")

    if start:
        difficulty_range = _expand_difficulty_range(difficulties)
        _start_new_game(
            rounds=rounds,
            categories=selected_categories,
            difficulties=difficulty_range,
            seed=seed or None,
        )


def _expand_difficulty_range(selection: tuple[str, str] | list[str]) -> list[str]:
    if isinstance(selection, (tuple, list)) and len(selection) == 2:
        ordering = ["easy", "medium", "hard"]
        start_idx = ordering.index(selection[0])
        end_idx = ordering.index(selection[1])
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
        return ordering[start_idx : end_idx + 1]
    return list(selection)


def _render_question(session: TriviaSession) -> None:
    if not session.current_question:
        st.success("All questions complete! Start a new game from the sidebar.")
        st.metric("Final score", f"{session.game.score}/{session.total_rounds()}")
        return

    question = session.current_question
    st.markdown(
        f"""
        <div class="question-card">
            <div style="font-size:0.9rem; text-transform:uppercase; letter-spacing:0.08em; color:#4050aa;">
                {question.category} • {question.difficulty.title()}
            </div>
            <h2 style="margin-top:0.4rem; color:#1a2353;">Question {session.question_number}</h2>
            <p style="font-size:1.05rem; color:#1f2345; line-height:1.6;">{question.prompt}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    options = ["Choose an answer"] + list(question.options)
    radio_key = f"choice_{session.question_number}"

    if (
        session.current_selection
        and session.current_selection in question.options
    ):
        st.session_state[radio_key] = session.current_selection
    elif radio_key in st.session_state and not session.current_selection:
        # Reset selection when loading a fresh question
        del st.session_state[radio_key]

    with st.form(f"answer_form_{session.question_number}", clear_on_submit=False):
        choice = st.radio(
            "Select your answer",
            options=options,
            label_visibility="collapsed",
            key=radio_key,
            disabled=session.answered,
        )
        submitted = st.form_submit_button("Lock in answer", use_container_width=True)

    if submitted:
        if choice == options[0]:
            st.warning("Pick an answer before locking it in.")
        else:
            session.submit_answer(choice)
            st.session_state[radio_key] = choice

    if session.answered:
        if session.was_correct:
            st.success("Nice! You nailed it 🎉")
        else:
            st.error(
                f"Not quite. The correct answer was **{question.answer}**."
            )

        if question.explanation:
            with st.expander("Why this answer?"):
                st.write(question.explanation)

        if session.questions_remaining():
            if st.button("Next question", type="primary", use_container_width=True):
                session.next_question()
                st.experimental_rerun()
        else:
            st.info(
                "That's the final question for this round. Start a fresh game from the sidebar to continue."
            )

    total_rounds = session.total_rounds()
    if total_rounds:
        progress = min(session.question_number / total_rounds, 1.0)
        st.progress(progress)


def _render_history(session: TriviaSession) -> None:
    if not session.history:
        return

    with st.expander("Review your answers"):
        for entry in reversed(session.history):
            question: Question = entry["question"]
            correct = entry["correct"]
            badge_color = "#32a852" if correct else "#d64545"
            badge_label = "Correct" if correct else "Missed"
            st.markdown(
                f"""
                <div class="history-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:600; color:#1b2248;">{question.category}</span>
                        <span style="background:{badge_color}; color:white; border-radius:999px; padding:0.2rem 0.75rem; font-size:0.8rem;">
                            {badge_label}
                        </span>
                    </div>
                    <p style="margin:0.4rem 0; color:#1f2345;"><strong>{question.prompt}</strong></p>
                    <p style="margin:0; color:#1f2345;">Your answer: <em>{entry['selected']}</em></p>
                    <p style="margin:0.2rem 0 0; color:#4050aa;">Correct answer: {question.answer}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def main() -> None:
    st.set_page_config(
        page_title="Trivia Pursuit",
        page_icon="🧠",
        layout="wide",
        menu_items={
            "Get help": None,
            "Report a bug": None,
            "About": "Trivia Pursuit — a quick-fire knowledge race built with Streamlit.",
        },
    )

    _ensure_session_state()

    base_game = TriviaGame()
    categories = base_game.available_categories()
    question_pool_size = len(base_game.question_bank)
    default_rounds = min(6, question_pool_size)
    _render_sidebar(
        default_rounds=default_rounds,
        categories=categories,
        question_pool_size=question_pool_size,
    )

    session: TriviaSession | None = st.session_state.trivia_session
    _render_header(session)

    if not session:
        st.info("Pick your game settings in the sidebar and press **Start new game** to begin.")
        return

    _render_question(session)
    _render_history(session)


if __name__ == "__main__":
    main()
