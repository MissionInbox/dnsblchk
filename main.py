import csv
import sys
import time
from pathlib import Path

from config import config
from dnsrbl import DNSRBLChecker
from files import FileHandler
from logger import Logger
from mail import MailClient
from signals import SignalHandler, SHUTDOWN_REQUESTED


def dnsbl_check_handler(servers: list, ips: list, mail_client: MailClient, dnsrbl_checker: DNSRBLChecker, logger: Logger):
    """
    Handles the DNSBL checking process.
    """
    if SHUTDOWN_REQUESTED:
        return

    try:
        listed_ips = {}
        report_file_handler = None
        csv_writer = None

        logger.log_info(f"Checking {len(ips)} IP addresses against {len(servers)} DNSBL servers.")

        for server in servers:
            if SHUTDOWN_REQUESTED:
                break
            for ip in ips:
                if SHUTDOWN_REQUESTED:
                    break

                is_listed = dnsrbl_checker.check(ip[0], server[0])
                if is_listed:
                    if report_file_handler is None:
                        timestamp_filename = time.strftime("%Y%m%d%H%M%S", time.gmtime())
                        report_file_path = Path(config.report_dir) / f"report_{timestamp_filename}.csv"
                        report_file_handler = open(report_file_path, 'w', newline='')
                        csv_writer = csv.writer(report_file_handler)

                    timestamp = time.strftime("%d %b %Y %H:%M:%S", time.gmtime())
                    csv_writer.writerow([timestamp, ip[0], server[0], is_listed[1]])
                    report_file_handler.flush()

                    if ip[0] not in listed_ips:
                        listed_ips[ip[0]] = []
                    listed_ips[ip[0]].append(server[0])
                    logger.log_info(f"DIRTY: {ip[0]} is listed on {server[0]}")
                else:
                    logger.log_debug(f"CLEAN: {ip[0]} is not listed on {server[0]}")

                time.sleep(0.01)

        if report_file_handler:
            report_file_handler.close()

        logger.log_info(f"Found {len(listed_ips)} listed IP addresses.")

        if listed_ips and config.email_report:
            send_email_report(listed_ips, mail_client, logger)

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_details = SignalHandler.format_exception(exc_type, exc_value, exc_traceback)
        if error_details:
            logger = Logger()
            logger.log_error(error_details, Path(config.log_file))


def send_email_report(listed_ips: dict, mail_client: MailClient, logger: Logger):
    """
    Sends an email report of the listed IP addresses.
    """
    mail_text = "The following IP addresses were found on one or more DNS blacklists:\n\n"
    for ip, servers in listed_ips.items():
        mail_text += f"{ip} ===> {', '.join(servers)}\n"

    for recipient in config.recipients:
        success, error = mail_client.send_plain(
            to_email=recipient,
            from_email=config.from_email,
            subject="DNS Black List Alert",
            message=mail_text
        )
        if not success:
            error_log_path = Path(config.log_file)
            logger.log_error(f"Mailer error: {error}", error_log_path)


def main():
    """
    Main function to run the DNSBL checker.
    """
    logger = Logger(log_file=Path(config.log_file), log_dir=Path(config.log_dir), debug=True)
    signal_handler = SignalHandler()
    signal_handler.setup_signal_handlers()
    mail_client = MailClient(config.smtp_host, config.smtp_port)
    dnsrbl_checker = DNSRBLChecker()

    servers = FileHandler.load_csv(Path(config.servers_file))
    ips = FileHandler.load_csv(Path(config.ips_file))

    while not SHUTDOWN_REQUESTED:
        dnsbl_check_handler(servers, ips, mail_client, dnsrbl_checker, logger)

        if getattr(config, 'run_once', False):
            logger.log_debug("Run-once mode enabled. Exiting.")
            break

        sleep_duration = getattr(config, 'sleep_hours', 3) * 3600
        logger.log_info(f"Sleeping for {getattr(config, 'sleep_hours', 3)} hours...")

        # Sleep in small intervals to allow for graceful shutdown
        for _ in range(int(sleep_duration / 10)):
            if SHUTDOWN_REQUESTED:
                break
            time.sleep(10)

    logger.log_debug("Shutdown complete.")


if __name__ == "__main__":
    main()
