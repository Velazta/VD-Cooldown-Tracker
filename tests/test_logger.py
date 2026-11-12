"""Unit Tests for Centralized Application Logger.

Verifies logger hierarchy, file writing, log levels, and handler cleanup.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.logger import APP_LOGGER_NAME, get_logger, setup_logging


class TestAppLogger(unittest.TestCase):
    """Test suite for application logger configuration and dispatching."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_file = Path(self.temp_dir.name) / "test_app.log"

    def tearDown(self) -> None:
        # Clear logger handlers to avoid file lock on Windows during cleanup
        logger = logging.getLogger(APP_LOGGER_NAME)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        self.temp_dir.cleanup()

    def test_setup_logging_defaults(self) -> None:
        """Verify default setup configures console and file handlers with correct levels."""
        logger = setup_logging(debug_mode=False, log_file=self.log_file)
        self.assertEqual(logger.name, APP_LOGGER_NAME)
        self.assertEqual(len(logger.handlers), 2)

        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]

        self.assertEqual(len(stream_handlers), 1)
        self.assertEqual(stream_handlers[0].level, logging.INFO)

        self.assertEqual(len(file_handlers), 1)
        self.assertEqual(file_handlers[0].level, logging.DEBUG)

    def test_setup_logging_debug_mode(self) -> None:
        """Verify debug_mode=True sets console handler level to DEBUG."""
        logger = setup_logging(debug_mode=True, log_file=self.log_file)
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        self.assertEqual(stream_handlers[0].level, logging.DEBUG)

    def test_get_logger_hierarchy(self) -> None:
        """Verify get_logger returns child loggers correctly attached to VDTracker."""
        root_logger = get_logger()
        self.assertEqual(root_logger.name, APP_LOGGER_NAME)

        child_logger = get_logger("capture")
        self.assertEqual(child_logger.name, f"{APP_LOGGER_NAME}.capture")

        nested_child = get_logger("database.manager")
        self.assertEqual(nested_child.name, f"{APP_LOGGER_NAME}.database.manager")

    def test_file_logging_writes_content(self) -> None:
        """Verify logged messages are persisted to disk in the configured log file."""
        logger = setup_logging(debug_mode=False, log_file=self.log_file)
        test_msg = "TEST_INTEGRATION_LOG_MESSAGE_12345"
        logger.info(test_msg)

        # Flush handlers
        for handler in logger.handlers:
            handler.flush()

        self.assertTrue(self.log_file.exists())
        content = self.log_file.read_text(encoding="utf-8")
        self.assertIn(test_msg, content)
        self.assertIn("[INFO   ]", content)

    def test_reconfigure_logging_avoids_duplicate_handlers(self) -> None:
        """Verify calling setup_logging multiple times replaces rather than duplicates handlers."""
        setup_logging(debug_mode=False, log_file=self.log_file)
        setup_logging(debug_mode=True, log_file=self.log_file)
        logger = get_logger()
        self.assertEqual(len(logger.handlers), 2)


if __name__ == "__main__":
    unittest.main()
