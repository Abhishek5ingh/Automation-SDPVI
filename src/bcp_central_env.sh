# Dataset titles to fetch (pipe-separated). Leave empty to use defaults.
REPORTS=Air Traffic Passenger Statistics|Air Quality

# Browser behavior and timeouts
HEADLESS=true
NAVIGATION_TIMEOUT_MS=45000

# Download destination
OUTPUT_DIR=./downloads
LOG_DIR=./logs

# Portal configuration
PORTAL_BASE_URL=https://catalog.data.gov/dataset
PORTAL_SEARCH_URL=https://catalog.data.gov/dataset?q={query}
RESOURCE_SELECTOR=a[href$=".csv"], a[href$=".xls"], a[href$=".xlsx"], a[href$=".geojson"], a[href$=".kml"], a[href$=".kmz"], a.download-resource, a.btn.btn-primary[href]
RESOURCE_PRE_CLICK_SELECTOR=
SEARCH_INPUT_SELECTOR=input#search-big
SEARCH_SUBMIT_SELECTOR=form.search-form button[type="submit"]

# Optional login configuration (fill all fields to enable)
PORTAL_LOGIN_URL=
PORTAL_USERNAME=
PORTAL_PASSWORD=
PORTAL_USERNAME_SELECTOR=
PORTAL_PASSWORD_SELECTOR=
PORTAL_SUBMIT_SELECTOR=
PORTAL_POST_LOGIN_SELECTOR=
