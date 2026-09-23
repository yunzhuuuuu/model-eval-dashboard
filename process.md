# Model Evaluation Dashboard Rewrite Process

## Goal

Move the public application from Streamlit to a Vercel-hosted Next.js app while preserving the existing learning and evaluation experience. Uploaded evaluations run asynchronously through a scheduled Python worker.

## Feature-parity requirements

The rewrite is not complete until it preserves:

- Introduction and learning-objective content.
- Dataset Explorer for shared examples and the current user's datasets.
- Question/context tables and the pair inspector.
- Two-file CSV upload using `context.csv` and `qanda.csv`.
- Dataset naming, validation, private ownership, and overwrite behavior.
- Evaluation with Gemini, `all-mpnet-base-v2`, and `multi-qa-MiniLM-L6-dot-v1`.
- Recall@1, Recall@3, Mean Rank, and MRR with selectable columns and explanations.
- Side-by-side results for available datasets and models.

The new interface will additionally show job progress, recoverable failures, and completion status instead of blocking the page while embeddings are generated.

## Target architecture

- **Web:** Next.js with TypeScript, deployed through Vercel.
- **Uploads:** Private object storage, uploaded directly by the browser.
- **State:** Postgres records for anonymous sessions, datasets, jobs, progress, and results.
- **Evaluation:** Scheduled GitHub Actions worker with cached SentenceTransformer downloads and server-side Gemini credentials.
- **Privacy:** Signed anonymous-session cookie, unguessable identifiers, authorization checks, rate limits, and automatic data expiry.

## Stages

### Stage 1 - Repository safety and baseline

- [x] Inspect the existing Streamlit application and evaluation pipeline.
- [x] Confirm the destination GitHub repository is empty.
- [x] Record feature-parity requirements.
- [x] Expand ignore rules for secrets, generated artifacts, build output, and local deployment state.
- [x] Initialize Git and configure the GitHub SSH remote.
- [x] Review the exact first-commit file set before committing.

### Stage 2 - Tested evaluation core

- [x] Extract CSV parsing and validation from Streamlit.
- [x] Separate embedding, ranking, and metrics into framework-independent Python modules.
- [x] Add tests for validation and all four metrics.
- [x] Produce baseline results from the current implementation for parity comparison.

### Stage 3 - Durable job system

- [x] Define the database schema for sessions, datasets, jobs, and results.
- [x] Add private upload storage and retention rules.
- [x] Implement a restart-safe Python worker with progress and error reporting.
- [x] Add Gemini retry handling, rate limits, and job limits.

### Stage 4 - Next.js interface

- [x] Rebuild all four existing sections.
- [x] Implement direct CSV uploads and validation feedback.
- [x] Add job progress, completion, and failure views.
- [x] Recreate the dataset explorer and metric result tables.

### Stage 5 - Verification and release

- [x] Confirm numerical parity on shared datasets.
- [x] Test production session ownership boundaries and cross-origin rejection.
- [ ] Test concurrent job limits, retry failures, and expiry cleanup on the hosted worker.
- [x] Pass Python tests plus frontend lint, type-check, test, and production build.
- [x] Commit the reviewed source locally.
- [x] Push the reviewed source to GitHub.
- [x] Deploy and verify the Vercel production application.
- [ ] Connect GitHub worker secrets and verify a scheduled production run.

## Verification

Run the framework-independent unit and local parity tests with:

```sh
make test
```

Run the frontend lint, type-check, tests, and production build with:

```sh
npm run check:web
```

## Current findings

- Legacy generated data and embeddings account for approximately 632 MB and are excluded from Vercel with an explicit deployment allowlist.
- The preprocessed-data archive alone is approximately 230 MB and remains local-only.
- Upload and evaluation currently happen synchronously inside the Streamlit request.
- User isolation currently relies on a random session prefix in local filenames.
- The local folder did not contain Git metadata before Stage 1.
- The Gemini secret file is local-only and must never enter version control.
- The initial Postgres migration is applied to a free Neon database in `iad1`.
- A private Vercel Blob store is connected to production, preview, and development.
- The production site is live at `https://retrieval-model-lab.vercel.app`.
- A production smoke test created a session, uploaded both private CSVs, queued an evaluation, and completed all three model results through the worker.
- A second session could not list or fetch the first session's dataset, and a cross-origin write was rejected.
- A five-minute GitHub Actions workflow is implemented; repository secrets and a live scheduled run still need verification.

## Change log

- 2026-09-23: Created this process record and established feature parity as a release requirement.
- 2026-09-23: Completed Stage 2 with framework-independent CSV, embedding, ranking, and metric modules plus 12 passing tests.
- 2026-09-23: Completed Stage 3 with the Postgres job schema, private Blob adapter, restart-safe worker, cleanup and retry handling, memory-bounded scoring, and 21 passing tests.
- 2026-09-23: Completed Stage 4 with all four Next.js sections, signed anonymous sessions, direct private uploads, browser CSV validation, job polling, example-data export, selectable results, 5 frontend tests, and a passing production build.
- 2026-09-23: Released the Vercel web app with Neon and private Blob, verified production isolation, and completed a three-model production smoke evaluation through the worker.
- 2026-09-23: Added a bounded queue-drain mode and five-minute GitHub Actions worker workflow.
