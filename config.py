from pathlib import Path

import yaml

from logger import LogLevel


class Config:
    """
    Handles loading the configuration from config.yaml and provides access to the settings.
    """

    def __init__(self):
        """Loads the configuration from config.yaml and resolves file paths."""
        root_path = Path(__file__).parent
        config_path = root_path / 'config/config.yaml'

        with open(config_path, 'r') as f:
            self._config_data = yaml.safe_load(f)

        # Resolve file paths to be absolute
        self._resolve_paths()

    def _resolve_paths(self):
        """Resolves all file paths in the config to be absolute."""
        self._config_data['servers_file'] = self._get_absolute_path('servers_file')
        self._config_data['ips_file'] = self._get_absolute_path('ips_file')
        self._config_data['report_dir'] = self._get_absolute_path('report_dir')

        # Resolve logging paths from nested logging config
        logging_config = self._config_data.get('logging', {})
        if 'log_dir' in logging_config:
            logging_config['log_dir'] = self._get_absolute_path_from_logging('log_dir')
        if 'log_file' in logging_config:
            logging_config['log_file'] = self._get_absolute_path_from_logging('log_file')

    def _get_absolute_path(self, key: str) -> Path:
        """Returns an absolute path for a given config key."""
        root_path = Path(__file__).parent
        return root_path / self._config_data[key]

    def _get_absolute_path_from_logging(self, key: str) -> Path:
        """Returns an absolute path for a given key in the logging config."""
        root_path = Path(__file__).parent
        logging_config = self._config_data.get('logging', {})
        return root_path / logging_config[key]

    def __getattr__(self, name):
        """Provides attribute-style access to the configuration settings."""
        if name in self._config_data:
            return self._config_data[name]

        # Check if the attribute is in the nested logging config
        logging_config = self._config_data.get('logging', {})
        if name in logging_config:
            return logging_config[name]

        # Check if the attribute is in the nested email config
        email_config = self._config_data.get('email', {})
        if name in email_config:
            return email_config[name]

        raise AttributeError(f"'Config' object has no attribute '{name}'")

    def get_log_level(self) -> LogLevel:
        """
        Returns the LogLevel enum based on the log_level config value.

        Returns:
            LogLevel: The configured log level (defaults to INFO if invalid).
        """
        logging_config = self._config_data.get('logging', {})
        level_str = logging_config.get('level', 'INFO').upper()
        try:
            return LogLevel[level_str]
        except KeyError:
            print(f"Warning: Invalid log level '{level_str}' in config. Using INFO.")
            return LogLevel.INFO

    def get_console_print(self) -> bool:
        """
        Returns whether console printing is enabled.

        Returns:
            bool: True if console printing is enabled (default: True).
        """
        logging_config = self._config_data.get('logging', {})
        return logging_config.get('console_print', True)

    def is_email_enabled(self) -> bool:
        """
        Returns whether email alerting is enabled.

        Returns:
            bool: True if email alerting is enabled (default: False).
        """
        email_config = self._config_data.get('email', {})
        return email_config.get('enabled', False)

    def get_email_recipients(self) -> list:
        """
        Returns the list of email recipients.

        Returns:
            list: List of email recipient addresses (default: empty list).
        """
        email_config = self._config_data.get('email', {})
        return email_config.get('recipients', [])

    def get_email_sender(self) -> str:
        """
        Returns the email sender address.

        Returns:
            str: The sender email address (default: empty string).
        """
        email_config = self._config_data.get('email', {})
        return email_config.get('sender', '')

    def get_smtp_host(self) -> str:
        """
        Returns the SMTP host.

        Returns:
            str: The SMTP host (default: empty string).
        """
        email_config = self._config_data.get('email', {})
        return email_config.get('smtp_host', '')

    def get_smtp_port(self) -> int:
        """
        Returns the SMTP port.

        Returns:
            int: The SMTP port (default: 25).
        """
        email_config = self._config_data.get('email', {})
        return email_config.get('smtp_port', 25)


# Create a single instance of the Config class to be used throughout the application
config = Config()
