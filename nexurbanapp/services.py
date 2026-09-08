# properties/services.py

import requests

from django.conf import settings
from django.core.cache import cache

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =========================================================
# CACHE SETTINGS
# =========================================================

# 1 hour
CACHE_TTL = getattr(
    settings,
    "X_OPPERP_CACHE_TTL",
    60 * 60
)

PROPERTY_LIST_CACHE_KEY = "xopperp:properties:all"
PROPERTY_DETAIL_CACHE_KEY = "xopperp:property:{id}:detail"
PROPERTY_UNITS_CACHE_KEY = "xopperp:property:{id}:units"


# =========================================================
# XOPPERP API
# =========================================================

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
            HTTPAdapter(
                max_retries=retries,
                pool_maxsize=10,
            )
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
        url = f"{self.base_url}/properties/{property_id}/"

        return self.session.get(
            url,
            headers=self.headers(),
            timeout=(5, 30),
        )

    def get_property_units(self, property_id):
        url = f"{self.base_url}/properties/{property_id}/units/"

        return self.session.get(
            url,
            headers=self.headers(),
            timeout=(5, 30),
        )


# =========================================================
# GET ALL PROPERTIES
# =========================================================

def get_all_properties(api, force_refresh=False):
    """
    Get all properties.

    First request:
        Fetches all properties from XOpperp API
        and stores them in Django cache.

    Subsequent requests:
        Returns properties directly from cache.

    Cache lifetime:
        1 hour.

    After 1 hour:
        Cache expires and fresh API data is fetched.
    """

    # -----------------------------------------------------
    # 1. CHECK CACHE
    # -----------------------------------------------------

    if not force_refresh:

        cached_properties = cache.get(
            PROPERTY_LIST_CACHE_KEY
        )

        if cached_properties is not None:
            return cached_properties

    # -----------------------------------------------------
    # 2. CACHE EMPTY / EXPIRED
    #    FETCH FROM API
    # -----------------------------------------------------

    all_properties = []

    page = 1
    page_size = 100

    while True:

        response = api.get_properties({
            "page": page,
            "page_size": page_size,
        })

        response.raise_for_status()

        data = response.json()

        # -------------------------------------------------
        # API RESPONSE FORMAT
        # -------------------------------------------------

        if isinstance(data, dict):

            results = data.get(
                "results",
                []
            )

        elif isinstance(data, list):

            results = data

        else:

            results = []

        # -------------------------------------------------
        # NO MORE RESULTS
        # -------------------------------------------------

        if not results:
            break

        all_properties.extend(results)

        # -------------------------------------------------
        # PAGINATION
        # -------------------------------------------------

        next_url = (
            data.get("next")
            if isinstance(data, dict)
            else None
        )

        if not next_url:
            break

        page += 1

    # -----------------------------------------------------
    # 3. STORE COMPLETE LIST IN CACHE
    # -----------------------------------------------------

    cache.set(
        PROPERTY_LIST_CACHE_KEY,
        all_properties,
        CACHE_TTL,
    )

    return all_properties


# =========================================================
# PROPERTY DETAIL
# =========================================================

def get_cached_property_detail(
    api,
    property_id,
    force_refresh=False
):

    key = PROPERTY_DETAIL_CACHE_KEY.format(
        id=property_id
    )

    if not force_refresh:

        cached = cache.get(key)

        if cached is not None:
            return cached

    response = api.get_property(property_id)

    response.raise_for_status()

    data = response.json()

    cache.set(
        key,
        data,
        CACHE_TTL,
    )

    return data


# =========================================================
# PROPERTY UNITS
# =========================================================

def get_cached_property_units(
    api,
    property_id,
    force_refresh=False
):

    key = PROPERTY_UNITS_CACHE_KEY.format(
        id=property_id
    )

    if not force_refresh:

        cached = cache.get(key)

        if cached is not None:
            return cached

    response = api.get_property_units(property_id)

    response.raise_for_status()

    data = response.json()

    cache.set(
        key,
        data,
        CACHE_TTL,
    )

    return data


# =========================================================
# FORCE REFRESH
# =========================================================

def refresh_all_properties_cache():

    """
    Force fresh property data from XOpperp
    and replace the existing cache.
    """

    api = XOpperpAPI()

    return get_all_properties(
        api,
        force_refresh=True,
    )