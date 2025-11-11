# Dataset titles to fetch (pipe-separated). Leave empty to use defaults.
REPORTS=

# Browser behavior and timeouts
HEADLESS=true
NAVIGATION_TIMEOUT_MS=45000

# Download destination
OUTPUT_DIR=./output

# Portal configuration
PORTAL_BASE_URL=https://www.data.gov.in/
PORTAL_SEARCH_URL=https://www.data.gov.in/search?query={query}
RESOURCE_SELECTOR=a[href$=".csv"], a[href$=".xls"], a[href$=".xlsx"], a.download-resource

# Optional login configuration (fill all fields to enable)
PORTAL_LOGIN_URL=
PORTAL_USERNAME=
PORTAL_PASSWORD=
PORTAL_USERNAME_SELECTOR=
PORTAL_PASSWORD_SELECTOR=
PORTAL_SUBMIT_SELECTOR=
PORTAL_POST_LOGIN_SELECTOR=
