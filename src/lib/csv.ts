import Papa from "papaparse";

import type { DatasetContent } from "@/types/dashboard";

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const MAX_CONTEXTS = 10_000;
export const MAX_QUESTIONS = 10_000;

export class CsvValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CsvValidationError";
  }
}

function normalizedHeader(value: string): string {
  return value.replace(/^\uFEFF/, "").trim().toLocaleLowerCase("en-US").replace(/\s+/g, " ");
}

function rowsFromText(text: string, label: string): string[][] {
  const parsed = Papa.parse<string[]>(text, { skipEmptyLines: "greedy" });
  const errors = parsed.errors.filter(
    (error) => error.code !== "UndetectableDelimiter",
  );
  if (errors.length > 0) {
    const first = errors[0];
    throw new CsvValidationError(
      `${label} is not valid CSV${first.row === undefined ? "" : ` near row ${first.row + 1}`}: ${first.message}`,
    );
  }
  return parsed.data;
}

export function parseDatasetText(
  contextText: string,
  qandaText: string,
): DatasetContent {
  const contextRows = rowsFromText(contextText, "context.csv");
  if (contextRows.length === 0 || normalizedHeader(contextRows[0]?.[0] ?? "") !== "note") {
    throw new CsvValidationError('context.csv must start with a "Note" column.');
  }

  const contexts: string[] = [];
  for (let index = 1; index < contextRows.length; index += 1) {
    const row = contextRows[index];
    if (row.length !== 1) {
      throw new CsvValidationError(
        `context.csv row ${index + 1} must contain exactly one column.`,
      );
    }
    const note = row[0].trim();
    if (!note) {
      throw new CsvValidationError(
        `context.csv row ${index + 1} contains an empty note.`,
      );
    }
    contexts.push(note);
  }

  if (contexts.length === 0) {
    throw new CsvValidationError("context.csv must contain at least one note.");
  }
  if (contexts.length > MAX_CONTEXTS) {
    throw new CsvValidationError(
      `context.csv has ${contexts.length} notes; the maximum is ${MAX_CONTEXTS}.`,
    );
  }
  if (new Set(contexts).size !== contexts.length) {
    throw new CsvValidationError(
      "context.csv contains duplicate notes; each note must be unique.",
    );
  }

  const qandaRows = rowsFromText(qandaText, "qanda.csv");
  const qandaHeader = qandaRows[0]?.map(normalizedHeader) ?? [];
  if (qandaHeader[0] !== "question" || qandaHeader[1] !== "relevant note") {
    throw new CsvValidationError(
      'qanda.csv must start with "Question" and "Relevant Note" columns.',
    );
  }

  const questions: string[] = [];
  const relevantNotes: string[] = [];
  for (let index = 1; index < qandaRows.length; index += 1) {
    const row = qandaRows[index];
    if (row.length !== 2) {
      throw new CsvValidationError(
        `qanda.csv row ${index + 1} must contain exactly two columns.`,
      );
    }
    const question = row[0].trim();
    const relevantNote = row[1].trim();
    if (!question || !relevantNote) {
      throw new CsvValidationError(
        `qanda.csv row ${index + 1} must include both a question and a relevant note.`,
      );
    }
    questions.push(question);
    relevantNotes.push(relevantNote);
  }

  if (questions.length === 0) {
    throw new CsvValidationError(
      "qanda.csv must contain at least one question and relevant note.",
    );
  }
  if (questions.length > MAX_QUESTIONS) {
    throw new CsvValidationError(
      `qanda.csv has ${questions.length} questions; the maximum is ${MAX_QUESTIONS}.`,
    );
  }

  const contextIndex = new Map(contexts.map((note, index) => [note, index]));
  const mostRelevant = relevantNotes.map((note) => {
    const index = contextIndex.get(note);
    if (index === undefined) {
      throw new CsvValidationError(
        "Every Relevant Note in qanda.csv must exactly match a note in context.csv.",
      );
    }
    return index;
  });

  return { questions, contexts, mostRelevant };
}

export async function validateDatasetFiles(
  contextFile: File,
  qandaFile: File,
): Promise<DatasetContent> {
  for (const file of [contextFile, qandaFile]) {
    if (file.size > MAX_UPLOAD_BYTES) {
      throw new CsvValidationError(`${file.name} is larger than the 10 MB upload limit.`);
    }
    if (!file.name.toLocaleLowerCase("en-US").endsWith(".csv")) {
      throw new CsvValidationError(`${file.name} must be a CSV file.`);
    }
  }
  const [contextText, qandaText] = await Promise.all([
    contextFile.text(),
    qandaFile.text(),
  ]);
  return parseDatasetText(contextText, qandaText);
}
