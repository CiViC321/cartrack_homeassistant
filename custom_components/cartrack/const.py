"""Constants for CarTrack."""

DOMAIN = "cartrack"
CONF_API_URL = "api_url"
CONF_API_REGION = "api_region"
CONF_API_KEY = "api_key"
CONF_USERNAME = "username"
DEFAULT_API_REGION = "za"
API_REGIONS = (
    ("au", "Australia"),
    ("bw", "Botswana"),
    ("kh", "Cambodia"),
    ("hk", "Hong Kong"),
    ("id", "Indonesia"),
    ("ke", "Kenya"),
    ("mw", "Malawi"),
    ("my", "Malaysia"),
    ("me", "Middle East"),
    ("mz", "Mozambique"),
    ("na", "Namibia"),
    ("nz", "New Zealand"),
    ("ng", "Nigeria"),
    ("ph", "Philippines"),
    ("pl", "Poland"),
    ("pt", "Portugal"),
    ("rw", "Rwanda"),
    ("sa", "Kingdom of Saudi Arabia"),
    ("sg", "Singapore"),
    ("za", "South Africa"),
    ("es", "Spain"),
    ("sz", "Swaziland"),
    ("th", "Thailand"),
    ("tz", "Tanzania"),
    ("vn", "Vietnam"),
    ("zm", "Zambia"),
    ("zw", "Zimbabwe"),
)
API_REGION_DOMAINS = {"ke": "karooooo.com", "sa": "karooooo.com"}
UPDATE_INTERVAL_SECONDS = 3
