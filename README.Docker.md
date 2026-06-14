### Building and running your application

Build the shared application image and launch both Streamlit apps:

```bash
docker compose up --build
```

- http://localhost:8000 — Expression Game (riddle Streamlit UI)
- http://localhost:8001 — Trivia Pursuit (trivia Streamlit UI)

Use `docker compose up server` or `docker compose up trivia` if you want to run
just one service at a time.

### Deploying your application to the cloud

First, build your image, e.g.: `docker build -t myapp .`.
If your cloud uses a different CPU architecture than your development
machine (e.g., you are on a Mac M1 and your cloud provider is amd64),
you'll want to build the image for that platform, e.g.:
`docker build --platform=linux/amd64 -t myapp .`.

Then, push it to your registry, e.g. `docker push myregistry.com/myapp`.

Consult Docker's [getting started](https://docs.docker.com/go/get-started-sharing/)
docs for more detail on building and pushing.

### Running containers manually

Each Streamlit app can be started from the built image by overriding the command:

```bash
# Expression Game UI
docker run --rm -p 8000:8000 myapp \
  streamlit run src/games/app/streamlit_app.py --server.address=0.0.0.0 --server.port=8000

# Trivia Pursuit UI
docker run --rm -p 8001:8000 myapp \
  streamlit run src/games/app/streamlit_trivia.py --server.address=0.0.0.0 --server.port=8000
```

### References
* [Docker's Python guide](https://docs.docker.com/language/python/)
