import tempfile
import unittest
from pathlib import Path

from scripts.check_arabic_po import check_catalog, parse_po


class ArabicPOCheckTests(unittest.TestCase):
    def check_text(self, text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ar.po"
            path.write_text(text, encoding="utf-8")
            return check_catalog(path)

    def test_accepts_translated_brace_placeholder(self):
        self.assertEqual(
            self.check_text(
                '#, python-brace-format\nmsgid "Hello {0}"\nmsgstr "مرحبا {0}"\n'
            ),
            [],
        )

    def test_reports_missing_translation(self):
        issues = self.check_text('msgid "Save"\nmsgstr ""\n')
        self.assertTrue(issues[0].startswith("Untranslated:"))

    def test_reports_missing_placeholder(self):
        issues = self.check_text(
            '#, python-brace-format\nmsgid "Hello {name}"\nmsgstr "مرحبا"\n'
        )
        self.assertTrue(issues[0].startswith("Placeholder mismatch"))

    def test_ignores_fuzzy_translation(self):
        self.assertEqual(
            self.check_text('#, fuzzy\nmsgid "Old text"\nmsgstr ""\n'), []
        )

    def test_parses_multiline_translation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ar.po"
            path.write_text(
                'msgid "Greeting"\nmsgstr "مرحبا "\n"بكم"\n', encoding="utf-8"
            )
            self.assertEqual(
                parse_po(path)[0]["translations"], {"msgstr": "مرحبا بكم"}
            )


if __name__ == "__main__":
    unittest.main()
