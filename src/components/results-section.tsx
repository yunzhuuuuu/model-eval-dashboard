"use client";

import { useState } from "react";

import { METRIC_HELP, MODEL_LABELS } from "@/lib/shared";
import {
  METRICS,
  MODELS,
  type DatasetSummary,
  type MetricName,
} from "@/types/dashboard";

type ResultsProps = {
  datasets: DatasetSummary[];
  isRefreshing: boolean;
  onRefresh: () => Promise<void>;
  onUpload: () => void;
};

function displayStage(stage: string): string {
  const labels: Record<string, string> = {
    queued: "Waiting for a worker",
    starting: "Starting evaluation",
    downloading_uploads: "Reading your files",
    validating_dataset: "Checking the dataset",
    embedding_gemini: "Running Gemini",
    evaluated_gemini: "Gemini complete",
    "embedding_all-mpnet-base-v2": "Running all-mpnet",
    "evaluated_all-mpnet-base-v2": "all-mpnet complete",
    "embedding_multi-qa-MiniLM-L6-dot-v1": "Running MiniLM",
    "evaluated_multi-qa-MiniLM-L6-dot-v1": "MiniLM complete",
    retry_scheduled: "Retry scheduled",
    completed: "Evaluation complete",
    failed: "Evaluation failed",
  };
  return labels[stage] ?? stage.replaceAll("_", " ");
}

function JobCard({ dataset }: { dataset: DatasetSummary }) {
  const job = dataset.job;
  if (!job || dataset.source === "shared") return null;
  const percent = Math.min(
    100,
    Math.round((job.progressCompleted / Math.max(1, job.progressTotal)) * 100),
  );
  if (job.status === "completed") return null;

  return (
    <div className={`job-card ${job.status}`}>
      <div className="job-topline">
        <div>
          <span className="status-dot" aria-hidden="true" />
          <strong>{dataset.name}</strong>
        </div>
        <span className="status-pill">{displayStage(job.stage)}</span>
      </div>
      {job.status === "failed" ? (
        <div className="job-error" role="alert">
          <p>{job.errorMessage ?? "The evaluation could not be completed."}</p>
          <span>
            Attempt {job.attemptCount} of {job.maxAttempts}
          </span>
        </div>
      ) : (
        <>
          <div className="progress-label">
            <span>{displayStage(job.stage)}</span>
            <span>{percent}%</span>
          </div>
          <progress max={100} value={percent}>
            {percent}%
          </progress>
          <p className="job-caption">
            You can leave this page. This evaluation continues in the background.
          </p>
        </>
      )}
    </div>
  );
}

function metricValue(value: number | undefined, metric: MetricName): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  return metric === "Mean Rank" ? value.toFixed(2) : value.toFixed(3);
}

export function ResultsSection({
  datasets,
  isRefreshing,
  onRefresh,
  onUpload,
}: ResultsProps) {
  const [selectedMetrics, setSelectedMetrics] = useState<MetricName[]>([
    ...METRICS,
  ]);

  function toggleMetric(metric: MetricName) {
    setSelectedMetrics((current) =>
      current.includes(metric)
        ? current.filter((item) => item !== metric)
        : [...current, metric],
    );
  }

  const activeJobs = datasets.filter(
    (dataset) =>
      dataset.source === "private" &&
      dataset.job &&
      dataset.job.status !== "completed",
  );
  const resultDatasets = datasets.filter(
    (dataset) => dataset.results.length > 0 || dataset.source === "shared",
  );

  return (
    <div className="section-stack">
      <header className="page-heading results-heading">
        <div>
          <p className="eyebrow">Evaluation results</p>
          <h1>Compare how each model retrieves</h1>
          <p>
            Choose the columns that matter to you, then compare models across
            example datasets and your own evaluations.
          </p>
        </div>
        <button
          type="button"
          className="button quiet refresh-button"
          disabled={isRefreshing}
          onClick={() => void onRefresh()}
        >
          <span className={isRefreshing ? "spin" : ""} aria-hidden="true">↻</span>
          {isRefreshing ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {activeJobs.length > 0 && (
        <section className="jobs-section" aria-labelledby="active-jobs-title">
          <div className="section-heading">
            <p className="eyebrow">Live evaluations</p>
            <h2 id="active-jobs-title">In progress</h2>
          </div>
          <div className="jobs-grid">
            {activeJobs.map((dataset) => (
              <JobCard key={dataset.id} dataset={dataset} />
            ))}
          </div>
        </section>
      )}

      <section className="content-card metric-guide">
        <div className="section-heading">
          <p className="eyebrow">Choose your lens</p>
          <h2>Metrics to display</h2>
        </div>
        <div className="metric-options">
          {METRICS.map((metric) => (
            <label key={metric} className={selectedMetrics.includes(metric) ? "selected" : ""}>
              <input
                type="checkbox"
                checked={selectedMetrics.includes(metric)}
                onChange={() => toggleMetric(metric)}
              />
              <span>
                <strong>{metric}</strong>
                <small>{METRIC_HELP[metric]}</small>
              </span>
            </label>
          ))}
        </div>
        <div className="metric-note">
          <strong>Why these four?</strong>
          <p>
            Every question has exactly one correct note. That makes Hit Rate@k
            identical to Recall@k, Precision@k a scaled version of Recall@k, and
            Mean Average Precision equivalent to MRR. Those extra names would not
            add new information here.
          </p>
          <a
            href="https://medium.com/@er111/recall-k-versus-mrr-918da3264f2a?sharedUserId=er111"
            target="_blank"
            rel="noreferrer"
          >
            Learn more about Recall and MRR
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </div>
      </section>

      {selectedMetrics.length === 0 ? (
        <div className="message warning" role="status">
          <strong>Select at least one metric.</strong>
          <span>The comparison tables will appear here.</span>
        </div>
      ) : (
        <section className="results-stack" aria-label="Model comparison tables">
          {resultDatasets.map((dataset) => (
            <article className="result-card" key={`${dataset.source}-${dataset.id}`}>
              <div className="result-card-header">
                <div>
                  <span className={`status-pill ${dataset.source}`}>
                    {dataset.source === "shared" ? "Example" : "Yours"}
                  </span>
                  <h2>{dataset.name}</h2>
                </div>
                <div className="result-counts">
                  <span>{dataset.questionCount?.toLocaleString() ?? "—"} questions</span>
                  <span>{dataset.contextCount?.toLocaleString() ?? "—"} notes</span>
                </div>
              </div>
              <div className="table-scroll">
                <table className="results-table">
                  <thead>
                    <tr>
                      <th scope="col">Model</th>
                      {selectedMetrics.map((metric) => (
                        <th scope="col" key={metric} title={METRIC_HELP[metric]}>
                          {metric}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {MODELS.map((model) => {
                      const result = dataset.results.find(
                        (item) => item.modelName === model,
                      );
                      return (
                        <tr key={model}>
                          <th scope="row">
                            <span className="model-mark" aria-hidden="true">
                              {model === "gemini_3072"
                                ? "G"
                                : model.startsWith("all")
                                  ? "M"
                                  : "L"}
                            </span>
                            <span>
                              {MODEL_LABELS[model]}
                              {model === "all-mpnet-base-v2" && (
                                <small>EchoMinds model</small>
                              )}
                            </span>
                          </th>
                          {selectedMetrics.map((metric) => (
                            <td key={metric}>
                              {metricValue(result?.metrics[metric], metric)}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {dataset.source === "private" && dataset.expiresAt && (
                <p className="expiry-note">
                  Private files expire{" "}
                  {new Date(dataset.expiresAt).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                  .
                </p>
              )}
            </article>
          ))}
        </section>
      )}

      {datasets.filter((dataset) => dataset.source === "private").length === 0 && (
        <section className="empty-callout">
          <div>
            <p className="eyebrow">Ready to compare your own?</p>
            <h2>Add a dataset to these tables</h2>
            <p>
              Upload two CSV files and the worker will evaluate all three models
              in the background.
            </p>
          </div>
          <button type="button" className="button primary" onClick={onUpload}>
            Upload a dataset <span aria-hidden="true">→</span>
          </button>
        </section>
      )}

      <section className="content-card models-guide">
        <div className="section-heading">
          <p className="eyebrow">The contenders</p>
          <h2>Three ways to represent meaning</h2>
        </div>
        <div className="model-grid">
          <article>
            <span className="model-mark gemini">G</span>
            <h3>Gemini embedding-001</h3>
            <p>
              Google&apos;s hosted embedding model. It captures nuanced meaning
              but needs an API call for each batch.
            </p>
          </article>
          <article>
            <span className="model-mark">M</span>
            <h3>all-mpnet-base-v2</h3>
            <p>
              A broad, general-purpose Sentence Transformers model—the same model
              used by EchoMinds.
            </p>
          </article>
          <article>
            <span className="model-mark minilm">L</span>
            <h3>multi-qa-MiniLM-L6</h3>
            <p>
              A smaller, faster model trained for question-answer retrieval. It
              trades some capacity for speed.
            </p>
          </article>
        </div>
      </section>
    </div>
  );
}
