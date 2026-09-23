"use client";

import { useEffect, useMemo, useState } from "react";

import type { DatasetContent, DatasetSummary } from "@/types/dashboard";

const QUESTIONS_PER_PAGE = 20;

type ExplorerProps = {
  datasets: DatasetSummary[];
};

async function loadContent(dataset: DatasetSummary): Promise<DatasetContent> {
  const url =
    dataset.source === "shared"
      ? dataset.dataUrl
      : `/api/datasets/${encodeURIComponent(dataset.id)}`;
  if (!url) throw new Error("Dataset content is unavailable.");
  const response = await fetch(url, { cache: dataset.source === "shared" ? "force-cache" : "no-store" });
  const body = (await response.json()) as DatasetContent & { error?: string };
  if (!response.ok) throw new Error(body.error ?? "Could not load this dataset.");
  return body;
}

export function ExplorerSection({ datasets }: ExplorerProps) {
  const [selectedId, setSelectedId] = useState(datasets[0]?.id ?? "");
  const [loaded, setLoaded] = useState<{
    datasetId: string;
    content: DatasetContent | null;
    error: string | null;
  }>({ datasetId: "", content: null, error: null });
  const [questionPage, setQuestionPage] = useState(0);
  const [inspectorIndex, setInspectorIndex] = useState(0);

  const selected =
    datasets.find((dataset) => dataset.id === selectedId) ?? datasets[0];
  const content =
    selected && loaded.datasetId === selected.id ? loaded.content : null;
  const loadError =
    selected && loaded.datasetId === selected.id ? loaded.error : null;
  const loading = Boolean(selected && loaded.datasetId !== selected.id);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    void loadContent(selected)
      .then((payload) => {
        if (!cancelled) {
          setLoaded({
            datasetId: selected.id,
            content: payload,
            error: null,
          });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoaded({
            datasetId: selected.id,
            content: null,
            error:
              error instanceof Error
                ? error.message
                : "Could not load this dataset.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  function chooseDataset(id: string) {
    setSelectedId(id);
    setQuestionPage(0);
    setInspectorIndex(0);
  }

  const totalPages = content
    ? Math.max(1, Math.ceil(content.questions.length / QUESTIONS_PER_PAGE))
    : 1;
  const visibleQuestions = useMemo(() => {
    if (!content) return [];
    const start = questionPage * QUESTIONS_PER_PAGE;
    return content.questions.slice(start, start + QUESTIONS_PER_PAGE).map((question, offset) => {
      const index = start + offset;
      const contextIndex = content.mostRelevant[index];
      return {
        index,
        question,
        context: content.contexts[contextIndex],
      };
    });
  }, [content, questionPage]);

  return (
    <div className="section-stack">
      <header className="page-heading">
        <p className="eyebrow">Dataset explorer</p>
        <h1>Look inside a retrieval dataset</h1>
        <p>
          A retrieval dataset pairs a set of notes with questions that each point
          to one correct note. Browse an example before building your own.
        </p>
      </header>

      <section className="content-card dataset-picker">
        <div>
          <label htmlFor="dataset-select">Choose a dataset</label>
          <p className="field-help">
            Start with a pre-loaded example, or return here after uploading your own.
          </p>
        </div>
        <div className="select-wrap">
          <select
            id="dataset-select"
            value={selected?.id ?? ""}
            onChange={(event) => chooseDataset(event.target.value)}
          >
            {datasets.map((dataset) => (
              <option key={`${dataset.source}-${dataset.id}`} value={dataset.id}>
                {dataset.name}
                {dataset.source === "private" ? " (yours)" : ""}
              </option>
            ))}
          </select>
        </div>
        {selected && (
          <div className="dataset-stats" aria-label="Dataset size">
            <div>
              <strong>{selected.questionCount ?? content?.questions.length ?? "—"}</strong>
              <span>questions</span>
            </div>
            <div>
              <strong>{selected.contextCount ?? content?.contexts.length ?? "—"}</strong>
              <span>notes</span>
            </div>
            <span className={`status-pill ${selected.source}`}>
              {selected.source === "shared" ? "Example" : "Private"}
            </span>
          </div>
        )}
      </section>

      {loading && (
        <div className="content-card loading-card" role="status">
          <span className="spinner" aria-hidden="true" />
          Loading the dataset…
        </div>
      )}
      {loadError && (
        <div className="message error" role="alert">
          <strong>We could not open this dataset.</strong>
          <span>{loadError}</span>
        </div>
      )}

      {content && (
        <>
          <section className="content-card">
            <div className="section-heading split-heading">
              <div>
                <p className="eyebrow">The answer key</p>
                <h2>Questions &amp; correct contexts</h2>
                <p>
                  The wording often differs on purpose: a good model should match
                  meaning, not just exact words.
                </p>
              </div>
              <span className="count-badge">{content.questions.length} pairs</span>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Question</th>
                    <th scope="col">Correct context</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleQuestions.map((row) => (
                    <tr key={row.index}>
                      <td className="id-cell">Q{row.index}</td>
                      <td>{row.question}</td>
                      <td>{row.context}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <button
                type="button"
                className="button quiet"
                disabled={questionPage === 0}
                onClick={() => setQuestionPage((page) => Math.max(0, page - 1))}
              >
                ← Previous
              </button>
              <span>
                Page {questionPage + 1} of {totalPages}
              </span>
              <button
                type="button"
                className="button quiet"
                disabled={questionPage + 1 >= totalPages}
                onClick={() =>
                  setQuestionPage((page) => Math.min(totalPages - 1, page + 1))
                }
              >
                Next →
              </button>
            </div>
          </section>

          <section className="content-card">
            <div className="section-heading split-heading">
              <div>
                <p className="eyebrow">The search space</p>
                <h2>Contexts</h2>
                <p>
                  These are the notes a model ranks for every question. As in the
                  original dashboard, the first 60 are shown for easier browsing.
                </p>
              </div>
              <span className="count-badge">
                Showing {Math.min(60, content.contexts.length)}
              </span>
            </div>
            <div className="table-scroll contexts-table">
              <table>
                <thead>
                  <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Context</th>
                  </tr>
                </thead>
                <tbody>
                  {content.contexts.slice(0, 60).map((context, index) => (
                    <tr key={index}>
                      <td className="id-cell">C{index}</td>
                      <td>{context}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="inspector-card">
            <div className="section-heading">
              <p className="eyebrow">Pair inspector</p>
              <h2>Zoom in on one match</h2>
              <p>
                Pick any question ID to see the human-labeled ground-truth note.
              </p>
            </div>
            <div className="inspector-control">
              <label htmlFor="question-id">Question ID</label>
              <input
                id="question-id"
                type="number"
                min={0}
                max={content.questions.length - 1}
                value={inspectorIndex}
                onChange={(event) => {
                  const value = Number(event.target.value);
                  setInspectorIndex(
                    Number.isFinite(value)
                      ? Math.min(content.questions.length - 1, Math.max(0, value))
                      : 0,
                  );
                }}
              />
              <span>
                of {content.questions.length - 1}
              </span>
            </div>
            <div className="pair-display">
              <article>
                <span className="pair-label">Question · Q{inspectorIndex}</span>
                <p>{content.questions[inspectorIndex]}</p>
              </article>
              <div className="pair-arrow" aria-hidden="true">→</div>
              <article className="ground-truth">
                <span className="pair-label">
                  Ground truth · C{content.mostRelevant[inspectorIndex]}
                </span>
                <p>
                  {content.contexts[content.mostRelevant[inspectorIndex]]}
                </p>
              </article>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
