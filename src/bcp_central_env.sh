# Dataset titles to fetch (pipe-separated). Leave empty to use defaults.
REPORTS=Pune Stormwater Drains|Bengaluru Stormwater Drains Maps

# Browser behavior and timeouts
HEADLESS=true
NAVIGATION_TIMEOUT_MS=45000

# Download destination
OUTPUT_DIR=./output

# Portal configuration
PORTAL_BASE_URL=https://data.opencity.in/
PORTAL_SEARCH_URL=https://data.opencity.in/dataset?q={query}
RESOURCE_SELECTOR=a[href$=".csv"], a[href$=".xls"], a[href$=".xlsx"], a[href$=".geojson"], a[href$=".kml"], a[href$=".kmz"], a.download-resource
RESOURCE_PRE_CLICK_SELECTOR=.resource-item .dropdown-toggle

# Optional login configuration (fill all fields to enable)
PORTAL_LOGIN_URL=
PORTAL_USERNAME=
PORTAL_PASSWORD=
PORTAL_USERNAME_SELECTOR=
PORTAL_PASSWORD_SELECTOR=
PORTAL_SUBMIT_SELECTOR=
PORTAL_POST_LOGIN_SELECTOR=
