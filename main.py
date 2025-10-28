import csv
import sys
import time

from config import config
from dnsrbl import DNSRBLChecker
from files import FileHandler
from logger import Logger, LogConfig, LogLevel
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
                        report_file_path = config.report_dir / f"report_{timestamp_filename}.csv"
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

        if listed_ips and config.is_email_enabled():
            send_email_report(listed_ips, mail_client, logger)

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_details = SignalHandler.format_exception(exc_type, exc_value, exc_traceback)
        if error_details:
            log_config = LogConfig(log_file=config.log_file, level=LogLevel.ERROR)
            logger = Logger(log_config)
            logger.log_error(error_details)


def send_email_report(listed_ips: dict, mail_client: MailClient, logger: Logger):
    """
    Sends an email report of the listed IP addresses.
    """
    mail_text = "The following IP addresses were found on one or more DNS blacklists:\n\n"
    for ip, servers in listed_ips.items():
        mail_text += f"{ip} ===> {', '.join(servers)}\n"

    for recipient in config.get_email_recipients():
        success, error = mail_client.send_plain(
            to_email=recipient,
            from_email=config.get_email_sender(),
            subject="DNS Black List Alert",
            message=mail_text
        )
        if not success:
            logger.log_error(f"Mailer error: {error}")


def main():
    """
    Main function to run the DNSBL checker.
    """
    # Create logger with config-driven settings
    log_config = LogConfig(
        log_file=config.log_file,
        log_dir=config.log_dir,
        level=config.get_log_level(),
        console_print=config.get_console_print()
    )
    logger = Logger(log_config)

    logger.log_info("DNSblChk service started.")

    signal_handler = SignalHandler()
    signal_handler.setup_signal_handlers()
    mail_client = MailClient(config.get_smtp_host(), config.get_smtp_port())
    dnsrbl_checker = DNSRBLChecker()

    servers = FileHandler.load_csv(config.servers_file)
    ips = FileHandler.load_csv(config.ips_file)

    logger.log_info(f"Loaded {len(servers)} DNSBL servers and {len(ips)} IP addresses.")

    while not SHUTDOWN_REQUESTED:
        dnsbl_check_handler(servers, ips, mail_client, dnsrbl_checker, logger)

        if config.run_once:
            logger.log_debug("Run-once mode enabled. Exiting.")
            break

        sleep_duration = config.sleep_hours * 3600
        logger.log_info(f"Sleeping for {config.sleep_hours} hours...")

        # Sleep in small intervals to allow for graceful shutdown
        for _ in range(int(sleep_duration / 10)):
            if SHUTDOWN_REQUESTED:
                break
            time.sleep(10)

    logger.log_info("DNSblChk service shutdown complete.")


if __name__ == "__main__":
    main()
