# Automation-SDPVI
Automation Projects 
=======
Bank Login Automation Toolkit
=============================

This project automates end-to-end validation of test banking accounts stored in an Excel workbook. For each credential set it:

- Launches a Playwright browser session and performs login.
- Retrieves the OTP delivered to a shared mailbox and submits it.
- Captures account summary screenshots for every linked account.
- Navigates to each account’s statements area and downloads the latest statement.
- Records structured run results, including any failures and the corresponding root cause.

Project Layout
--------------

```
├── configs/          # Static selectors and metadata (JSON/YAML/etc.)
├── data/             # Non-sensitive fixtures (sample Excel workbook)
├── docs/             # Architecture notes and runbooks
├── docker/           # Container build files
├── outputs/          # Screenshots, statements, run_results.csv
├── src/              # Application code (package modules + tests)
│   ├── browser/      # Playwright bootstrap + page objects
│   ├── email/        # Mailbox polling + OTP parsing
│   ├── io/           # Excel reader + result writer
│   ├── utils/        # Config loading, security helpers
│   └── tests/        # Module-level unit tests
├── tests/            # Pytest entry point for black-box tests
├── .env.example      # Template for required environment variables
├── requirements.txt  # Python dependencies (pip install -r requirements.txt)
└── README.md
```

Quick Start
-----------

1. **Install system dependencies**

   - Python 3.11+
   - Node.js 18+ (for installing Playwright browsers)

2. **Create and populate your `.env`**

   ```
   cp .env.example .env
   # Fill in real values: bank URL, mailbox credentials, etc.
   ```

3. **Install Python dependencies**

   ```
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install --upgrade pip
   pip install -r requirements.txt
   playwright install  # download Chromium/WebKit/Firefox as needed
   ```

4. **Prepare runtime folders**

   ```
   mkdir -p outputs/screenshots outputs/statements
   ```

5. **Update selectors and sample data**

   - Adjust `configs/selectors.json` to mirror the target banking UI.
   - Replace `data/sample_accounts.xlsx` with your sanitized credential set.

6. **Run the automation**

   ```
   python -m src --env-file .env --selectors configs/selectors.json
   ```

   Additional CLI options:

   - `--limit 10` runs only the first 10 accounts (useful for dry-runs).
   - `--headless / --no-headless` overrides the Playwright headless flag from config.
   - `--account user@example.com` targets a single login.

7. **Review outputs**

   - Screenshots per account are written to `outputs/screenshots/<username>/`.
   - Statements are downloaded to `outputs/statements/<username>/`.
   - A CSV summarizing pass/fail status lives at `outputs/run_results.csv`.
   - Logs are rotated in `outputs/automation.log`.

Docker Usage
------------

Build and run from a clean host:

```
docker build -t bank-automation ./docker
docker run --rm \
  -v "$(pwd)/outputs:/app/outputs" \
  -v "$(pwd)/data:/app/data" \
  --env-file .env \
  bank-automation
```

Continuous Integration
----------------------

The `ci/github-actions.yml` workflow installs dependencies, runs unit tests (including Playwright install), and archives runtime artifacts. Adapt the job to your CI provider as needed.

Extending The Toolkit
---------------------

- Add OCR or statement parsing to enrich the result CSV with balance data.
- Swap the Excel reader for an API/DB source by implementing a new reader in `src/io/`.
- Integrate with a secret manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) by extending `src/utils/security.py`.
- Introduce parallelism by leveraging Playwright contexts per worker account (coordinate email polling carefully).

Support
-------

Issues and enhancement ideas can be tracked in `docs/README.md`. For production hardening, prioritize:

- Selector stability and retries.
- Observability (structured logging, metrics).
- Secure handling of credentials and OTP payloads (masking, secret rotation).
