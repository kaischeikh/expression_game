# Expression Game

Expression Game is a collection of puzzle experiences powered by locally running
Ollama models. Play the original riddle challenge from the terminal, or launch
two Streamlit apps that bring the riddles and a trivia contest to the browser.

## Apps

- **Expression Game (Streamlit)** — the visual version of the riddle host,
  offering hints, answer reveals, and configurable difficulty.
- **Trivia Pursuit (Streamlit)** — test your knowledge across categories with
  multi-choice questions, streak tracking, and per-round history.
- **CLI Riddle Game** — a fast terminal workflow for riddles, perfect for
  scripted runs or quick experiments.

## Features

- Works with any Ollama chat model you have pulled locally.
- Adjustable rounds, difficulty, and model selection per game.
- Browser-based interfaces for both riddles and trivia in addition to the CLI.
- Docker Compose recipe to serve both web apps simultaneously.

## Prerequisites

- A running [Ollama](https://ollama.com) server with at least one chat-capable
  model (for example `ollama pull llama3.1`).
- [uv](https://github.com/astral-sh/uv) for local installs and virtualenv
  management (optional but recommended).
- Docker (optional) if you prefer containerised execution.

## Local usage with uv

Install dependencies once:

```bash
uv pip install .
```

Run the CLI riddle host:

```bash
uv run riddle-game --rounds 5 --difficulty medium
```

Launch the Streamlit apps locally:

```bash
# Expression Game UI
uv run streamlit run src/games/app/streamlit_app.py

# Trivia Pursuit UI
uv run streamlit run src/games/app/streamlit_trivia.py
```

### CLI options

- `--rounds`: Number of guesses the player gets before the host offers the answer (default `5`).
- `--difficulty`: One of `easy`, `medium`, or `hard` (default `medium`).
- `--model`: Ollama model name (defaults to the `OLLAMA_MODEL` environment variable or `llama3.1:latest`).
- `--system-prompt`: Provide a custom system prompt for the host persona.
- `--list-models`: Print detected Ollama models and exit.

At any prompt you can type `ANSWER` to reveal the solution or `quit`/`exit` to leave the game.

## Docker Compose workflow

To build the shared image and bring both web apps online:

```bash
docker compose up --build
```

- `http://localhost:8000` → Expression Game Streamlit UI.
- `http://localhost:8001` → Trivia Pursuit Streamlit UI.

Both services use the same Docker image defined in `Dockerfile`, and each
exports port `8000` internally—Compose publishes them on different host ports.

## Individual Docker runs

Build the image manually if you want to run containers without Compose:

```bash
docker build -t expression-game .
```

Run the CLI host:

```bash
docker run --rm -it \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  expression-game \
  riddle-game --rounds 4 --difficulty easy
```

Run a Streamlit app by overriding the container command:

```bash
# Expression Game UI
docker run --rm -p 8000:8000 expression-game \
  streamlit run src/games/app/streamlit_app.py --server.address=0.0.0.0 --server.port=8000

# Trivia Pursuit UI
docker run --rm -p 8001:8000 expression-game \
  streamlit run src/games/app/streamlit_trivia.py --server.address=0.0.0.0 --server.port=8000
```

## Project layout

```
.
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── src/
│   └── games/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app/
│       │   ├── streamlit_app.py
│       │   └── streamlit_trivia.py
│       ├── cli.py
│       └── games/
│           ├── __init__.py
│           ├── _host.py
│           ├── riddle_game.py
│           └── trivia_game.py
├── README.md
└── README.Docker.md
```

All Python code lives under `src/games`, and dependencies are declared in
`pyproject.toml` so `uv` can manage installations and virtual environments
cleanly.

## Troubleshooting

- `Could not reach Ollama`: Ensure the Ollama server is running and reachable via
  the configured `OLLAMA_HOST`.
- No models listed: Run `ollama pull <model-name>` locally, then retry `--list-models`.
- Dependency cache issues: `uv cache clear` will reset UV's cached wheels and indices.
