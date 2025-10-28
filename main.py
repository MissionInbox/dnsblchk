import time

from config import config
from dnschk import DNSBLCheckHandler
from dnsrbl import DNSRBLChecker
from files import FileHandler
from logger import Logger, LogConfig
from mail import MailClient
from signals import SignalHandler, SHUTDOWN_REQUESTED


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

    # Create the DNSBL check handler
    check_handler = DNSBLCheckHandler(mail_client, dnsrbl_checker, logger)

    while not SHUTDOWN_REQUESTED:
        check_handler.run(servers, ips)

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
