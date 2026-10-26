import os
from pathlib import Path
import sys
import unittest

# Ensure project root in sys.path
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from rag_service.infrastructure.document_reader import DocumentReader


class TestDocumentReader(unittest.TestCase):
    def setUp(self):
        self.reader = DocumentReader()
        self.service = "income-assessment-service"

    def test_read_valid_markdown_document(self):
        """Successfully read a valid markdown file from service documentation."""
        doc = self.reader.read_document(self.service, "00-overview.md")
        self.assertEqual(doc.file, "00-overview.md")
        self.assertEqual(doc.service, self.service)
        self.assertEqual(doc.content_type, "text/markdown")
        self.assertGreater(doc.total_lines, 50)
        self.assertGreater(doc.size_bytes, 1000)
        self.assertIn("Income Assessment", doc.content)

    def test_read_valid_with_subpath_or_prefix(self):
        """Reading with 'docs/01-architecture.md' or full path still resolves safely."""
        doc = self.reader.read_document(self.service, "docs/01-architecture.md")
        self.assertEqual(doc.file, "01-architecture.md")
        self.assertIn("Architecture", doc.content)

    def test_read_absolute_path_from_qdrant_citation(self):
        """Reading with full absolute path stored by Qdrant ingestion resolves safely."""
        abs_path = str(self.reader.data_dir / self.service / "01-architecture.md")
        doc = self.reader.read_document(self.service, abs_path)
        self.assertEqual(doc.file, "01-architecture.md")
        self.assertEqual(doc.service, self.service)
        self.assertIn("Architecture", doc.content)

    def test_path_traversal_blocked(self):
        """Path traversal attempts using ../ are blocked with PermissionError."""
        with self.assertRaises(PermissionError):
            self.reader.read_document(self.service, "../../etc/passwd")

        with self.assertRaises(PermissionError):
            self.reader.read_document(self.service, "../../../Users/siddhantbhanot/.bashrc")

    def test_source_code_denied(self):
        """Source code files (.kt, .py, .java, etc.) must be rejected with PermissionError."""
        with self.assertRaises(PermissionError):
            self.reader.read_document(self.service, "FourWheelerPersonalAssessmentHandler.kt")

        with self.assertRaises(PermissionError):
            self.reader.read_document(self.service, "config.py")

        with self.assertRaises(PermissionError):
            self.reader.read_document(self.service, ".env")

    def test_missing_document_raises_404(self):
        """Non-existent markdown files raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.reader.read_document(self.service, "non_existent_file.md")

    def test_invalid_service_name(self):
        """Invalid service names with slashes or invalid characters raise ValueError."""
        with self.assertRaises(ValueError):
            self.reader.read_document("invalid/service/name", "00-overview.md")


if __name__ == "__main__":
    unittest.main()
