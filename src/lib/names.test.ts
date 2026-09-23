import { describe, expect, it } from "vitest";

import { cleanDatasetName, datasetNameKey, validateDatasetName } from "@/lib/names";

describe("dataset names", () => {
  it("normalizes display and comparison names", () => {
    expect(cleanDatasetName("  Study   Notes ")).toBe("Study Notes");
    expect(datasetNameKey("  STUDY notes ")).toBe("study notes");
  });

  it("rejects unsafe or missing names", () => {
    expect(validateDatasetName("")).toMatch("provide");
    expect(validateDatasetName("mine__other")).toMatch("double underscores");
    expect(validateDatasetName("x".repeat(121))).toMatch("120");
  });
});
