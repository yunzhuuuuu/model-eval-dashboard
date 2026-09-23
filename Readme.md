# Retrieval Model Evaluation Dashboard

A website for learning how retrieval-based machine learning systems work, hands-on. Students will:

1. **Learn about sentence embeddings and retrieval models** — how a machine learning model converts text into numerical vectors, and how similarity between those vectors is used to find the right answer to a question.
2. **Design their own dataset of notes** — design notes that users might jot down. Each note is paired with a question someone might later ask to look that note back up, phrased differently than the note itself. This mirrors the real dataset structure used by EchoMinds, a note-taking app built by Olin students to support people who are blind or visually impaired (more information on the website).
3. **Learn evaluation metrics and evaluate ML models** — apply metrics like Recall@1, Recall@3, Mean Rank, and MRR to measure how well different embedding models retrieve the correct note for a given question, using both pre-loaded example datasets and the dataset students design themselves.

## Features

- **Dataset Explorer** — browse pre-loaded example datasets (SQuAD, and the Assistive Technology dataset used to build EchoMinds), inspecting individual question-note pairs
- **Upload your own dataset** — design a note-taking scenario, write or LLM-generate notes and matching questions, and upload two CSVs to have them automatically embedded
- **Compare 3 embedding models** — `gemini-embedding-001`, `all-mpnet-base-v2`, and `multi-qa-MiniLM-L6-dot-v1`, evaluated side by side
- **Multiple evaluation metrics** — Recall@1, Recall@3, Mean Rank, and MRR, with plain-language explanations and column tooltips built into the app

## Architecture

- **Next.js web app:** the student interface and authenticated API routes, designed for Vercel.
- **Postgres:** anonymous sessions, private dataset records, job progress, and results.
- **Vercel Blob:** direct browser uploads to private object storage.
- **Python worker:** scheduled GitHub Actions job for Gemini and the two SentenceTransformer models.
- **Static examples:** the existing SQuAD, Assistive Technology, and Cooking datasets ship with the web app.

The original Streamlit app remains in `app.py` as a reference while the new release is verified.

The production web app is available at <https://retrieval-model-lab.vercel.app>.

## Run the web app locally

1. Install the Node dependencies:

   ```sh
   npm ci
   ```

2. Copy `.env.example` to `.env.local` and provide:

   - `DATABASE_URL` for a Postgres database.
   - `SESSION_SECRET` with at least 32 random characters.
   - `BLOB_READ_WRITE_TOKEN` for a private Vercel Blob store.

   Never commit the populated environment file.

3. Apply `migrations/001_initial.sql` to the database.

4. Start the site:

   ```sh
   npm run dev
   ```

The interface is available at `http://localhost:3000`. The preloaded examples work without private storage; uploads require the database and Blob settings above.

## Run the evaluation worker

The worker needs the same `DATABASE_URL` and `BLOB_READ_WRITE_TOKEN`, plus a server-side `GEMINI_API_KEY`.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install torch==2.14.0+cpu --index-url https://download.pytorch.org/whl/cpu
pip install -r worker-requirements.txt
python -m worker
```

The worker is intentionally separate from Vercel. Run `python -m worker` for
continuous local polling, or `python -m worker --drain` to process the current
queue and exit, as the scheduled GitHub workflow does.

## Verification

```sh
make test
npm run lint
npm run typecheck
npm run test:web
npm run build
```

Regenerate the deployable example JSON after changing the local example data or embeddings:

```sh
npm run export:shared
```

## Deploy

1. Import this repository into Vercel.
2. Connect a Marketplace Postgres provider and a **private** Vercel Blob store.
3. Add `DATABASE_URL`, `SESSION_SECRET`, and `BLOB_READ_WRITE_TOKEN` to the Vercel project.
4. Apply the database migration.
5. Add the worker variables as GitHub repository secrets and enable the scheduled workflow.
6. Verify a preview deployment before promoting it to production.

The Vercel web app, free Neon database, private Blob store, migration, and a
complete three-model smoke evaluation are verified. The scheduled worker
workflow runs every five minutes; evaluations can wait for the next scheduled
run before processing begins.

The deployment and live service checks are tracked in `process.md`.
