import time
from pathlib import Path
from typing import Optional


class Logger:
    """Handles logging of errors and other messages to log files."""

    def __init__(self, log_file: Optional[Path] = None, log_dir: Optional[Path] = None, debug: bool = False):
        """
        Initialize the logger with an optional log file path.

        Args:
            log_file: Path to the log file. If None, no logging to file will occur.
            log_dir: Path to the log directory. Will be created if it doesn't exist.
            debug: Enable debug logging.
        """
        self.log_file = log_file
        self.debug = debug

        # Create log directory if provided
        if log_dir:
            self._create_log_directory(log_dir)

    def log_error(self, message: str, log_file: Optional[Path] = None) -> None:
        """
        Logs an error message to a file with a timestamp.

        Args:
            message: The error message to log.
            log_file: Optional override for the log file path. Uses self.log_file if not provided.
        """
        self._log("ERROR", message, log_file)

    def log_info(self, message: str, log_file: Optional[Path] = None) -> None:
        """
        Logs an info message to a file with a timestamp.

        Args:
            message: The info message to log.
            log_file: Optional override for the log file path. Uses self.log_file if not provided.
        """
        self._log("INFO", message, log_file)

    def log_warning(self, message: str, log_file: Optional[Path] = None) -> None:
        """
        Logs a warning message to a file with a timestamp.

        Args:
            message: The warning message to log.
            log_file: Optional override for the log file path. Uses self.log_file if not provided.
        """
        self._log("WARN", message, log_file)

    def log_debug(self, message: str, log_file: Optional[Path] = None) -> None:
        """
        Logs a debug message to a file with a timestamp (only if debug mode is enabled).

        Args:
            message: The debug message to log.
            log_file: Optional override for the log file path. Uses self.log_file if not provided.
        """
        if self.debug:
            self._log("DEBUG", message, log_file)

    def set_log_file(self, log_file: Path) -> None:
        """
        Sets or updates the log file path.

        Args:
            log_file: Path to the new log file.
        """
        self.log_file = log_file

    def _log(self, log_type: str, message: str, log_file: Optional[Path] = None) -> None:
        """
        Internal method to handle all logging with consistent formatting.

        Args:
            log_type: The type of log (ERROR, INFO, WARN, DEBUG, etc.).
            message: The message to log.
            log_file: Optional override for the log file path.
        """
        file_path = log_file or self.log_file
        if not file_path:
            return

        with open(file_path, 'a') as f:
            timestamp = self._timemark()
            f.write(f"{timestamp} - {log_type}: {message}\n")

    def _create_log_directory(self, log_dir: Path) -> None:
        """
        Creates the log directory if it doesn't exist.
        Logs a debug message if the directory is created.

        Args:
            log_dir: Path to the log directory.
        """
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            if self.debug:
                print(f"[DEBUG] Created log file: {log_dir}")

    @staticmethod
    def _timemark() -> str:
        """Returns the current time formatted as a string."""
        return time.strftime("%d %b %Y %H:%M:%S", time.gmtime())
