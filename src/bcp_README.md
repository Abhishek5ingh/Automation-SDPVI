# Playwright Dataset Downloader (Python)

Single-file Python automation that opens a configurable open-data portal (defaults to [data.gov.in](https://www.data.gov.in/)), searches for one or more dataset names, opens the matching dataset page, and downloads the first CSV/XLS resource into `./output`. The flow is intentionally generic so you can point it to other sites by updating the `.env` values without touching code.

## Prerequisites
- Python 3.10+
- `pip` and Playwright browsers (`python -m playwright install chromium` after installing dependencies)

## Setup
```bash
python -m venv .venv && source .venv/bin/activate  # optional but recommended
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env  # adjust values as needed
```

Key `.env` knobs:
- `REPORTS`: pipe-separated dataset titles; CLI args append/override
- `PORTAL_BASE_URL` / `PORTAL_SEARCH_URL`: base landing page and search template (`{query}` placeholder is replaced automatically)
- `RESOURCE_SELECTOR`: CSS selector Playwright uses to click the desired downloadable resource
- `RESOURCE_PRE_CLICK_SELECTOR`: optional selector to expand or activate UI elements (like dropdown toggles) before the resource link exists/turns visible
- `SEARCH_INPUT_SELECTOR` / `SEARCH_SUBMIT_SELECTOR`: drive portals whose search box lives on the landing page—when set, the script fills the input and either presses Enter or clicks the provided submit selector instead of navigating to `PORTAL_SEARCH_URL`.
- `LOG_DIR`: location for timestamped log files (default `./logs`); each run writes a detailed log for troubleshooting
- `PORTAL_*_SELECTOR` + credentials: enable login for portals that require authentication (left empty for data.gov.in)
- `HEADLESS=false`: observe the browser when troubleshooting

## Usage
```bash
# Use defaults or values from .env
python automation.py

# Provide report names directly
python automation.py "International Air Traffic Data" "Average Number Of Trains Run Daily upto 2013-14"

# Force headed mode regardless of .env
python automation.py --headed "Some Dataset"
```

Downloads are saved under `OUTPUT_DIR` (default `./downloads`) using the filename suggested by the portal. Each dataset is processed independently, so failures are logged and the script moves on before summarizing at the end.

## Adapting to New Websites
1. Update `.env` with the new base/search URLs and, if necessary, tweak `RESOURCE_SELECTOR` to match the download buttons on that site.
2. If the site requires authentication, fill in the login URL, selectors, and credentials; the helper only attempts login when all values are present.
3. Provide the dataset titles either via `.env` (`REPORTS`) or CLI arguments.

Because the automation relies primarily on text matching for dataset links plus configurable selectors, it should handle most dataset portals without code changes.

## Repository Contents
- `automation.py`: main Playwright script that reads `.env`/CLI inputs and orchestrates downloads.
- `requirements.txt`: locked Python dependencies for the automation runtime.
- `downloads/`: default directory where downloaded resources are saved; safe to clear between runs if you need a fresh workspace.
- `logs/`: timestamped run logs that capture the detailed Playwright flow and errors.

## Example Configuration
The committed `.env` demonstrates how to automate [catalog.data.gov](https://catalog.data.gov/dataset): it uses the site’s built-in search bar (`SEARCH_INPUT_SELECTOR=input#search-big`, `SEARCH_SUBMIT_SELECTOR=form.search-form button[type="submit"]`) and downloads the “Air Traffic Passenger Statistics” and “Air Quality” datasets. Swap those report titles for any other catalog entries to try different downloads without changing code.
