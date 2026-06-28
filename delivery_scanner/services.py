import os
import re
import ssl
import certifi
import pygeohash as pgh
from geopy.geocoders import Nominatim
from tavily import TavilyClient

def clean_slug(text):
    """Converts location strings to clean URL slugs (e.g., 'Notting Hill' -> 'notting-hill')."""
    if not text:
        return ""
    # Strip out administrative prefixes that break Deliveroo's router
    text = text.lower().replace("london borough of ", "").replace("city of ", "")
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')


def convert_postcode_to_deliveroo_url(postcode_string):
    """
    Dynamically maps a UK postcode to a high-precision Geohash and constructs
    the undocumented native URL routing structure for Deliveroo.
    """
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    geolocator = Nominatim(
        user_agent="ghost_kitchen_arbiter",
        ssl_context=ssl_context
    )

    location = geolocator.geocode(
        f"{postcode_string}, UK",
        addressdetails=True,
        language="en"
    )

    if not location or 'address' not in location.raw:
        return None

    address_data = location.raw['address']

    # 1. Dynamically extract the City
    city_raw = address_data.get('city', address_data.get('town', ''))

    # 2. Smart Neighborhood Extraction
    neighborhood_raw = address_data.get('suburb',
                       address_data.get('village',
                       address_data.get('neighbourhood',
                       address_data.get('city_district', ''))))

    # Fallbacks in case geopy completely fails to find a location
    city_slug = clean_slug(city_raw) if city_raw else "london"
    neighborhood_slug = clean_slug(neighborhood_raw) if neighborhood_raw else "central"

    # 3. Generate the 12-character high-precision coordinate hash
    delivery_geohash = pgh.encode(location.latitude, location.longitude, precision=12)

    # 4. Construct the fully dynamic, native Deliveroo taxonomy URL
    target_url = f"https://deliveroo.co.uk/restaurants/{city_slug}/{neighborhood_slug}?geohash={delivery_geohash}&collection=restaurants&sort=distance"

    return target_url


def scrape_postcode_delivery_data(target_deliveroo_url):
    """
    Attempts a passive headless crawl of the target URL.
    Note: Production deployment requires an active Playwright/Puppeteer framework
    to bypass Deliveroo's React Hydration and OneTrust GDPR modal limitations.
    """
    # ALWAYS use environment variables for API keys in your final commits
    api_key = os.environ.get("TAVILY_API_KEY", "tvly-YOUR-SAFE-KEY")
    tavily_client = TavilyClient(api_key=api_key)

    response = tavily_client.crawl(
        url=target_deliveroo_url,
        max_depth=1,
        max_breadth=40,
        limit=40,
        extract_depth="advanced",
        wait_for="networkidle",
        timeout=20
    )

    results = response.get("results", [])
    if not results:
        return "No data returned from crawler. (React Hydration / GDPR Wall Intercept)"

    return results[0].get("raw_content", "")