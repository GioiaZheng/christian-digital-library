from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "review_uploads", ROOT / "scripts" / "review_uploads.py"
)
assert SPEC and SPEC.loader
REVIEW = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REVIEW
SPEC.loader.exec_module(REVIEW)


class ReviewUploadsTests(unittest.TestCase):
    def test_env_file_parses_r2_settings_without_public_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "R2_ENDPOINT=https://example.r2.cloudflarestorage.com/christian-digital-library",
                        "R2_BUCKET=christian-digital-library",
                        "R2_ACCESS_KEY_ID=test-key",
                        "R2_SECRET_ACCESS_KEY=test-secret",
                    ]
                ),
                encoding="utf-8",
            )

            settings = REVIEW.load_settings(env_path)

        self.assertEqual("https://example.r2.cloudflarestorage.com", settings.endpoint)
        self.assertEqual("christian-digital-library", settings.bucket)
        self.assertEqual("test-key", settings.access_key_id)

    def test_pending_keys_are_restricted_to_pending_prefix(self) -> None:
        request_id = "abc-123"

        self.assertEqual(
            "pending/metadata/abc-123.json",
            REVIEW.pending_metadata_key(request_id),
        )
        self.assertEqual(
            "pending/uploads/abc-123/",
            REVIEW.pending_upload_prefix(request_id),
        )

    def test_rejects_request_id_with_path_separators(self) -> None:
        with self.assertRaises(REVIEW.R2Error):
            REVIEW.pending_metadata_key("../raw/book.zip")

    def test_request_id_from_metadata_key(self) -> None:
        self.assertEqual(
            "abc-123",
            REVIEW.request_id_from_metadata_key("pending/metadata/abc-123.json"),
        )

    def test_canonical_query_string_sorts_and_encodes(self) -> None:
        self.assertEqual(
            "list-type=2&prefix=pending%2Fmetadata%2F",
            REVIEW.canonical_query_string(
                {"prefix": "pending/metadata/", "list-type": "2"}
            ),
        )


if __name__ == "__main__":
    unittest.main()
