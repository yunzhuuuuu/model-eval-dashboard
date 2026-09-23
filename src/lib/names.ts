export function cleanDatasetName(value: string): string {
  return value.normalize("NFKC").trim().replace(/\s+/g, " ");
}

export function datasetNameKey(value: string): string {
  return cleanDatasetName(value).toLocaleLowerCase("en-US");
}

export function validateDatasetName(value: string): string | null {
  const clean = cleanDatasetName(value);
  if (!clean) return "Please provide a dataset name.";
  if (clean.length > 120) return "Dataset names must be 120 characters or fewer.";
  if (clean.includes("__")) return "Dataset names cannot contain double underscores.";
  return null;
}
