from __future__ import annotations

import unittest

from evaluation_core.datasets import DatasetValidationError, parse_csv_dataset


class DatasetParsingTests(unittest.TestCase):
    def test_parses_valid_dataset_and_bom(self):
        dataset = parse_csv_dataset(
            b"Note\nAlpha note\nBeta note\n",
            "\ufeffQuestion,Relevant Note\nWhere is alpha?,Alpha note\n".encode("utf-8"),
        )
        self.assertEqual(dataset.contexts, ("Alpha note", "Beta note"))
        self.assertEqual(dataset.questions, ("Where is alpha?",))
        self.assertEqual(dataset.most_relevant, (0,))

    def test_rejects_missing_relevant_note_in_strict_mode(self):
        with self.assertRaisesRegex(DatasetValidationError, "exactly match"):
            parse_csv_dataset(
                b"Note\nAlpha note\n",
                b"Question,Relevant Note\nWhere is beta?,Beta note\n",
            )

    def test_compatibility_mode_adds_missing_relevant_note(self):
        dataset = parse_csv_dataset(
            b"Note\nAlpha note\n",
            b"Question,Relevant Note\nWhere is beta?,Beta note\n",
            add_missing_contexts=True,
        )
        self.assertEqual(dataset.contexts, ("Alpha note", "Beta note"))
        self.assertEqual(dataset.most_relevant, (1,))
        self.assertEqual(dataset.added_contexts, ("Beta note",))

    def test_enforces_row_limits(self):
        with self.assertRaisesRegex(DatasetValidationError, "maximum is 1"):
            parse_csv_dataset(
                b"Note\nAlpha\nBeta\n",
                b"Question,Relevant Note\nQuestion?,Alpha\n",
                max_contexts=1,
            )

    def test_rejects_wrong_headers(self):
        with self.assertRaisesRegex(DatasetValidationError, "Note"):
            parse_csv_dataset(
                b"Text\nAlpha\n",
                b"Question,Relevant Note\nQuestion?,Alpha\n",
            )


if __name__ == "__main__":
    unittest.main()
