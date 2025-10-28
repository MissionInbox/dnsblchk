import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from config import config
from dnsrbl import DNSRBLChecker
from logger import Logger, LogConfig, LogLevel
from mail import MailClient
from signals import SignalHandler


class DNSBLCheckHandler:
    """
    Handles DNSBL checking with support for multithreading.
    """

    def __init__(self, mail_client: MailClient, dnsrbl_checker: DNSRBLChecker, logger: Logger):
        """
        Initialize the DNSBL Check Handler.

        Args:
            mail_client: MailClient instance for sending alerts
            dnsrbl_checker: DNSRBLChecker instance for checking IPs
            logger: Logger instance for logging
        """
        self.mail_client = mail_client
        self.dnsrbl_checker = dnsrbl_checker
        self.logger = logger
        self.listed_ips = {}
        self.report_file_handler = None
        self.csv_writer = None
        self.lock = Lock()

    def check_ip_against_server(self, ip: str, server: str) -> tuple:
        """
        Check a single IP against a single DNSBL server.

        Args:
            ip: The IP address to check
            server: The DNSBL server to check against

        Returns:
            tuple: (ip, server, is_listed, result_details)
        """
        if SignalHandler().is_shutdown_requested:
            return None

        try:
            is_listed = self.dnsrbl_checker.check(ip, server)
            return (ip, server, is_listed, is_listed[1] if is_listed else None)
        except Exception as e:
            self.logger.log_error(f"Error checking {ip} against {server}: {str(e)}")
            return None

    def _write_report(self, ip: str, server: str, result_details: str):
        """
        Write a report entry to the CSV file (thread-safe).

        Args:
            ip: The IP address
            server: The DNSBL server
            result_details: Details about the listing
        """
        with self.lock:
            if self.report_file_handler is None:
                timestamp_filename = time.strftime("%Y%m%d%H%M%S", time.gmtime())
                report_file_path = config.report_dir / f"report_{timestamp_filename}.csv"
                self.report_file_handler = open(report_file_path, 'w', newline='')
                self.csv_writer = csv.writer(self.report_file_handler)

            timestamp = time.strftime("%d %b %Y %H:%M:%S", time.gmtime())
            self.csv_writer.writerow([timestamp, ip, server, result_details])
            self.report_file_handler.flush()

    def _record_listed_ip(self, ip: str, server: str):
        """
        Record a listed IP (thread-safe).

        Args:
            ip: The IP address
            server: The DNSBL server
        """
        with self.lock:
            if ip not in self.listed_ips:
                self.listed_ips[ip] = []
            if server not in self.listed_ips[ip]:
                self.listed_ips[ip].append(server)

    def _process_check_result(self, result: tuple):
        """
        Process the result of an IP check.

        Args:
            result: tuple containing (ip, server, is_listed, result_details)
        """
        if result is None:
            return

        ip, server, is_listed, result_details = result

        if is_listed:
            self._write_report(ip, server, result_details)
            self._record_listed_ip(ip, server)
            self.logger.log_info(f"DIRTY: {ip} is listed on {server}")
        else:
            self.logger.log_debug(f"CLEAN: {ip} is not listed on {server}")

    def run(self, servers: list, ips: list):
        """
        Run the DNSBL check with multithreading support.

        Args:
            servers: List of DNSBL servers
            ips: List of IPs to check
        """
        if SignalHandler().is_shutdown_requested:
            return

        try:
            self.listed_ips = {}
            self.report_file_handler = None
            self.csv_writer = None

            self.logger.log_info(f"Checking {len(ips)} IP addresses against {len(servers)} DNSBL servers.")
            self.logger.log_info(f"Using {config.get_thread_count()} threads.")

            # Prepare all check tasks
            check_tasks = []
            for server in servers:
                if SignalHandler().is_shutdown_requested:
                    break
                for ip in ips:
                    if SignalHandler().is_shutdown_requested:
                        break
                    check_tasks.append((ip[0], server[0]))

            # Execute checks with threading
            thread_count = config.get_thread_count()
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = {
                    executor.submit(self.check_ip_against_server, ip, server): (ip, server)
                    for ip, server in check_tasks
                }

                for future in as_completed(futures):
                    if SignalHandler().is_shutdown_requested:
                        break

                    try:
                        result = future.result()
                        self._process_check_result(result)
                    except Exception as e:
                        ip, server = futures[future]
                        self.logger.log_error(f"Exception checking {ip} against {server}: {str(e)}")

                    time.sleep(0.01)

            if self.report_file_handler:
                self.report_file_handler.close()

            self.logger.log_info(f"Found {len(self.listed_ips)} listed IP addresses.")

            if self.listed_ips and config.is_email_enabled():
                self._send_email_report()

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_details = SignalHandler.format_exception(exc_type, exc_value, exc_traceback)
            if error_details:
                log_config = LogConfig(log_file=config.log_file, level=LogLevel.ERROR)
                logger = Logger(log_config)
                logger.log_error(error_details)

    def _send_email_report(self):
        """
        Send an email report of the listed IP addresses.
        """
        mail_text = "The following IP addresses were found on one or more DNS blacklists:\n\n"
        for ip, servers in self.listed_ips.items():
            mail_text += f"{ip} ===> {', '.join(servers)}\n"

        for recipient in config.get_email_recipients():
            success, error = self.mail_client.send_plain(
                to_email=recipient,
                from_email=config.get_email_sender(),
                subject="DNS Black List Alert",
                message=mail_text
            )
            if not success:
                self.logger.log_error(f"Mailer error: {error}")

