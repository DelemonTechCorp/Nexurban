import requests

from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


CACHE_TTL = getattr(settings, "X_OPPERP_CACHE_TTL", 60 * 60)

PROPERTY_LIST_CACHE_KEY = "xopperp:properties:all"
PROPERTY_DETAIL_CACHE_KEY = "xopperp:property:{id}:detail"
PROPERTY_UNITS_CACHE_KEY = "xopperp:property:{id}:units"


class XOpperpAPI:

    def __init__(self):
        self.base_url = settings.X_OPPERP_BASE_URL.rstrip("/")
        self.api_key = settings.X_OPPERP_API_KEY

        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET"],
        )
        self.session.mount(
            "https://",
            HTTPAdapter(max_retries=retries, pool_maxsize=10),
        )

    def headers(self):
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }

    def get_properties(self, params=None):
        return self.session.get(
            f"{self.base_url}/properties/",
            headers=self.headers(),
            params=params or {},
            timeout=(5, 30),
        )

    def get_property(self, property_id):
        return self.session.get(
            f"{self.base_url}/properties/{property_id}/",
            headers=self.headers(),
            timeout=(5, 30),
        )

    def get_property_units(self, property_id):
        return self.session.get(
            f"{self.base_url}/properties/{property_id}/units/",
            headers=self.headers(),
            timeout=(5, 30),
        )


def get_all_properties(api, force_refresh=False):
    if not force_refresh:
        cached = cache.get(PROPERTY_LIST_CACHE_KEY)
        if cached is not None:
            return cached

    all_properties = []
    page = 1
    page_size = 100

    while True:
        response = api.get_properties({"page": page, "page_size": page_size})
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict):
            results = data.get("results", [])
        elif isinstance(data, list):
            results = data
        else:
            results = []

        if not results:
            break

        all_properties.extend(results)

        next_url = data.get("next") if isinstance(data, dict) else None
        if not next_url:
            break

        page += 1

    cache.set(PROPERTY_LIST_CACHE_KEY, all_properties, CACHE_TTL)
    return all_properties


def get_cached_property_detail(api, property_id, force_refresh=False):
    key = PROPERTY_DETAIL_CACHE_KEY.format(id=property_id)

    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached

    response = api.get_property(property_id)
    response.raise_for_status()
    data = response.json()

    cache.set(key, data, CACHE_TTL)
    return data


def get_cached_property_units(api, property_id, force_refresh=False):
    key = PROPERTY_UNITS_CACHE_KEY.format(id=property_id)

    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached

    response = api.get_property_units(property_id)
    response.raise_for_status()
    data = response.json()

    cache.set(key, data, CACHE_TTL)
    return data


def refresh_all_properties_cache():
    return get_all_properties(XOpperpAPI(), force_refresh=True)


def property_slug(prop):
    return f"{slugify(prop.get('title') or 'property')}-{prop['id']}"


def get_area_slug(prop):
    district = prop.get("district")
    return slugify(district) if district else None


def id_from_slug(slug):
    try:
        return int(slug.rsplit("-", 1)[-1])
    except (ValueError, AttributeError):
        return None


def is_listed(prop):
    return bool(prop.get("is_active")) and (prop.get("available_units_count") or 0) > 0


def get_listed_properties(api=None):
    api = api or XOpperpAPI()
    listed = []
    for p in get_all_properties(api):
        if is_listed(p):
            p["slug"] = property_slug(p)
            p["area_slug"] = get_area_slug(p)
            listed.append(p)
    return listed