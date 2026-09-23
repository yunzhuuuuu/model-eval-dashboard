export const METRICS = ["Recall@1", "Recall@3", "Mean Rank", "MRR"] as const;
export type MetricName = (typeof METRICS)[number];

export const MODELS = [
  "gemini_3072",
  "all-mpnet-base-v2",
  "multi-qa-MiniLM-L6-dot-v1",
] as const;
export type ModelName = (typeof MODELS)[number];

export type ModelResult = {
  modelName: string;
  metrics: Partial<Record<MetricName, number>>;
};

export type JobSummary = {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  stage: string;
  progressCompleted: number;
  progressTotal: number;
  attemptCount: number;
  maxAttempts: number;
  errorMessage: string | null;
};

export type DatasetSummary = {
  id: string;
  name: string;
  source: "shared" | "private";
  status: string;
  contextCount: number | null;
  questionCount: number | null;
  createdAt: string | null;
  expiresAt: string | null;
  job: JobSummary | null;
  results: ModelResult[];
  dataUrl?: string;
};

export type DatasetContent = {
  questions: string[];
  contexts: string[];
  mostRelevant: number[];
};

export type SessionInfo = {
  id: string;
  expiresAt: string;
};
