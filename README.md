# DNSblChk

DNSblChk is a modern, open-source Python service for monitoring and reporting on DNS blacklists. It is designed for ease of use, with a straightforward configuration and clear reporting.

## Features

-   **Modern Python**: Refactored for Python 3 with type hints and current best practices.
-   **Easy Configuration**: All settings are managed in a single `config/config.yaml` file.
-   **Flexible Operation**: Can be run as a continuous monitoring service or as a one-time check.
-   **Email Alerts**: Sends detailed email notifications when listed IP addresses are found.
-   **CSV Reports**: Records all findings in CSV files for easy analysis.
-   **Advanced Logging**: Configurable logging levels (DEBUG, INFO, WARN, ERROR) with console and file output control.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/transilvlad/dnsblchk.git
    cd dnsblchk
    ```

2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

All configuration is done in the `config.yaml` file. Here are the available options:

-   `run_once`: If `true`, the script will run once and then exit. (Default: `false`)
-   `sleep_hours`: The number of hours to wait between checks. (Default: `3`)
-   `log_level`: Logging level for the application. Can be `DEBUG`, `INFO`, `WARN`, or `ERROR`. (Default: `INFO`)
-   `console_print`: If `true`, log messages will be printed to console in addition to the log file. (Default: `true`)
-   `email_report`: If `true`, an email report will be sent if any IPs are listed. (Default: `true`)
-   `recipients`: A list of email addresses to receive alerts.
-   `from_email`: The "From" address for email alerts.
-   `smtp_host`: The hostname or IP address of your SMTP server.
-   `smtp_port`: The port for your SMTP server.
-   `servers_file`: Path to the CSV file containing DNSBL servers.
-   `ips_file`: Path to the CSV file containing IPs to check.
-   `log_dir`: Directory to store log files.
-   `log_file`: Path to the main log file for logging errors and events.
-   `report_dir`: Directory to store CSV report files from DNSBL checks.

## Usage

To run the service, simply execute the `main.py` script:

```bash
python main.py
```

The service will start checking the IPs listed in `config/ips.txt` against the DNSBL servers in `config/servers.txt`.
Any findings will be logged and to a CSV file and if configured, email alerts will be sent.
