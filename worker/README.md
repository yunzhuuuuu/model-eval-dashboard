# Evaluation Worker

This service processes evaluation jobs created by the Vercel application. It is
a background worker, not a public web server.

## Responsibilities

1. Claim one queued job with a renewable database lease.
2. Download both CSVs from private Vercel Blob storage.
3. Validate and normalize the retrieval dataset.
4. Generate Gemini and SentenceTransformer embeddings.
5. Calculate Recall@1, Recall@3, Mean Rank, and MRR.
6. Save all model results and mark the job complete atomically.
7. Retry temporary failures and recover work whose previous lease expired.
8. Delete expired or replaced private uploads through the cleanup queue.

## Required services

- PostgreSQL from a Vercel Marketplace provider such as Neon or Supabase.
- A private Vercel Blob store.
- GitHub Actions or a persistent worker host capable of running the two local models.

Apply `migrations/001_initial.sql` to an empty PostgreSQL database before
starting either the web app or worker.

## Configuration

Copy the variable names from `.env.example` into GitHub repository secrets or
the worker host's secret manager. Never commit their real values.

The required variables are:

- `DATABASE_URL`
- `BLOB_READ_WRITE_TOKEN`
- `GEMINI_API_KEY`

## Run

For a configured local environment, run continuously with:

```sh
python -m worker
```

For a scheduled or one-shot environment, process the current queue and exit:

```sh
python -m worker --drain --max-items 10
```

The GitHub workflow runs this bounded mode every five minutes and caches model
downloads between runs. `worker.Dockerfile` remains available for a future
continuous background-worker service.
