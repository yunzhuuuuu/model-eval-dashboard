"use client";

import { upload } from "@vercel/blob/client";
import Image from "next/image";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { validateDatasetFiles } from "@/lib/csv";
import {
  cleanDatasetName,
  datasetNameKey,
  validateDatasetName,
} from "@/lib/names";
import type {
  DatasetContent,
  DatasetSummary,
  SessionInfo,
} from "@/types/dashboard";

type UploadProps = {
  session: SessionInfo | null;
  datasets: DatasetSummary[];
  onComplete: () => Promise<void>;
};

type UploadState = "idle" | "uploading" | "queued" | "error";

export function UploadSection({
  session,
  datasets,
  onComplete,
}: UploadProps) {
  const [name, setName] = useState("");
  const [contextFile, setContextFile] = useState<File | null>(null);
  const [qandaFile, setQandaFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<DatasetContent | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [confirmOverwrite, setConfirmOverwrite] = useState(false);

  useEffect(() => {
    if (!contextFile || !qandaFile) return;
    let cancelled = false;
    void validateDatasetFiles(contextFile, qandaFile)
      .then((dataset) => {
        if (!cancelled) {
          setPreview(dataset);
          setValidationMessage(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setPreview(null);
          setValidationMessage(
            error instanceof Error ? error.message : "The CSV files are not valid.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [contextFile, qandaFile]);

  function chooseContextFile(file: File | null) {
    setContextFile(file);
    setPreview(null);
    setValidationMessage(null);
  }

  function chooseQandaFile(file: File | null) {
    setQandaFile(file);
    setPreview(null);
    setValidationMessage(null);
  }

  const existingDataset = useMemo(() => {
    const key = datasetNameKey(name);
    if (!key) return null;
    return datasets.find((dataset) => datasetNameKey(dataset.name) === key) ?? null;
  }, [datasets, name]);

  async function cleanupUploads(urls: string[]) {
    if (urls.length === 0) return;
    try {
      await fetch("/api/uploads", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls }),
      });
    } catch {
      // The server-side retention cleanup remains a fallback.
    }
  }

  async function submit(overwriteAccepted: boolean) {
    const nameError = validateDatasetName(name);
    if (nameError) {
      setState("error");
      setStatusMessage(nameError);
      return;
    }
    if (!contextFile || !qandaFile) {
      setState("error");
      setStatusMessage("Please choose both context.csv and qanda.csv.");
      return;
    }
    if (!preview) {
      setState("error");
      setStatusMessage(
        validationMessage ?? "Wait for both CSV files to finish validation.",
      );
      return;
    }
    if (!session) {
      setState("error");
      setStatusMessage(
        "Private uploads are not connected yet. Configure the deployment services and refresh.",
      );
      return;
    }
    if (existingDataset && !overwriteAccepted) {
      setConfirmOverwrite(true);
      return;
    }

    setConfirmOverwrite(false);
    setState("uploading");
    setProgress(0);
    setStatusMessage("Uploading context.csv securely…");
    const uploadedUrls: string[] = [];

    try {
      const contextBlob = await upload(
        `${session.id}/uploads/${crypto.randomUUID()}-context.csv`,
        contextFile,
        {
          access: "private",
          contentType: "text/csv",
          handleUploadUrl: "/api/uploads",
          clientPayload: JSON.stringify({ role: "context" }),
          onUploadProgress: ({ percentage }) => setProgress(percentage / 2),
        },
      );
      uploadedUrls.push(contextBlob.url);

      setStatusMessage("Uploading qanda.csv securely…");
      const qandaBlob = await upload(
        `${session.id}/uploads/${crypto.randomUUID()}-qanda.csv`,
        qandaFile,
        {
          access: "private",
          contentType: "text/csv",
          handleUploadUrl: "/api/uploads",
          clientPayload: JSON.stringify({ role: "qanda" }),
          onUploadProgress: ({ percentage }) =>
            setProgress(50 + percentage / 2),
        },
      );
      uploadedUrls.push(qandaBlob.url);

      setStatusMessage("Adding your evaluation to the queue…");
      const response = await fetch("/api/datasets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: cleanDatasetName(name),
          contextBlobUrl: contextBlob.url,
          qandaBlobUrl: qandaBlob.url,
        }),
      });
      const body = (await response.json()) as { error?: string };
      if (!response.ok) throw new Error(body.error ?? "Could not queue the evaluation.");

      setState("queued");
      setProgress(100);
      setStatusMessage(
        `“${cleanDatasetName(name)}” is queued. You can follow its progress in Evaluation Results.`,
      );
      setName("");
      setContextFile(null);
      setQandaFile(null);
      setPreview(null);
      const contextInput = document.querySelector<HTMLInputElement>("#context-file");
      const qandaInput = document.querySelector<HTMLInputElement>("#qanda-file");
      if (contextInput) contextInput.value = "";
      if (qandaInput) qandaInput.value = "";
      await onComplete();
    } catch (error) {
      await cleanupUploads(uploadedUrls);
      setState("error");
      setStatusMessage(
        error instanceof Error ? error.message : "The upload could not be completed.",
      );
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit(false);
  }

  return (
    <div className="section-stack">
      <header className="page-heading">
        <p className="eyebrow">Create your dataset</p>
        <h1>Turn your notes into a retrieval test</h1>
        <p>
          Make two CSV files in Excel or Google Sheets. We validate them in your
          browser before anything is uploaded.
        </p>
      </header>

      <section className="requirements-grid">
        <article className="content-card requirement-card">
          <div className="file-number">1</div>
          <div>
            <p className="eyebrow">context.csv</p>
            <h2>Your notes</h2>
            <p>
              One note per row under a single column named <code>Note</code>.
              Every note must be unique.
            </p>
          </div>
          <Image
            src="/examples/contexts.png"
            alt='Example spreadsheet with a "Note" header and one note per row'
            width={694}
            height={324}
          />
        </article>
        <article className="content-card requirement-card">
          <div className="file-number">2</div>
          <div>
            <p className="eyebrow">qanda.csv</p>
            <h2>Questions &amp; matches</h2>
            <p>
              Use columns named <code>Question</code> and <code>Relevant Note</code>.
              The relevant note must exactly match one from context.csv.
            </p>
          </div>
          <Image
            src="/examples/qanda.png"
            alt='Example spreadsheet with "Question" and "Relevant Note" headers'
            width={1330}
            height={419}
          />
        </article>
      </section>

      <section className="content-card prompt-card">
        <details>
          <summary>
            <span>
              <span className="eyebrow">Optional helper</span>
              A prompt for generating a practice dataset
            </span>
            <span aria-hidden="true">+</span>
          </summary>
          <div className="prompt-copy">
            <p>
              I&apos;m building a test dataset for a note-taking app&apos;s search
              feature. Generate [NUMBER] short notes about [YOUR TOPIC]. Each
              note should be 1–3 sentences and sound like something a real person
              would jot down.
            </p>
            <p>
              Then choose [NUMBER] notes and write one question for each. Rephrase
              the idea instead of copying the note&apos;s exact words. Output two
              lists: notes, then questions with their exactly matching notes.
            </p>
          </div>
        </details>
      </section>

      <section className="content-card upload-card">
        <div className="section-heading">
          <p className="eyebrow">Upload &amp; evaluate</p>
          <h2>Check your two files</h2>
          <p>
            Recommended: fewer than 1,000 notes and 200 questions. The hard limit
            is 10,000 rows per file and 10 MB per file.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="dataset-name">Dataset name</label>
            <input
              id="dataset-name"
              value={name}
              maxLength={120}
              placeholder="e.g. Biology study notes"
              onChange={(event) => {
                setName(event.target.value);
                setConfirmOverwrite(false);
              }}
            />
            <span className="field-help">A short name only you will see.</span>
          </div>

          <div className="file-grid">
            <label className={`file-drop ${contextFile ? "has-file" : ""}`}>
              <input
                id="context-file"
                type="file"
                accept=".csv,text/csv"
                onChange={(event) =>
                  chooseContextFile(event.target.files?.[0] ?? null)
                }
              />
              <span className="file-icon" aria-hidden="true">N</span>
              <strong>{contextFile?.name ?? "Choose context.csv"}</strong>
              <small>
                {contextFile
                  ? `${(contextFile.size / 1024).toFixed(1)} KB`
                  : "One column: Note"}
              </small>
            </label>
            <label className={`file-drop ${qandaFile ? "has-file" : ""}`}>
              <input
                id="qanda-file"
                type="file"
                accept=".csv,text/csv"
                onChange={(event) =>
                  chooseQandaFile(event.target.files?.[0] ?? null)
                }
              />
              <span className="file-icon" aria-hidden="true">Q</span>
              <strong>{qandaFile?.name ?? "Choose qanda.csv"}</strong>
              <small>
                {qandaFile
                  ? `${(qandaFile.size / 1024).toFixed(1)} KB`
                  : "Two columns: Question, Relevant Note"}
              </small>
            </label>
          </div>

          {preview && (
            <div className="message success" role="status">
              <strong>Files look good.</strong>
              <span>
                {preview.contexts.length.toLocaleString()} notes ·{" "}
                {preview.questions.length.toLocaleString()} questions · all
                relevant notes matched
              </span>
            </div>
          )}
          {validationMessage && (
            <div className="message error" role="alert">
              <strong>Please fix one thing.</strong>
              <span>{validationMessage}</span>
            </div>
          )}
          {confirmOverwrite && existingDataset && (
            <div className="overwrite-panel" role="alert">
              <div>
                <strong>Replace “{existingDataset.name}”?</strong>
                <p>
                  Its current files and results will be removed after the new
                  evaluation is queued.
                </p>
              </div>
              <div>
                <button
                  type="button"
                  className="button danger"
                  onClick={() => void submit(true)}
                >
                  Yes, replace it
                </button>
                <button
                  type="button"
                  className="button quiet"
                  onClick={() => setConfirmOverwrite(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {(state === "uploading" || state === "queued") && (
            <div className="upload-progress" role="status">
              <div>
                <strong>{statusMessage}</strong>
                <span>{Math.round(progress)}%</span>
              </div>
              <progress max={100} value={progress}>
                {Math.round(progress)}%
              </progress>
            </div>
          )}
          {state === "error" && statusMessage && (
            <div className="message error" role="alert">
              <strong>Upload not completed.</strong>
              <span>{statusMessage}</span>
            </div>
          )}

          <button
            className="button primary submit-button"
            type="submit"
            disabled={state === "uploading" || !preview}
          >
            {state === "uploading" ? "Uploading…" : "Save dataset & evaluate"}
            <span aria-hidden="true">→</span>
          </button>
        </form>
      </section>
    </div>
  );
}
