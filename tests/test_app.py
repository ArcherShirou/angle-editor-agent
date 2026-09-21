import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class AppTest(unittest.TestCase):
    def test_load_env_and_draft_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            env = Path(folder) / ".env"
            env.write_text("TEST_ANGLE_AGENT=value=with-equals\n", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                app.load_env(env)
                self.assertEqual("value=with-equals", app.os.environ["TEST_ANGLE_AGENT"])

        with self.assertRaisesRegex(ValueError, "drafts"):
            app.safe_draft(str(app.ROOT / "profile.md"))

    def test_quota_error_is_actionable(self):
        error = RuntimeError()
        error.code = "credit_balance_exhausted"
        self.assertIn("billing", app.api_error_message(error))


if __name__ == "__main__":
    unittest.main()
