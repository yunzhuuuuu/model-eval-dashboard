# Model Evaluation Dashboard Rewrite Process

## Goal

Move the public application from Streamlit to a Vercel-hosted Next.js app while preserving the existing learning and evaluation experience. Uploaded evaluations will run asynchronously through a persistent Python worker so the two local SentenceTransformer models can remain available.

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
- **Evaluation:** Persistent Python worker with cached SentenceTransformer models and server-side Gemini credentials.
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

- [ ] Define the database schema for sessions, datasets, jobs, and results.
- [ ] Add private upload storage and retention rules.
- [ ] Implement a restart-safe Python worker with progress and error reporting.
- [ ] Add Gemini retry handling, rate limits, and job limits.

### Stage 4 - Next.js interface

- [ ] Rebuild all four existing sections.
- [ ] Implement direct CSV uploads and validation feedback.
- [ ] Add job progress, completion, and failure views.
- [ ] Recreate the dataset explorer and metric result tables.

### Stage 5 - Verification and release

- [ ] Confirm numerical parity on shared datasets.
- [ ] Test concurrent users, ownership boundaries, failures, and cleanup.
- [ ] Pass Python tests plus frontend lint, type-check, test, and production build.
- [ ] Commit and push the reviewed source to GitHub.
- [ ] Deploy a Vercel preview, verify it, and promote it to production.

## Verification

Run the framework-independent unit and local parity tests with:

```sh
make test
```

## Current findings

- The current folder is approximately 632 MB, mostly generated data and embeddings.
- The preprocessed-data archive alone is approximately 230 MB.
- Upload and evaluation currently happen synchronously inside the Streamlit request.
- User isolation currently relies on a random session prefix in local filenames.
- The local folder did not contain Git metadata before Stage 1.
- The Gemini secret file is local-only and must never enter version control.

## Change log

- 2026-09-23: Created this process record and established feature parity as a release requirement.
- 2026-09-23: Completed Stage 2 with framework-independent CSV, embedding, ranking, and metric modules plus 12 passing tests.
