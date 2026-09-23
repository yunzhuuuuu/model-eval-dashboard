"""CSV parsing and validation for retrieval evaluation datasets."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import io
from pathlib import Path


CONTEXT_HEADER = "note"
QUESTION_HEADER = "question"
RELEVANT_NOTE_HEADER = "relevant note"


class DatasetValidationError(ValueError):
    """Raised when uploaded CSV files do not form a valid retrieval dataset."""


@dataclass(frozen=True)
class RetrievalDataset:
    """Normalized question/context data used by the embedding and metric layers."""

    questions: tuple[str, ...]
    contexts: tuple[str, ...]
    most_relevant: tuple[int, ...]
    added_contexts: tuple[str, ...] = ()


def _rows_from_bytes(contents: bytes, label: str) -> list[list[str]]:
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DatasetValidationError(f"{label} must be UTF-8 encoded.") from exc

    try:
        return list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise DatasetValidationError(f"{label} is not valid CSV: {exc}") from exc


def _normalized_header(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _parse_contexts(contents: bytes) -> list[str]:
    rows = _rows_from_bytes(contents, "context.csv")
    if not rows:
        raise DatasetValidationError("context.csv is empty.")
    if not rows[0] or _normalized_header(rows[0][0]) != CONTEXT_HEADER:
        raise DatasetValidationError('context.csv must start with a "Note" column.')

    contexts: list[str] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != 1:
            raise DatasetValidationError(
                f"context.csv row {row_number} must contain exactly one column."
            )
        note = row[0].strip()
        if not note:
            raise DatasetValidationError(
                f"context.csv row {row_number} contains an empty note."
            )
        contexts.append(note)

    if not contexts:
        raise DatasetValidationError("context.csv must contain at least one note.")
    if len(set(contexts)) != len(contexts):
        raise DatasetValidationError(
            "context.csv contains duplicate notes; each note must be unique."
        )
    return contexts


def _parse_questions(contents: bytes) -> list[tuple[str, str]]:
    rows = _rows_from_bytes(contents, "qanda.csv")
    if not rows:
        raise DatasetValidationError("qanda.csv is empty.")

    header = [_normalized_header(cell) for cell in rows[0]]
    if header[:2] != [QUESTION_HEADER, RELEVANT_NOTE_HEADER]:
        raise DatasetValidationError(
            'qanda.csv must start with "Question" and "Relevant Note" columns.'
        )

    pairs: list[tuple[str, str]] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != 2:
            raise DatasetValidationError(
                f"qanda.csv row {row_number} must contain exactly two columns."
            )
        question, relevant_note = (cell.strip() for cell in row)
        if not question or not relevant_note:
            raise DatasetValidationError(
                f"qanda.csv row {row_number} must include both a question and a relevant note."
            )
        pairs.append((question, relevant_note))

    if not pairs:
        raise DatasetValidationError(
            "qanda.csv must contain at least one question and relevant note."
        )
    return pairs


def parse_csv_dataset(
    context_csv: bytes,
    qanda_csv: bytes,
    *,
    max_contexts: int | None = None,
    max_questions: int | None = None,
    add_missing_contexts: bool = False,
) -> RetrievalDataset:
    """Parse the two upload files and map each question to its ground-truth note."""

    contexts = _parse_contexts(context_csv)
    pairs = _parse_questions(qanda_csv)

    if max_contexts is not None and len(contexts) > max_contexts:
        raise DatasetValidationError(
            f"context.csv has {len(contexts)} notes; the maximum is {max_contexts}."
        )
    if max_questions is not None and len(pairs) > max_questions:
        raise DatasetValidationError(
            f"qanda.csv has {len(pairs)} questions; the maximum is {max_questions}."
        )

    added_contexts: list[str] = []
    known_contexts = set(contexts)
    for _, relevant_note in pairs:
        if relevant_note in known_contexts:
            continue
        if not add_missing_contexts:
            raise DatasetValidationError(
                "Every Relevant Note in qanda.csv must exactly match a note in context.csv."
            )
        contexts.append(relevant_note)
        known_contexts.add(relevant_note)
        added_contexts.append(relevant_note)

    if max_contexts is not None and len(contexts) > max_contexts:
        raise DatasetValidationError(
            f"The normalized dataset has {len(contexts)} notes; the maximum is {max_contexts}."
        )

    context_to_index = {context: index for index, context in enumerate(contexts)}
    return RetrievalDataset(
        questions=tuple(question for question, _ in pairs),
        contexts=tuple(contexts),
        most_relevant=tuple(
            context_to_index[relevant_note] for _, relevant_note in pairs
        ),
        added_contexts=tuple(added_contexts),
    )


def load_csv_dataset(
    context_path: str | Path,
    qanda_path: str | Path,
    **options: object,
) -> RetrievalDataset:
    """Load and parse a dataset from two filesystem paths."""

    return parse_csv_dataset(
        Path(context_path).read_bytes(),
        Path(qanda_path).read_bytes(),
        **options,
    )
