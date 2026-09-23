BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE app_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash bytea NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    CHECK (expires_at > created_at)
);

CREATE TABLE datasets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES app_sessions(id) ON DELETE CASCADE,
    name text NOT NULL,
    name_key text NOT NULL,
    context_blob_url text NOT NULL,
    qanda_blob_url text NOT NULL,
    status text NOT NULL DEFAULT 'uploaded',
    context_count integer,
    question_count integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    deleted_at timestamptz,
    CHECK (char_length(name) BETWEEN 1 AND 120),
    CHECK (status IN ('uploaded', 'queued', 'processing', 'ready', 'failed')),
    CHECK (context_count IS NULL OR context_count > 0),
    CHECK (question_count IS NULL OR question_count > 0)
);

CREATE UNIQUE INDEX datasets_active_name
    ON datasets (session_id, name_key)
    WHERE deleted_at IS NULL;
CREATE INDEX datasets_expiry ON datasets (expires_at) WHERE deleted_at IS NULL;

CREATE TABLE evaluation_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id uuid NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'queued',
    stage text NOT NULL DEFAULT 'queued',
    progress_completed integer NOT NULL DEFAULT 0,
    progress_total integer NOT NULL DEFAULT 1,
    attempt_count integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 3,
    run_after timestamptz NOT NULL DEFAULT now(),
    lease_token uuid,
    lease_expires_at timestamptz,
    last_heartbeat_at timestamptz,
    error_code text,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    completed_at timestamptz,
    CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    CHECK (progress_completed >= 0),
    CHECK (progress_total > 0),
    CHECK (progress_completed <= progress_total),
    CHECK (attempt_count >= 0),
    CHECK (max_attempts BETWEEN 1 AND 10)
);

CREATE UNIQUE INDEX evaluation_jobs_one_active_per_dataset
    ON evaluation_jobs (dataset_id)
    WHERE status IN ('queued', 'running');
CREATE INDEX evaluation_jobs_claim
    ON evaluation_jobs (run_after, created_at)
    WHERE status IN ('queued', 'running');

CREATE TABLE evaluation_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL REFERENCES evaluation_jobs(id) ON DELETE CASCADE,
    dataset_id uuid NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    model_name text NOT NULL,
    metrics jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (job_id, model_name),
    CHECK (
        metrics ? 'Recall@1'
        AND metrics ? 'Recall@3'
        AND metrics ? 'Mean Rank'
        AND metrics ? 'MRR'
    )
);

CREATE TABLE session_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id uuid NOT NULL REFERENCES app_sessions(id) ON DELETE CASCADE,
    event_type text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (event_type IN ('evaluation_submitted'))
);

CREATE INDEX session_events_rate_limit
    ON session_events (session_id, event_type, created_at DESC);

CREATE TABLE blob_cleanup_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id uuid REFERENCES datasets(id) ON DELETE SET NULL,
    blob_url text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'pending',
    attempt_count integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 5,
    lease_token uuid,
    lease_expires_at timestamptz,
    run_after timestamptz NOT NULL DEFAULT now(),
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CHECK (status IN ('pending', 'running', 'deleted', 'failed')),
    CHECK (attempt_count >= 0),
    CHECK (max_attempts BETWEEN 1 AND 20)
);

CREATE INDEX blob_cleanup_claim
    ON blob_cleanup_requests (run_after, created_at)
    WHERE status IN ('pending', 'running');

CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER datasets_touch_updated_at
BEFORE UPDATE ON datasets
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER evaluation_jobs_touch_updated_at
BEFORE UPDATE ON evaluation_jobs
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TRIGGER blob_cleanup_touch_updated_at
BEFORE UPDATE ON blob_cleanup_requests
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE OR REPLACE FUNCTION enqueue_evaluation(
    p_session_id uuid,
    p_name text,
    p_name_key text,
    p_context_blob_url text,
    p_qanda_blob_url text,
    p_expires_at timestamptz,
    p_max_active_jobs integer DEFAULT 2,
    p_max_jobs_per_hour integer DEFAULT 5
)
RETURNS TABLE (dataset_id uuid, job_id uuid)
LANGUAGE plpgsql
AS $$
DECLARE
    v_dataset_id uuid;
    v_job_id uuid;
    v_active_jobs integer;
    v_recent_jobs integer;
    v_existing datasets%ROWTYPE;
BEGIN
    PERFORM 1
    FROM app_sessions
    WHERE id = p_session_id AND expires_at > now()
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'session is missing or expired' USING ERRCODE = 'P0001';
    END IF;

    SELECT count(*)
    INTO v_active_jobs
    FROM evaluation_jobs jobs
    JOIN datasets data ON data.id = jobs.dataset_id
    WHERE data.session_id = p_session_id
      AND data.deleted_at IS NULL
      AND jobs.status IN ('queued', 'running')
      AND data.name_key <> p_name_key;

    IF v_active_jobs >= p_max_active_jobs THEN
        RAISE EXCEPTION 'too many active evaluation jobs' USING ERRCODE = 'P0001';
    END IF;

    SELECT count(*)
    INTO v_recent_jobs
    FROM session_events
    WHERE session_id = p_session_id
      AND event_type = 'evaluation_submitted'
      AND created_at >= now() - interval '1 hour';

    IF v_recent_jobs >= p_max_jobs_per_hour THEN
        RAISE EXCEPTION 'hourly evaluation limit reached' USING ERRCODE = 'P0001';
    END IF;

    SELECT *
    INTO v_existing
    FROM datasets
    WHERE session_id = p_session_id
      AND name_key = p_name_key
      AND deleted_at IS NULL
    FOR UPDATE;

    IF FOUND THEN
        INSERT INTO blob_cleanup_requests (dataset_id, blob_url)
        VALUES
            (v_existing.id, v_existing.context_blob_url),
            (v_existing.id, v_existing.qanda_blob_url)
        ON CONFLICT (blob_url) DO NOTHING;

        UPDATE evaluation_jobs
        SET status = 'cancelled',
            stage = 'cancelled',
            lease_token = NULL,
            lease_expires_at = NULL,
            completed_at = now()
        WHERE evaluation_jobs.dataset_id = v_existing.id
          AND status IN ('queued', 'running');

        UPDATE datasets
        SET deleted_at = now()
        WHERE id = v_existing.id;
    END IF;

    INSERT INTO datasets (
        session_id,
        name,
        name_key,
        context_blob_url,
        qanda_blob_url,
        status,
        expires_at
    )
    VALUES (
        p_session_id,
        p_name,
        p_name_key,
        p_context_blob_url,
        p_qanda_blob_url,
        'queued',
        p_expires_at
    )
    RETURNING id INTO v_dataset_id;

    INSERT INTO evaluation_jobs (dataset_id)
    VALUES (v_dataset_id)
    RETURNING id INTO v_job_id;

    INSERT INTO session_events (session_id, event_type)
    VALUES (p_session_id, 'evaluation_submitted');

    RETURN QUERY SELECT v_dataset_id, v_job_id;
END;
$$;

CREATE OR REPLACE FUNCTION queue_expired_dataset_cleanup(
    p_batch_size integer DEFAULT 100
)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_dataset datasets%ROWTYPE;
    v_count integer := 0;
BEGIN
    FOR v_dataset IN
        SELECT *
        FROM datasets
        WHERE deleted_at IS NULL
          AND expires_at <= now()
        ORDER BY expires_at
        FOR UPDATE SKIP LOCKED
        LIMIT p_batch_size
    LOOP
        INSERT INTO blob_cleanup_requests (dataset_id, blob_url)
        VALUES
            (v_dataset.id, v_dataset.context_blob_url),
            (v_dataset.id, v_dataset.qanda_blob_url)
        ON CONFLICT (blob_url) DO NOTHING;

        UPDATE evaluation_jobs
        SET status = 'cancelled',
            stage = 'expired',
            lease_token = NULL,
            lease_expires_at = NULL,
            completed_at = now()
        WHERE dataset_id = v_dataset.id
          AND status IN ('queued', 'running');

        UPDATE datasets
        SET deleted_at = now()
        WHERE id = v_dataset.id;

        v_count := v_count + 1;
    END LOOP;

    DELETE FROM session_events
    WHERE created_at < now() - interval '24 hours';

    DELETE FROM app_sessions
    WHERE expires_at <= now()
      AND NOT EXISTS (
          SELECT 1 FROM datasets WHERE datasets.session_id = app_sessions.id
      );

    RETURN v_count;
END;
$$;

COMMIT;
