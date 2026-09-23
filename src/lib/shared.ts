import type { DatasetSummary } from "@/types/dashboard";

export const SHARED_DATASETS: DatasetSummary[] = [
  {
    id: "squad_1_1",
    name: "SQuAD 1.1",
    source: "shared",
    status: "ready",
    contextCount: 2067,
    questionCount: 10570,
    createdAt: null,
    expiresAt: null,
    job: null,
    results: [],
    dataUrl: "/data/squad_1_1.json",
  },
  {
    id: "assistive_tech",
    name: "Assistive Technology",
    source: "shared",
    status: "ready",
    contextCount: 320,
    questionCount: 20,
    createdAt: null,
    expiresAt: null,
    job: null,
    results: [],
    dataUrl: "/data/assistive_tech.json",
  },
  {
    id: "cooking",
    name: "Cooking",
    source: "shared",
    status: "ready",
    contextCount: 89,
    questionCount: 20,
    createdAt: null,
    expiresAt: null,
    job: null,
    results: [],
    dataUrl: "/data/cooking.json",
  },
];

export const METRIC_HELP = {
  "Recall@1": "How often the correct note was the top result. Higher is better.",
  "Recall@3": "How often the correct note appeared in the top three. Higher is better.",
  "Mean Rank": "The average position of the correct note. Lower is better.",
  MRR: "Rewards putting the correct note closer to the top. Higher is better.",
} as const;

export const MODEL_LABELS: Record<string, string> = {
  gemini_3072: "Gemini embedding-001",
  "all-mpnet-base-v2": "all-mpnet-base-v2",
  "multi-qa-MiniLM-L6-dot-v1": "multi-qa-MiniLM-L6-dot-v1",
};
