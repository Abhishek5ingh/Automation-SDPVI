Architecture Notes
------------------

### Overview

1. `src/utils.config.load_config` loads environment variables and prepares folder structure.
2. `src/io.excel_reader.ExcelAccountReader` streams credential records from the configured workbook.
3. `src/browser.browser_manager.BrowserManager` bootstraps a Playwright Chromium browser with isolated context per account run.
4. `src/email.mailbox_client.MailboxClient` polls the shared mailbox for OTP messages and uses `src/email/parser.py` to extract the numeric code.
5. `src/runner.AutomationRunner` orchestrates the workflow, capturing screenshots and downloading statements via `src/browser.pages`.
6. `src/io.results_writer.ResultsWriter` appends run metadata (status, failure reason, artifacts) to a CSV for downstream reporting.

### Retry and Resilience

- The mailbox client retries the connection check and polls with a configurable timeout/interval.
- Extend the workflow with `tenacity` decorators for idempotent browser steps (e.g., re-click login on transient network failures).

### Security Guidance

- Keep `.env` out of source control by relying on `.env.example` for templates.
- Store secrets in a secret manager in production; load them at runtime and inject into the container or execution environment.
- The `src/utils/security.py` module offers simple redaction helpers for logging; expand it with encryption/HSM integration if necessary.

### Future Enhancements

- Add concurrency with per-account browser contexts; throttle mailbox polling to avoid rate limits.
- Persist structured logs/metrics to ELK, Splunk, or CloudWatch for observability.
- Integrate OCR/statement parsing (planned next iteration) to extract balance figures for QA validation.
