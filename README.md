# Expression Game

An interactive CLI riddle host that turns your locally running Ollama models
into a playful guessing game. The app poses a riddle, offers hints, and lets you
ask for the answer whenever you are ready.

## Features

- Play short riddle sessions with configurable round count and difficulty.
- Request hints or reveal the answer in-game by typing `ANSWER`.
- Works with any Ollama chat model you have pulled locally.
- Quickly inspect available models with the `--list-models` flag.

## Prerequisites

- A running [Ollama](https://ollama.com) server with at least one chat-capable
  model (for example `ollama pull llama3.1`).
- [uv](https://github.com/astral-sh/uv) for local installs and virtualenv
  management (optional but recommended).
- Docker (optional) if you prefer containerised execution.

## Run with uv

```bash
# Install dependencies into an isolated UV environment
uv pip install .

# Start the interactive riddle game
uv run riddle-game --rounds 5 --difficulty medium
```

### CLI options

- `--rounds`: Number of guesses the player gets before the host offers the answer (default `5`).
- `--difficulty`: One of `easy`, `medium`, or `hard` (default `medium`).
- `--model`: Ollama model name (defaults to the `OLLAMA_MODEL` environment variable or `llama3.1:latest`).
- `--system-prompt`: Provide a custom system prompt for the host persona.
- `--list-models`: Print detected Ollama models and exit.

At any prompt you can type `ANSWER` to reveal the solution or `quit`/`exit` to leave the game.

## Run directly with Python

If you already have dependencies available, you can invoke the module entry point:

```bash
python -m games --difficulty hard --rounds 3
```

Set `OLLAMA_MODEL` to change the default model without passing `--model` every time.

## Docker usage

```bash
# Build the container image
docker build -t expression-game .

# Run it against your host Ollama instance (override the command to pick the CLI)
docker run --rm -it \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  expression-game \
  riddle-game --rounds 4 --difficulty easy
```

You can forward any of the CLI flags used in the local workflow.

## Project layout

```
.
├── Dockerfile
├── pyproject.toml
├── src/
│   └── games/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── game.py
│       └── games/
│           ├── __init__.py
│           ├── _host.py
│           └── riddle_game.py
└── README.md
```

All Python code lives under `src/games`, and dependencies are declared in `pyproject.toml`
so `uv` can manage installations and virtual environments cleanly.

## Troubleshooting

- `Could not reach Ollama`: ensure the Ollama server is running and reachable via
  the configured `OLLAMA_HOST`.
- No models listed: run `ollama pull <model-name>` locally, then retry `--list-models`.
- Dependency cache issues: `uv cache clear` will reset UV's cached wheels and indices.
