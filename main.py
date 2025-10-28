import time

from config import config
from dnschk import DNSBLCheckHandler
from dnsrbl import DNSRBLChecker
from files import FileHandler
from logger import Logger, LogConfig
from mail import MailClient
from signals import SignalHandler


class MainApplication:
    """
    Main application class for the DNSBL checker service.
    """

    def __init__(self):
        """Initialize the application."""
        self.logger = None
        self.signal_handler = None
        self.mail_client = None
        self.dnsrbl_checker = None
        self.check_handler = None
        self.servers = None
        self.ips = None

    def _setup_logger(self):
        """Set up the logger with config-driven settings."""
        log_config = LogConfig(
            log_file=config.log_file,
            log_dir=config.log_dir,
            level=config.get_log_level(),
            console_print=config.get_console_print()
        )
        self.logger = Logger(log_config)

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        self.signal_handler = SignalHandler()
        self.signal_handler.setup_signal_handlers()

    def _setup_clients_and_checkers(self):
        """Initialize mail client and DNSRBL checker."""
        self.mail_client = MailClient(config.get_smtp_host(), config.get_smtp_port())
        self.dnsrbl_checker = DNSRBLChecker()

    def _load_configuration(self):
        """Load servers and IPs from configuration files."""
        self.servers = FileHandler.load_csv(config.servers_file)
        self.ips = FileHandler.load_csv(config.ips_file)
        self.logger.log_info(f"Loaded {len(self.servers)} DNSBL servers and {len(self.ips)} IP addresses.")

    def _initialize(self):
        """Initialize all components."""
        self._setup_logger()
        self.logger.log_info("DNSblChk service started.")

        self._setup_signal_handlers()
        self._setup_clients_and_checkers()
        self._load_configuration()

        self.check_handler = DNSBLCheckHandler(self.mail_client, self.dnsrbl_checker, self.logger)

    def _run_checks(self):
        """Run the DNSBL checks."""
        self.check_handler.run(self.servers, self.ips)

    def _sleep_with_shutdown_check(self, duration: int):
        """
        Sleep for a specified duration while allowing graceful shutdown.

        Args:
            duration: Sleep duration in seconds
        """
        # Sleep in small intervals to allow for graceful shutdown.
        for _ in range(int(duration / 10)):
            if self.signal_handler.is_shutdown_requested:
                break
            time.sleep(10)

    def run(self):
        """Run the main application loop."""
        self._initialize()

        try:
            while not self.signal_handler.is_shutdown_requested:
                self._run_checks()

                if config.run_once:
                    self.logger.log_debug("Run-once mode enabled. Exiting.")
                    break

                sleep_duration = config.sleep_hours * 3600
                self.logger.log_info(f"Sleeping for {config.sleep_hours} hours...")
                self._sleep_with_shutdown_check(sleep_duration)

        finally:
            self.logger.log_info("DNSblChk service shutdown complete.")


def main():
    """
    Main entry point for the DNSBL checker service.
    """
    app = MainApplication()
    app.run()


if __name__ == "__main__":
    main()
