"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ExplorerSection } from "@/components/explorer-section";
import { IntroductionSection } from "@/components/introduction-section";
import { ResultsSection } from "@/components/results-section";
import { UploadSection } from "@/components/upload-section";
import { SHARED_DATASETS } from "@/lib/shared";
import type {
  DatasetSummary,
  ModelResult,
  SessionInfo,
} from "@/types/dashboard";

type SectionId = "introduction" | "explorer" | "upload" | "results";

const SECTIONS: { id: SectionId; label: string; number: string }[] = [
  { id: "introduction", label: "Introduction", number: "01" },
  { id: "explorer", label: "Dataset Explorer", number: "02" },
  { id: "upload", label: "Upload Dataset", number: "03" },
  { id: "results", label: "Evaluation Results", number: "04" },
];

type SharedResults = Record<string, ModelResult[]>;

async function responseJson<T>(response: Response): Promise<T> {
  const body = (await response.json()) as T & { error?: string };
  if (!response.ok) {
    throw new Error(body.error ?? "Request failed.");
  }
  return body;
}

export function Dashboard() {
  const [activeSection, setActiveSection] =
    useState<SectionId>("introduction");
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [privateDatasets, setPrivateDatasets] = useState<DatasetSummary[]>([]);
  const [sharedDatasets, setSharedDatasets] =
    useState<DatasetSummary[]>(SHARED_DATASETS);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshDatasets = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch("/api/datasets", { cache: "no-store" });
      const payload = await responseJson<{ datasets: DatasetSummary[] }>(response);
      setPrivateDatasets(payload.datasets);
    } catch {
      // Upload-specific guidance is shown in the upload section.
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function start() {
      try {
        const resultsResponse = await fetch("/data/shared-results.json");
        const resultsPayload = await responseJson<SharedResults>(resultsResponse);
        if (!cancelled) {
          setSharedDatasets((current) =>
            current.map((dataset) => ({
              ...dataset,
              results: resultsPayload[dataset.id] ?? [],
            })),
          );
        }
      } catch {
        // The datasets remain explorable even if their precomputed scores fail to load.
      }

      try {
        const sessionResponse = await fetch("/api/session", { method: "POST" });
        const sessionPayload = await responseJson<SessionInfo>(sessionResponse);
        if (cancelled) return;
        setSession(sessionPayload);
        await refreshDatasets();
      } catch {
        // Examples remain available; upload-specific guidance appears when needed.
      }
    }
    void start();
    return () => {
      cancelled = true;
    };
  }, [refreshDatasets]);

  const hasActiveJobs = privateDatasets.some((dataset) =>
    dataset.job && ["queued", "running"].includes(dataset.job.status),
  );

  useEffect(() => {
    if (!session || !hasActiveJobs) return;
    const timer = window.setInterval(() => {
      void refreshDatasets();
    }, 4000);
    return () => window.clearInterval(timer);
  }, [hasActiveJobs, refreshDatasets, session]);

  const datasets = useMemo(
    () => [...sharedDatasets, ...privateDatasets],
    [privateDatasets, sharedDatasets],
  );

  function navigate(section: SectionId) {
    setActiveSection(section);
    window.requestAnimationFrame(() => {
      document.querySelector("main")?.focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  async function handleUploadComplete() {
    await refreshDatasets();
    navigate("results");
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#main" aria-label="Retrieval Lab home">
          <span className="brand-mark" aria-hidden="true">
            RL
          </span>
          <span>
            <strong>Retrieval Lab</strong>
            <small>Model evaluation studio</small>
          </span>
        </a>
      </header>

      <div className="workspace">
        <nav className="top-tabs" aria-label="Dashboard sections">
          <div className="section-nav" role="tablist" aria-orientation="horizontal">
            {SECTIONS.map((section) => (
              <button
                id={`tab-${section.id}`}
                type="button"
                role="tab"
                aria-selected={activeSection === section.id}
                aria-controls={`panel-${section.id}`}
                key={section.id}
                className={activeSection === section.id ? "active" : ""}
                onClick={() => navigate(section.id)}
              >
                <span>{section.number}</span>
                {section.label}
              </button>
            ))}
          </div>
        </nav>

        <main id="main" tabIndex={-1}>
          <section
            id={`panel-${activeSection}`}
            role="tabpanel"
            aria-labelledby={`tab-${activeSection}`}
          >
            {activeSection === "introduction" && (
              <IntroductionSection onContinue={() => navigate("explorer")} />
            )}
            {activeSection === "explorer" && (
              <ExplorerSection datasets={datasets} />
            )}
            {activeSection === "upload" && (
              <UploadSection
                session={session}
                datasets={privateDatasets}
                onComplete={handleUploadComplete}
              />
            )}
            {activeSection === "results" && (
              <ResultsSection
                datasets={datasets}
                isRefreshing={isRefreshing}
                onRefresh={refreshDatasets}
                onUpload={() => navigate("upload")}
              />
            )}
          </section>
        </main>
      </div>
    </div>
  );
}
