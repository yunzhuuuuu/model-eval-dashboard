import { describe, expect, it } from "vitest";

import { CsvValidationError, parseDatasetText } from "@/lib/csv";

const contexts = 'Note\n"Buy milk, eggs, and bread"\nPack an umbrella\n';
const qanda =
  'Question,Relevant Note\n"What groceries do I need?","Buy milk, eggs, and bread"\nWill it rain?,Pack an umbrella\n';

describe("CSV validation", () => {
  it("parses valid quoted CSV and maps relevant notes", () => {
    expect(parseDatasetText(contexts, qanda)).toEqual({
      contexts: ["Buy milk, eggs, and bread", "Pack an umbrella"],
      questions: ["What groceries do I need?", "Will it rain?"],
      mostRelevant: [0, 1],
    });
  });

  it("rejects notes that are not exact context matches", () => {
    expect(() =>
      parseDatasetText(contexts, "Question,Relevant Note\nQuestion,Missing note\n"),
    ).toThrow(CsvValidationError);
  });

  it("rejects duplicate contexts", () => {
    expect(() =>
      parseDatasetText("Note\nSame\nSame\n", "Question,Relevant Note\nQ,Same\n"),
    ).toThrow("duplicate");
  });
});
