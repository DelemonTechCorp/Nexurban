import re
from django.shortcuts import render
from django.http import JsonResponse
from urllib.parse import urljoin
from django.http import Http404
from .services import (
    XOpperpAPI,
    get_all_properties,
    get_cached_property_detail,
    get_cached_property_units,
)
import json
from django.urls import reverse
INVALID_LABELS = {"unnamed", "unnamed city", "n/a", "none", "null", ""}
import traceback
from .models import *
from django.shortcuts import render, get_object_or_404
from .models import BlogPost
from django.core.paginator import Paginator

# =========================================================
# FIELD HELPERS
# Matched to the documented X-Opperp v1 partner API schema.
# Fields are flat strings/numbers — no nested translation
# objects on this endpoint.
# =========================================================
from django.utils.text import slugify
def propertydetail(request, slug):

    
    # =====================================================
    # HANDLE ENQUIRY FORM SUBMISSION
    # =====================================================

    if request.method == "POST":

        enquiry = Enquiry.objects.create(
            form_type="property",
            name=request.POST.get("name", "").strip(),
            email=request.POST.get("email", "").strip(),
            phone=request.POST.get("phone", "").strip(),
            message=request.POST.get("message", "").strip(),
            interest=request.POST.get("interest", "").strip(),
            property_name=request.POST.get("property_name", "").strip(),
            property_slug=request.POST.get("property_slug", "").strip(),
        )

        try:
            result = send_enquiry_email(enquiry)

            print("BREVO SUCCESS:", result)

            enquiry.sent_to_brevo = True
            enquiry.save(update_fields=["sent_to_brevo"])

        except Exception as e:
            print("========== BREVO ERROR ==========")
            print("ERROR:", str(e))
            traceback.print_exc()
            print("=================================")

        return redirect(f"{reverse('thank_you')}?type=property")

    api = XOpperpAPI()

    # =====================================================
    # STEP 1: FIND PROPERTY FROM SLUG
    # =====================================================

    try:
        all_properties = get_all_properties(api)
    except Exception as e:
        print("X-OPPERP PROPERTY LIST ERROR:", e)
        all_properties = []

    prop_from_list = _find_property_by_slug(
        all_properties,
        slug
    )

    if not prop_from_list:
        raise Http404("Property not found")

    # =====================================================
    # STEP 2: GET PROPERTY ID
    # =====================================================

    property_id = (
        prop_from_list.get("id")
        or prop_from_list.get("external_id")
    )

    if not property_id:
        raise Http404("Property ID not found")

    # =====================================================
    # STEP 3: GET FULL PROPERTY DETAIL
    # GET /properties/{id}/
    # =====================================================

    # AFTER
    try:
        detail_data = get_cached_property_detail(api, property_id)
    except Exception as e:
        print("X-OPPERP PROPERTY DETAIL ERROR:", e)
        detail_data = prop_from_list
    # Handle:
    # {
    #     "data": {...}
    # }
    # OR:
    # {
    #     ...
    # }

    if isinstance(detail_data, dict):

        if isinstance(
            detail_data.get("data"),
            dict
        ):
            prop = detail_data["data"]

        else:
            prop = detail_data

    else:
        prop = prop_from_list

    # =====================================================
    # SOLD OUT CHECK
    # =====================================================

    if (
        get_sales_status_name(prop)
        .lower()
        == "sold out"
    ):
        raise Http404("Property not found")

    # =====================================================
    # STEP 4: GET ALL UNITS
    # GET /properties/{id}/units/
    # =====================================================

    # AFTER
    units = []
    try:
        units_data = get_cached_property_units(api, property_id)
        units = normalize_units(units_data)
    except Exception as e:
        print("X-OPPERP UNITS ERROR:", e)
        units = []

    # =====================================================
    # BASIC INFORMATION
    # =====================================================

    prop_slug = get_property_slug(prop)

    title = (
        api_text(
            prop.get("title")
        )
        or "Luxury Property"
    )

    bedroom_list = get_bedroom_list(prop)

    property_types = get_property_type_list(
        prop
    )

    # =====================================================
    # IMAGES
    # =====================================================

    cover_image = normalize_image_url(
        get_property_cover_image(prop)
    )

    images = []

    if cover_image:
        images.append(
            cover_image
        )

    raw_images = (
        prop.get("images")
        or []
    )

    if isinstance(raw_images, list):

        for image in raw_images:

            image_url = normalize_image_url(
                image
            )

            if (
                image_url
                and image_url not in images
            ):
                images.append(
                    image_url
                )

    # =====================================================
    # AMENITIES
    # =====================================================

    amenities = normalize_amenities(
        prop.get("amenities")
    )

    # =====================================================
    # PAYMENT PLANS
    # =====================================================

    payment_plans = normalize_payment_plans(
        prop
    )

    # =====================================================
    # NEARBY PLACES
    # =====================================================

    nearby_places = normalize_nearby_places(
        prop
    )

    # =====================================================
    # UNIT TYPES
    # =====================================================

    unit_types = build_unit_types(
        units
    )

    # =====================================================
    # UNIT STATISTICS
    # =====================================================

    available_units = [
        unit
        for unit in units
        if (
            unit.get("status")
            or ""
        ).lower()
        == "available"
    ]

    reserved_units = [
        unit
        for unit in units
        if (
            unit.get("status")
            or ""
        ).lower()
        == "reserved"
    ]

    sold_units = [
        unit
        for unit in units
        if (
            unit.get("status")
            or ""
        ).lower()
        == "sold"
    ]

    # =====================================================
    # MAIN PROPERTY OBJECT
    # =====================================================

    p = {

        # ---------------------------------------------
        # ID
        # ---------------------------------------------

        "id": property_id,

        "external_id": api_text(
            prop.get("external_id")
        ),

        "slug": prop_slug,

        # ---------------------------------------------
        # BASIC
        # ---------------------------------------------

        "name": title,

        "place": (
            get_area_name(prop)
            or get_city(prop)
        ),

        "district": get_area_name(
            prop
        ),

        "city": get_city(
            prop
        ),

        "developer": get_developer_name(
            prop
        ),

        # ---------------------------------------------
        # PROPERTY TYPE
        # ---------------------------------------------

        "tag": (
            get_property_type(prop)
            or get_property_status_name(prop)
        ),

        "property_type": (
            get_property_type(prop)
            or "Residence"
        ),

        "property_types": property_types,

        # ---------------------------------------------
        # PRICE
        # ---------------------------------------------

        "price": format_price_display(
            get_property_price(prop)
        ),

        "price_from": prop.get(
            "price_from"
        ),

        "price_to": prop.get(
            "price_to"
        ),

        # ---------------------------------------------
        # IMAGES
        # ---------------------------------------------

        "image": cover_image,

        "images": images,

        # ---------------------------------------------
        # DESCRIPTION
        # ---------------------------------------------

        "description": api_text(
            prop.get("description")
        ),

        # ---------------------------------------------
        # BEDROOMS
        # ---------------------------------------------

        "bedrooms": (
            ", ".join(bedroom_list)
            if bedroom_list
            else ""
        ),

        "bedroom_list": bedroom_list,

        "bedrooms_from": prop.get(
            "bedrooms_from"
        ),

        "bedrooms_to": prop.get(
            "bedrooms_to"
        ),

        # ---------------------------------------------
        # AREA
        # ---------------------------------------------

        "area_sqft": (
            prop.get("area_from")
            or prop.get("area_to")
        ),

        "area_from": prop.get(
            "area_from"
        ),

        "area_to": prop.get(
            "area_to"
        ),

        # ---------------------------------------------
        # STATUS
        # ---------------------------------------------

        "property_status": (
            get_property_status_name(prop)
        ),

        "sales_status": (
            get_sales_status_name(prop)
        ),

        # ---------------------------------------------
        # HANDOVER
        # ---------------------------------------------

        "delivery_date": api_text(
            prop.get("delivery_date")
        ),

        "handover": get_handover(
            prop
        ),

        # ---------------------------------------------
        # MAP
        # ---------------------------------------------

        "latitude": prop.get(
            "latitude"
        ),

        "longitude": prop.get(
            "longitude"
        ),

        # ---------------------------------------------
        # CONSTRUCTION
        # ---------------------------------------------

        "completion_rate": prop.get(
            "completion_rate"
        ),

        # ---------------------------------------------
        # RENTAL GUARANTEE
        # ---------------------------------------------

        "has_rental_guarantee": prop.get(
            "has_rental_guarantee"
        ),

        "rental_guarantee_pct": prop.get(
            "rental_guarantee_pct"
        ),

        # ---------------------------------------------
        # PROJECT UNITS
        # ---------------------------------------------

        "residential_units": prop.get(
            "residential_units"
        ),

        "commercial_units": prop.get(
            "commercial_units"
        ),

        "units_count": prop.get(
            "units_count"
        ),

        # ---------------------------------------------
        # PAYMENT PLAN DETAILS
        # ---------------------------------------------

        "down_payment_pct": prop.get(
            "down_payment_pct"
        ),

        "during_construction_pct": prop.get(
            "during_construction_pct"
        ),

        "on_handover_pct": prop.get(
            "on_handover_pct"
        ),

        "down_payment_amount": prop.get(
            "down_payment_amount"
        ),

        "post_delivery_payment": prop.get(
            "post_delivery_payment"
        ),

        # ---------------------------------------------
        # AMENITIES
        # ---------------------------------------------

        "amenities": amenities,

        # ---------------------------------------------
        # PAYMENT PLANS
        # ---------------------------------------------

        "payment_plans": payment_plans,

        # ---------------------------------------------
        # NEARBY
        # ---------------------------------------------

        "nearby_places": nearby_places,

        # ---------------------------------------------
        # UNITS
        # ---------------------------------------------

        "units": units,

        # ---------------------------------------------
        # UNIT TYPES
        # ---------------------------------------------

        "unit_types": unit_types,

        # ---------------------------------------------
        # UNIT COUNTS
        # ---------------------------------------------

        "available_units_count": len(
            available_units
        ),

        "reserved_units_count": len(
            reserved_units
        ),

        "sold_units_count": len(
            sold_units
        ),
    }

    # =====================================================
    # RELATED PROPERTIES
    # =====================================================

    def is_related(item):

        item_slug = get_property_slug(
            item
        )

        return (
            item_slug != prop_slug
            and
            get_sales_status_name(item)
            .lower()
            != "sold out"
        )

    same_district = [

        rp
        for rp in all_properties

        if (
            is_related(rp)
            and
            get_area_name(rp)
            .lower()
            ==
            get_area_name(prop)
            .lower()
        )

    ]

    same_city = [

        rp
        for rp in all_properties

        if (
            is_related(rp)
            and
            rp not in same_district
            and
            get_city(rp)
            .lower()
            ==
            get_city(prop)
            .lower()
        )

    ]

    related_pool = (
        same_district
        + same_city
    )[:3]

    properties = []

    for rp in related_pool:

        properties.append({

            "id": rp.get(
                "id"
            ),

            "slug": get_property_slug(
                rp
            ),

            "name": (
                api_text(
                    rp.get("title")
                )
                or "Luxury Property"
            ),

            "place": (
                get_area_name(rp)
                or get_city(rp)
            ),

            "tag": (
                get_property_type(rp)
                or get_property_status_name(rp)
            ),

            "price": format_price_display(
                get_property_price(rp)
            ),

            "image": normalize_image_url(
                get_property_cover_image(rp)
            ),
        })




    # =====================================================
    # FINAL CONTEXT
    # =====================================================

    context = {

        "p": p,

        "properties": properties,

        "amenities": amenities,

        "payment_plans": payment_plans,

        "nearby_places": nearby_places,

        "units": units,

        "unit_types": unit_types,

        "available_units": available_units,

        "reserved_units": reserved_units,

        "sold_units": sold_units,

    }

    return render(
        request,
        "main/propertydetail.html",
        context
    )




##
### 6. Full updated HTML



def get_property_slug(property_data):
    """
    Create URL slug from property title.
    """

    title = api_text(property_data.get("title"))

    if title:
        return slugify(title)

    fallback = (
        api_text(property_data.get("id"))
        or api_text(property_data.get("external_id"))
    )

    return slugify(fallback) if fallback else ""
def api_text(value):
    """
    Safely convert API values into readable text.
    """

    if value is None:
        return ""

    if isinstance(value, dict):

        for key in (
            "en",
            "name",
            "title",
            "label",
            "value",
            "display_name",
            "text",
        ):
            v = value.get(key)

            if v:
                return api_text(v)

        return ""

    return str(value).strip()


def get_city(property_data):
    return api_text(property_data.get("city"))


def get_area_name(property_data):
    """
    District/community name — the only location granularity
    this API exposes below city.
    """
    return api_text(property_data.get("district"))


def get_district_name(property_data):
    return get_area_name(property_data)


def get_developer_name(property_data):
    return api_text(property_data.get("developer_name"))


def get_property_type(property_data):
    """
    May be comma-separated, e.g. "Apartment, Villa" —
    displayed as-is; use get_property_type_list() for filtering.
    """
    return api_text(property_data.get("property_type"))


def get_property_type_list(property_data):
    raw = get_property_type(property_data)
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def get_property_status_name(property_data):
    """Flat field: 'Ready' or 'Off Plan'."""
    return api_text(property_data.get("property_status_name"))


def get_sales_status_name(property_data):
    """Flat field, e.g. 'On Sale', 'Sold Out'."""
    return api_text(property_data.get("sales_status_name"))
def get_bedroom_list(p):
    """
    Return actual bedroom values from the API.
    Never use area/sqft as bedrooms.
    """

    # Try common single-value / list API field names first
    value = (
        p.get("bedrooms")
        or p.get("bedroom")
        or p.get("number_of_bedrooms")
        or p.get("bedroom_count")
    )

    result = []

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                bedroom = (
                    item.get("bedrooms")
                    or item.get("bedroom")
                    or item.get("count")
                    or item.get("value")
                )
            else:
                bedroom = item
            if bedroom is not None:
                result.append(str(bedroom).strip())

    elif isinstance(value, dict):
        bedroom = (
            value.get("bedrooms")
            or value.get("bedroom")
            or value.get("count")
            or value.get("value")
        )
        if bedroom is not None:
            result.append(str(bedroom).strip())

    elif value is not None:
        value = str(value).strip()
        if value:
            result.append(value)

    # ---------------------------------------------
    # FALLBACK: project-level range, e.g. bedrooms_from=1,
    # bedrooms_to=4 -> expand to ["1","2","3","4"].
    # This is the field your list/detail endpoints
    # actually populate for projects (vs. single units).
    # ---------------------------------------------
    if not result:

        def to_num(v):
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return None

        low = to_num(p.get("bedrooms_from"))
        high = to_num(p.get("bedrooms_to"))

        if low is not None and high is not None:
            if low > high:
                low, high = high, low
            # cap the range so a bad API value (e.g. to=500) can't
            # generate thousands of bogus options
            high = min(high, low + 10)
            for n in range(low, high + 1):
                result.append("Studio" if n == 0 else str(n))
        elif low is not None:
            result.append("Studio" if low == 0 else str(low))
        elif high is not None:
            result.append("Studio" if high == 0 else str(high))

    return result
def get_property_price(property_data):
    """
    price_from is the documented starting price field. Falls
    back to price_to if price_from is missing/zero (price on
    request).
    """
    value = property_data.get("price_from")

    if value in (None, "", 0, "0"):
        value = property_data.get("price_to")

    if value in (None, "", 0, "0"):
        return None

    try:
        if isinstance(value, str):
            cleaned = (
                value
                .replace("AED", "")
                .replace(",", "")
                .replace(" ", "")
            )
            value = float(cleaned)
        else:
            value = float(value)

        return value if value > 0 else None

    except (TypeError, ValueError):
        return None


def get_property_cover_image(property_data):
    cover = property_data.get("cover")
    if cover:
        return str(cover).strip()

    images = property_data.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, str) and first.strip():
            return first.strip()

    return ""


def normalize_image_url(image):
    """
    Keep API image URL usable in template. Absolute URLs pass
    through unchanged; protocol-relative URLs get https: added.
    """
    if not image:
        return ""

    image = str(image).strip()

    if image.startswith("//"):
        return "https:" + image

    return image


def get_handover_code(property_data):
    """
    delivery_date is free text like "Q4 2027" (may be empty for
    ready units). Extract just the year for the filter value,
    e.g. "2027".
    """
    raw = api_text(property_data.get("delivery_date"))
    if not raw:
        return ""

    match = re.search(r"(20\d{2})", raw)
    return match.group(1) if match else ""


def get_handover(property_data):
    """Human-readable label — just the year, e.g. '2027'."""
    return get_handover_code(property_data)


# =========================================================
# DISTINCT-VALUE HELPERS (for filter dropdown options)
# =========================================================

def get_distinct_cities(all_properties):
    seen = {}
    for p in all_properties:
        value = get_city(p)
        if not value or value.strip().lower() in INVALID_LABELS:
            continue
        key = value.strip().lower()
        if key not in seen:
            seen[key] = value.strip()
    return sorted(seen.values(), key=lambda v: v.lower())


def get_distinct_districts(all_properties):
    seen = {}
    for p in all_properties:
        value = get_district_name(p)
        if not value or value.strip().lower() in INVALID_LABELS:
            continue
        key = value.strip().lower()
        if key not in seen:
            seen[key] = value.strip()
    return sorted(seen.values(), key=lambda v: v.lower())


def get_distinct_developers(all_properties):
    seen = {}
    for p in all_properties:
        value = get_developer_name(p)
        if not value or value.strip().lower() in INVALID_LABELS:
            continue
        key = value.strip().lower()
        if key not in seen:
            seen[key] = value.strip()
    return sorted(seen.values(), key=lambda v: v.lower())

def get_distinct_bedrooms(properties):
    """
    Build bedroom filter options only from actual bedroom values.
    """

    values = set()

    for p in properties:
        bedrooms = get_bedroom_list(p)

        for bedroom in bedrooms:

            if bedroom is None:
                continue

            bedroom = str(bedroom).strip()

            if not bedroom:
                continue

            # Ignore obvious sqft/area values
            try:
                number = float(bedroom)

                # Bedroom counts should normally be small.
                # This prevents 1060, 2051, 3953 etc.
                if number > 20:
                    continue

            except ValueError:
                pass

            values.add(bedroom)

    def sort_key(value):
        if value.lower() == "studio":
            return 0

        try:
            return float(value)
        except ValueError:
            return 999

    return sorted(values, key=sort_key)

def get_distinct_handover_options(all_properties):
    seen = {}
    for p in all_properties:
        year = get_handover_code(p)
        if not year:
            continue
        if year not in seen:
            seen[year] = year  # label is just the year
    return sorted(seen.items(), key=lambda kv: kv[0])  # list of (year, year)


def get_distinct_property_names(all_properties):
    names_seen = {}
    for p in all_properties:
        name = api_text(p.get("title"))
        if not name:
            continue
        key = name.strip().lower()
        if key not in names_seen:
            names_seen[key] = name.strip()
    return sorted(names_seen.values(), key=lambda v: v.lower())


def get_distinct_property_statuses(all_properties):
    statuses_seen = {}
    for p in all_properties:
        status = get_property_status_name(p) or get_sales_status_name(p)
        if not status:
            continue
        key = status.strip().lower()
        if key not in statuses_seen:
            statuses_seen[key] = status.strip()
    return sorted(statuses_seen.values(), key=lambda v: v.lower())


def get_distinct_locations(all_properties):
    locations_seen = {}
    for p in all_properties:
        area_name = get_area_name(p)
        if not area_name:
            continue
        key = area_name.strip().lower()
        if key not in locations_seen:
            locations_seen[key] = area_name.strip()
    return sorted(locations_seen.values(), key=lambda v: v.lower())


def parse_budget_range(budget_str):
    if not budget_str:
        return None, None
    parts = budget_str.split("-")
    try:
        budget_min = float(parts[0]) if parts[0] else None
    except ValueError:
        budget_min = None
    try:
        budget_max = float(parts[1]) if len(parts) > 1 and parts[1] else None
    except ValueError:
        budget_max = None
    return budget_min, budget_max


# =========================================================
# HOME
# =========================================================

import time


def home(request):

    api = XOpperpAPI()

    all_properties = []

    # Retry API request if connection is interrupted
    for attempt in range(3):

        try:
            all_properties = get_all_properties(api)

            print(
                f"X-OPPERP HOME API SUCCESS: "
                f"{len(all_properties)} properties loaded"
            )

            break

        except Exception as e:

            print(
                f"X-OPPERP HOME API ERROR "
                f"(attempt {attempt + 1}/3): {e}"
            )

            if attempt < 2:
                time.sleep(2)

    property_names = get_distinct_property_names(all_properties)
    property_statuses = get_distinct_property_statuses(all_properties)
    locations = get_distinct_locations(all_properties)

    # ==========================================
    # BUILD DISPLAY-READY HOME PROPERTIES
    # ==========================================

    home_properties = []

    for p in all_properties:

        # Get slug exactly like offplan
        slug = get_property_slug(p)

        # Property must have a slug
        if not slug:
            print(
                "HOME PROPERTY SKIPPED - NO SLUG:",
                p.get("title"),
                p.get("id")
            )
            continue

        cover_image = get_property_cover_image(p)

        title = api_text(
            p.get("title")
        ) or "Luxury Property"

        bedroom_list = get_bedroom_list(p)

        # Convert bedroom list to display string
        bedroom_labels = ", ".join(
            str(b) for b in bedroom_list
        ) if bedroom_list else ""

        # Area
        area_from = (
            p.get("area_from")
            or p.get("area_to")
        )

        # Price
        price_from = get_property_price(p)

        # External ID
        external_id = (
            api_text(p.get("id"))
            or api_text(p.get("external_id"))
        )

        home_properties.append({

            "id": external_id,

            # IMPORTANT
            "slug": slug,

            "title": title,

            "cover": normalize_image_url(
                cover_image
            ),

            "sales_status_name": get_sales_status_name(p),

            "property_status": get_property_status_name(p),

            "city": get_city(p),

            "district": get_area_name(p),

            "area_from": area_from,

            "area_to": p.get("area_to"),

            "property_type": get_property_type(p),

            "price_from": price_from,

            "developer": get_developer_name(p),

            "bedrooms": bedroom_list,

            "bedroom_labels": bedroom_labels,

            "bathrooms": p.get("bathrooms"),

            "handover": get_handover(p),

            "external_id": external_id,

            "raw": p,
        })

        # Only 6 properties on homepage
        if len(home_properties) >= 3:
            break

    print(
        "HOME DISPLAY PROPERTIES:",
        len(home_properties)
    )

    for prop in home_properties:
        print(
            "HOME PROPERTY:",
            prop["title"],
            "| SLUG:",
            prop["slug"]
        )

    context = {
        "home_properties": home_properties,
        "property_names": property_names,
        "property_statuses": property_statuses,
        "locations": locations,
    }

    return render(
        request,
        "main/home.html",
        context
    )

# =========================================================
# OFF-PLAN
# =========================================================
def offplan(request):

    api = XOpperpAPI()

    current_page = request.GET.get("page", 1)
    try:
        current_page = int(current_page)
    except (TypeError, ValueError):
        current_page = 1
    if current_page < 1:
        current_page = 1

    # BASIC FILTERS
    property_name = request.GET.get("property_name", "").strip()
    location = request.GET.get("location", "").strip()   # district
    city = request.GET.get("city", "").strip()            # emirate
    budget = request.GET.get("budget", "").strip()

    # ADVANCED FILTERS
    developer = request.GET.get("developer", "").strip()
    bedrooms = request.GET.get("bedrooms", "").strip()
    handover = request.GET.get("handover", "").strip()

    budget_min, budget_max = parse_budget_range(budget)

    try:
        all_properties = get_all_properties(api)
    except Exception as e:
        print("X-OPPERP API ERROR:", e)
        all_properties = []

    # OFF-PLAN BASE SET, excluding Sold Out
    base = [
        p for p in all_properties
        if get_property_status_name(p) == "Off Plan"
        and get_sales_status_name(p) != "Sold Out"
    ]

    # DYNAMIC FILTER OPTIONS (from base, not hardcoded)
    property_names = get_distinct_property_names(base)
    locations = get_distinct_districts(base)
    cities = get_distinct_cities(base)
    developers = get_distinct_developers(base)
    bedroom_options = get_distinct_bedrooms(base)
    handover_options = get_distinct_handover_options(base)

    # APPLY FILTERS
    filtered = base

    if property_name:
        pname_lower = property_name.lower()
        filtered = [
            p for p in filtered
            if pname_lower in api_text(p.get("title")).lower()
        ]

    if location:
        loc_lower = location.lower()
        filtered = [
            p for p in filtered
            if loc_lower in get_area_name(p).lower()
        ]

    if city:
        city_lower = city.lower()
        filtered = [
            p for p in filtered
            if city_lower in get_city(p).lower()
        ]

    if developer:
        developer_lower = developer.lower()
        filtered = [
            p for p in filtered
            if developer_lower in get_developer_name(p).lower()
        ]

    if bedrooms:
        filtered = [
            p for p in filtered
            if bedrooms in get_bedroom_list(p)
        ]

    if handover:
        filtered = [
            p for p in filtered
            if get_handover_code(p) == handover
        ]

    if budget_min is not None:
        filtered = [
            p for p in filtered
            if (get_property_price(p) or 0) >= budget_min
        ]

    if budget_max is not None:
        filtered = [
            p for p in filtered
            if (get_property_price(p) or 0) <= budget_max
        ]

   

       # BUILD DISPLAY-READY LIST
    properties_display = []

    for p in filtered:

        slug = get_property_slug(p)
        if not slug:
            continue

        cover_image = get_property_cover_image(p)
        title = api_text(p.get("title")) or "Luxury Property"

        properties_display.append({
            "id": p.get("id") or p.get("external_id"),
            "slug": slug,
            "title": title,
            "cover": normalize_image_url(cover_image),
            "sales_status_name": get_sales_status_name(p),
            "city": get_city(p),
            "district": get_area_name(p),
            "area_from": p.get("area_from") or p.get("area_to"),
            "property_type": get_property_type(p),
            "price_from": get_property_price(p),
            "developer": get_developer_name(p),
            "bedrooms": get_bedroom_list(p),
            "handover": get_handover(p),
        })
    # PAGINATION
    page_size = 9
    total_properties = len(properties_display)
    total_pages = (
        (total_properties + page_size - 1) // page_size
        if total_properties else 0
    )
    if total_pages and current_page > total_pages:
        current_page = total_pages

    start = (current_page - 1) * page_size
    end = start + page_size
    properties = properties_display[start:end]

    previous_page = current_page - 1 if current_page > 1 else None
    next_page = current_page + 1 if current_page < total_pages else None

    page_numbers = _build_page_numbers(current_page, total_pages)

    context = {
        "properties": properties,
        "total_properties": total_properties,
        "current_page": current_page,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "previous_page": previous_page,
        "next_page": next_page,
        "property_names": property_names,
        "locations": locations,
        "cities": cities,
        "developers": developers,
        "bedroom_options": bedroom_options,
        "handover_options": handover_options,
        "filters": {
            "property_name": property_name,
            "location": location,
            "city": city,
            "budget": budget,
            "developer": developer,
            "bedrooms": bedrooms,
            "handover": handover,
        },
    }

    return render(request, "main/offplan.html", context)

# =========================================================
# READY
# =========================================================

def ready(request):

    api = XOpperpAPI()

    current_page = request.GET.get("page", 1)
    try:
        current_page = int(current_page)
    except (TypeError, ValueError):
        current_page = 1
    if current_page < 1:
        current_page = 1

    # BASIC FILTERS
    property_name = request.GET.get("property_name", "").strip()
    location = request.GET.get("location", "").strip()   # district
    city = request.GET.get("city", "").strip()            # emirate
    budget = request.GET.get("budget", "").strip()

    # ADVANCED FILTERS
    developer = request.GET.get("developer", "").strip()
    bedrooms = request.GET.get("bedrooms", "").strip()
    handover = request.GET.get("handover", "").strip()

    budget_min, budget_max = parse_budget_range(budget)

    try:
        all_properties = get_all_properties(api)
    except Exception as e:
        print("X-OPPERP READY API ERROR:", e)
        all_properties = []

    # READY BASE SET, excluding Sold Out
    base = [
        p for p in all_properties
        if get_property_status_name(p) == "Ready"
        and get_sales_status_name(p) != "Sold Out"
    ]

    # DYNAMIC FILTER OPTIONS (from base, not hardcoded)
    property_names = get_distinct_property_names(base)
    locations = get_distinct_districts(base)
    cities = get_distinct_cities(base)
    developers = get_distinct_developers(base)
    bedroom_options = get_distinct_bedrooms(base)
    handover_options = get_distinct_handover_options(base)

    # APPLY FILTERS
    filtered = base

    if property_name:
        pname_lower = property_name.lower()
        filtered = [
            p for p in filtered
            if pname_lower in api_text(p.get("title")).lower()
        ]

    if location:
        loc_lower = location.lower()
        filtered = [
            p for p in filtered
            if loc_lower in get_area_name(p).lower()
        ]

    if city:
        city_lower = city.lower()
        filtered = [
            p for p in filtered
            if city_lower in get_city(p).lower()
        ]

    if developer:
        developer_lower = developer.lower()
        filtered = [
            p for p in filtered
            if developer_lower in get_developer_name(p).lower()
        ]

    if bedrooms:
        filtered = [
            p for p in filtered
            if bedrooms in get_bedroom_list(p)
        ]

    if handover:
        filtered = [
            p for p in filtered
            if get_handover_code(p) == handover
        ]

    if budget_min is not None:
        filtered = [
            p for p in filtered
            if (get_property_price(p) or 0) >= budget_min
        ]

    if budget_max is not None:
        filtered = [
            p for p in filtered
            if (get_property_price(p) or 0) <= budget_max
        ]

    # BUILD DISPLAY-READY LIST
    properties_display = []

    for p in filtered:

        # Get slug for THIS property
        slug = get_property_slug(p)

        # Skip properties without a valid slug
        if not slug:
            continue

        cover_image = get_property_cover_image(p)
        title = api_text(p.get("title")) or "Luxury Property"

        properties_display.append({
            "id": p.get("id") or p.get("external_id"),
            "slug": slug,
            "title": title,
            "cover": normalize_image_url(cover_image),
            "sales_status_name": get_sales_status_name(p),
            "city": get_city(p),
            "district": get_area_name(p),
            "area_from": p.get("area_from") or p.get("area_to"),
            "property_type": get_property_type(p),
            "price_from": get_property_price(p),
            "developer": get_developer_name(p),
            "bedrooms": get_bedroom_list(p),
            "handover": get_handover(p),
        })

    # PAGINATION
    page_size = 9
    total_properties = len(properties_display)
    total_pages = (
        (total_properties + page_size - 1) // page_size
        if total_properties else 0
    )
    if total_pages and current_page > total_pages:
        current_page = total_pages

    start = (current_page - 1) * page_size
    end = start + page_size
    properties = properties_display[start:end]

    previous_page = current_page - 1 if current_page > 1 else None
    next_page = current_page + 1 if current_page < total_pages else None

    page_numbers = _build_page_numbers(current_page, total_pages)

    context = {
        "properties": properties,
        "total_properties": total_properties,
        "current_page": current_page,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "previous_page": previous_page,
        "next_page": next_page,
        "property_names": property_names,
        "locations": locations,
        "cities": cities,
        "developers": developers,
        "bedroom_options": bedroom_options,
        "handover_options": handover_options,
        "filters": {
            "property_name": property_name,
            "location": location,
            "city": city,
            "budget": budget,
            "developer": developer,
            "bedrooms": bedrooms,
            "handover": handover,
        },
        "property_status": "Ready",
    }

    return render(request, "main/ready.html", context)

# =========================================================
# LUXURY
# =========================================================

def luxury(request):

    api = XOpperpAPI()

    current_page = request.GET.get("page", 1)

    try:
        current_page = int(current_page)
    except (TypeError, ValueError):
        current_page = 1

    if current_page < 1:
        current_page = 1

    city = request.GET.get("city", "").strip()
    property_type = request.GET.get("property_type", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()

    try:
        all_properties = get_all_properties(api)
    except Exception as e:
        print("X-OPPERP LUXURY API ERROR:", e)
        all_properties = []

    # =========================================================
    # LUXURY BASE SET
    # =========================================================

    LUXURY_PRICE_THRESHOLD = 5000000  # AED

    filtered = [
        p for p in all_properties
        if get_sales_status_name(p) != "Sold Out"
        and (get_property_price(p) or 0) >= LUXURY_PRICE_THRESHOLD
    ]

    # =========================================================
    # FILTERS
    # =========================================================

    if city:
        city_lower = city.lower()

        filtered = [
            p for p in filtered
            if city_lower in get_city(p).lower()
        ]

    if property_type:
        property_type_lower = property_type.lower()

        filtered = [
            p for p in filtered
            if property_type_lower in get_property_type(p).lower()
        ]

    if min_price:
        try:
            min_p = int(min_price)

            filtered = [
                p for p in filtered
                if (get_property_price(p) or 0) >= min_p
            ]

        except ValueError:
            pass

    if max_price:
        try:
            max_p = int(max_price)

            filtered = [
                p for p in filtered
                if (get_property_price(p) or 0) <= max_p
            ]

        except ValueError:
            pass

    # =========================================================
    # BUILD DISPLAY-READY LIST
    # =========================================================

    properties_display = []

    for p in filtered:

        # IMPORTANT:
        # Generate slug for THIS property
        slug = get_property_slug(p)

        # Skip property if it has no valid slug
        if not slug:
            continue

        cover_image = get_property_cover_image(p)

        title = api_text(p.get("title")) or "Luxury Property"

        properties_display.append({
            "id": p.get("id") or p.get("external_id"),

            "slug": slug,

            "title": title,

            "cover": normalize_image_url(cover_image),

            "city": get_city(p),

            "district": get_area_name(p),

            "property_type": get_property_type(p),

            "price_from": get_property_price(p),

            "developer": get_developer_name(p),

            "bedrooms": get_bedroom_list(p),

            "handover": get_handover(p),

        })

    # =========================================================
    # PAGINATION
    # =========================================================

    page_size = 8

    total_properties = len(properties_display)

    total_pages = (
        (total_properties + page_size - 1) // page_size
        if total_properties
        else 0
    )

    if total_pages and current_page > total_pages:
        current_page = total_pages

    start = (current_page - 1) * page_size
    end = start + page_size

    properties = properties_display[start:end]

    previous_page = (
        current_page - 1
        if current_page > 1
        else None
    )

    next_page = (
        current_page + 1
        if current_page < total_pages
        else None
    )

    page_numbers = _build_page_numbers(
        current_page,
        total_pages
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {
        "properties": properties,

        "total_properties": total_properties,

        "current_page": current_page,

        "total_pages": total_pages,

        "page_numbers": page_numbers,

        "previous_page": previous_page,

        "next_page": next_page,

        "selected_city": city,

        "selected_property_type": property_type,

        "selected_min_price": min_price,

        "selected_max_price": max_price,
    }

    return render(
        request,
        "main/luxury.html",
        context
    )


# =========================================================
# BUY
# =========================================================

def buy(request):

    api = XOpperpAPI()

    current_page = request.GET.get("page", 1)
    try:
        current_page = int(current_page)
    except (TypeError, ValueError):
        current_page = 1
    if current_page < 1:
        current_page = 1

    # BASIC FILTERS
    property_name = request.GET.get("property_name", "").strip()
    property_status = request.GET.get("property_status", "").strip()
    location = request.GET.get("location", "").strip()
    budget = request.GET.get("budget", "").strip()

    # ADVANCED FILTERS
    city = request.GET.get("city", "").strip()
    developer = request.GET.get("developer", "").strip()
    bedrooms = request.GET.get("bedrooms", "").strip()
    handover = request.GET.get("handover", "").strip()

    budget_min, budget_max = parse_budget_range(budget)

    try:
        all_properties = get_all_properties(api)
    except Exception as e:
        print("X-OPPERP BUY API ERROR:", e)
        all_properties = []

    # BUY BASE SET = Off Plan + Ready, excluding Sold Out
    base = [
        p for p in all_properties
        if get_property_status_name(p) in ("Off Plan", "Ready")
        and get_sales_status_name(p) != "Sold Out"
    ]

    # DYNAMIC FILTER OPTIONS (from base, not hardcoded)
    property_names = get_distinct_property_names(base)
    property_statuses = get_distinct_property_statuses(base)
    locations = get_distinct_locations(base)
    cities = get_distinct_cities(base)
    developers = get_distinct_developers(base)
    bedroom_options = get_distinct_bedrooms(base)
    handover_options = get_distinct_handover_options(base)

    # APPLY FILTERS
    filtered = base

    if property_name:
        pname_lower = property_name.lower()
        filtered = [
            p for p in filtered
            if pname_lower in api_text(p.get("title")).lower()
        ]

    if property_status:
        pstatus_lower = property_status.lower()
        filtered = [
            p for p in filtered
            if pstatus_lower in get_property_status_name(p).lower()
        ]

    if location:
        loc_lower = location.lower()
        filtered = [
            p for p in filtered
            if loc_lower in get_area_name(p).lower()
        ]

    if city:
        city_lower = city.lower()
        filtered = [
            p for p in filtered
            if city_lower in get_city(p).lower()
        ]

    if developer:
        developer_lower = developer.lower()
        filtered = [
            p for p in filtered
            if developer_lower in get_developer_name(p).lower()
        ]

    if bedrooms:
        filtered = [
            p for p in filtered
            if bedrooms in get_bedroom_list(p)
        ]

    if handover:
        filtered = [
            p for p in filtered
            if get_handover_code(p) == handover
        ]

    if budget_min is not None:
        filtered = [
            p for p in filtered
            if (get_property_price(p) or 0) >= budget_min
        ]

    if budget_max is not None:
        filtered = [
            p for p in filtered
            if (get_property_price(p) or 0) <= budget_max
        ]

    # BUILD DISPLAY-READY LIST
    properties_display = []

    for p in filtered:

        cover_image = get_property_cover_image(p)
        title = api_text(p.get("title")) or "Luxury Property"

        properties_display.append({
            "id": p.get("id") or p.get("external_id"),
            "slug": get_property_slug(p),        
            "title": title,
            "cover": normalize_image_url(cover_image),
            "property_status_name": get_property_status_name(p),
            "city": get_city(p),
            "district": get_area_name(p),
            "area_from": p.get("area_from") or p.get("area_to"),
            "property_type": get_property_type(p),
            "price_from": get_property_price(p),
            "developer": get_developer_name(p),
            "bedrooms": get_bedroom_list(p),
            "handover": get_handover(p),
        })

    # PAGINATION
    page_size = 9
    total_properties = len(properties_display)
    total_pages = (
        (total_properties + page_size - 1) // page_size
        if total_properties else 0
    )
    if total_pages and current_page > total_pages:
        current_page = total_pages

    start = (current_page - 1) * page_size
    end = start + page_size
    properties = properties_display[start:end]

    previous_page = current_page - 1 if current_page > 1 else None
    next_page = current_page + 1 if current_page < total_pages else None

    page_numbers = _build_page_numbers(current_page, total_pages)

    context = {
        "properties": properties,
        "total_properties": total_properties,
        "current_page": current_page,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "previous_page": previous_page,
        "next_page": next_page,
        "property_names": property_names,
        "property_statuses": property_statuses,
        "locations": locations,
        "cities": cities,
        "developers": developers,
        "bedroom_options": bedroom_options,
        "handover_options": handover_options,
        "filters": {
            "property_name": property_name,
            "property_status": property_status,
            "location": location,
            "budget": budget,
            "city": city,
            "developer": developer,
            "bedrooms": bedrooms,
            "handover": handover,
        },
    }

    return render(request, "main/buy.html", context)


# =========================================================
# SIMPLE STATIC PAGES
# =========================================================

def about(request):
    return render(request, 'main/about.html')

def Jd(request):
    return render(request, 'main/jointdevelopment.html')

def propertyadvisory(request):
    return render(request, 'main/propertyadvisory.html')

def JointVentures(request):
    return render(request, 'main/jointventures.html')

def landdeal(request):
    return render(request, 'main/landdeals.html')
def contact(request):
    if request.method == "POST":

        enquiry = Enquiry.objects.create(
            form_type="contact",
            name=request.POST.get("name", "").strip(),
            email=request.POST.get("email", "").strip(),
            phone=request.POST.get("phone", "").strip(),
            message=request.POST.get("message", "").strip(),
        )

        try:
            result = send_enquiry_email(enquiry)

            print("BREVO SUCCESS:", result)

            enquiry.sent_to_brevo = True
            enquiry.save(update_fields=["sent_to_brevo"])

        except Exception as e:
            print("========== BREVO ERROR ==========")
            print("ERROR:", str(e))
            traceback.print_exc()
            print("=================================")

        return redirect(f"{reverse('thank_you')}?type=contact")

    return render(request, "main/contact.html")
def invest(request):
    return render(request, 'main/invest.html')
def investmentadvisory(request):
    return render(request, 'main/investmentadvisory.html')

def format_price_display(value):
    """AED 2.4M / AED 850K / Price on Request."""
    if value is None:
        return "Price on Request"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "Price on Request"
    if value <= 0:
        return "Price on Request"
    if value >= 1_000_000:
        m = value / 1_000_000
        return f"AED {m:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"AED {value/1_000:.0f}K"
    return f"AED {int(value):,}"

def _find_property_by_slug(all_properties, slug):

    slug = slug.strip().lower()

    for item in all_properties:

        property_slug = get_property_slug(item)

        if property_slug == slug:
            return item

    return None

def normalize_amenities(raw_amenities):

    amenities = []

    if not raw_amenities:
        return amenities

    if isinstance(raw_amenities, str):

        raw_amenities = raw_amenities.split(",")

    if not isinstance(raw_amenities, list):
        return amenities

    for item in raw_amenities:

        name = api_text(item)

        if name:
            amenities.append(name)

    return amenities


def normalize_payment_plans(prop):

    payment_plans = []

    raw_plans = prop.get(
        "payment_plans"
    ) or []

    # -----------------------------------------------------
    # API PAYMENT PLAN ARRAY
    # -----------------------------------------------------

    if isinstance(raw_plans, list):

        for index, plan in enumerate(raw_plans, start=1):

            if not isinstance(plan, dict):
                continue

            payment_plans.append({

                "name": (
                    api_text(plan.get("name"))
                    or f"Payment Plan {index}"
                ),

                "down_payment_pct": (
                    plan.get("down_payment_pct")
                ),

                "during_construction_pct": (
                    plan.get(
                        "during_construction_pct"
                    )
                ),

                "on_handover_pct": (
                    plan.get(
                        "on_handover_pct"
                    )
                ),

                "post_delivery_payment": (
                    plan.get(
                        "post_delivery_payment"
                    )
                ),

            })

    # -----------------------------------------------------
    # FALLBACK TO PRIMARY PAYMENT PLAN
    # -----------------------------------------------------

    if not payment_plans:

        has_plan = any([
            prop.get("down_payment_pct") is not None,
            prop.get("during_construction_pct") is not None,
            prop.get("on_handover_pct") is not None,
            prop.get("post_delivery_payment") is not None,
        ])

        if has_plan:

            payment_plans.append({

                "name": "Standard Payment Plan",

                "down_payment_pct": (
                    prop.get("down_payment_pct")
                ),

                "during_construction_pct": (
                    prop.get(
                        "during_construction_pct"
                    )
                ),

                "on_handover_pct": (
                    prop.get(
                        "on_handover_pct"
                    )
                ),

                "post_delivery_payment": (
                    prop.get(
                        "post_delivery_payment"
                    )
                ),

            })

    return payment_plans


def normalize_nearby_places(prop):

    places = []

    raw_places = prop.get(
        "nearby_places"
    ) or []

    if not isinstance(raw_places, list):
        return places

    for place in raw_places:

        if not isinstance(place, dict):
            continue

        name = api_text(
            place.get("name")
        )

        distance = api_text(
            place.get("distance")
        )

        if name:

            places.append({

                "name": name,

                "distance": distance,

            })

    return places
def normalize_units(raw_units):

    units = []

    if isinstance(raw_units, dict):

        raw_units = (
            raw_units.get("results")
            or raw_units.get("units")
            or []
        )

    if not isinstance(raw_units, list):
        return units

    for unit in raw_units:

        if not isinstance(unit, dict):
            continue

        bedrooms = unit.get("bedrooms")

        bedroom_label = api_text(
            unit.get("bedroom_label")
        )

        # ---------------------------------------------
        # BEDROOM DISPLAY
        # ---------------------------------------------

        if bedroom_label:

            bedroom_display = bedroom_label

        elif bedrooms == 0:

            bedroom_display = "Studio"

        elif bedrooms is not None:

            bedroom_display = str(
                bedrooms
            )

        else:

            bedroom_display = ""

        # ---------------------------------------------
        # UNIT
        # ---------------------------------------------

        units.append({

            "id": unit.get("id"),

            "unit_no": api_text(
                unit.get("unit_no")
            ),

            "floor_no": api_text(
                unit.get("floor_no")
            ),

            "bedrooms": bedrooms,

            "bedroom_label": bedroom_display,

            "bathrooms": unit.get(
                "bathrooms"
            ),

            "area": unit.get(
                "area"
            ),

            "price": unit.get(
                "price"
            ),

            "price_display": format_price_display(
                unit.get("price")
            ),

            "view": api_text(
                unit.get("view")
            ),

            "status": api_text(
                unit.get("status")
            ),

            "unit_image": normalize_image_url(
                unit.get("unit_image")
            ),

            "floor_plan_image": normalize_image_url(
                unit.get("floor_plan_image")
            ),

        })

    return units
def build_unit_types(units):

    grouped = {}

    for unit in units:

        bedroom_type = (
            unit.get("bedroom_label")
            or "Unit"
        )

        key = bedroom_type.strip().lower()

        if key not in grouped:

            grouped[key] = {

                "name": bedroom_type,

                "count": 0,

                "available_count": 0,

                "min_price": None,

                "max_price": None,

                "min_area": None,

                "max_area": None,

                "units": [],

            }

        group = grouped[key]

        group["count"] += 1

        status = (
            unit.get("status")
            or ""
        ).lower()

        if status == "available":

            group["available_count"] += 1

        price = unit.get("price")

        if price:

            try:
                price = float(price)

                if (
                    group["min_price"] is None
                    or price < group["min_price"]
                ):
                    group["min_price"] = price

                if (
                    group["max_price"] is None
                    or price > group["max_price"]
                ):
                    group["max_price"] = price

            except (
                TypeError,
                ValueError
            ):
                pass

        area = unit.get("area")

        if area:

            try:
                area = float(area)

                if (
                    group["min_area"] is None
                    or area < group["min_area"]
                ):
                    group["min_area"] = area

                if (
                    group["max_area"] is None
                    or area > group["max_area"]
                ):
                    group["max_area"] = area

            except (
                TypeError,
                ValueError
            ):
                pass

        group["units"].append(unit)

    return list(grouped.values())

def sell(request):

    if request.method == "POST":

        enquiry = Enquiry.objects.create(
            form_type="valuation",
            name=request.POST.get("name", "").strip(),
            email=request.POST.get("email", "").strip(),
            phone=request.POST.get("phone", "").strip(),
            message=request.POST.get("message", "").strip(),
            property_type=request.POST.get("property_type", "").strip(),
        )

        try:
            result = send_enquiry_email(enquiry)
            print("BREVO SUCCESS:", result)
            enquiry.sent_to_brevo = True
            enquiry.save(update_fields=["sent_to_brevo"])

        except Exception as e:
            print("========== BREVO ERROR ==========")
            print("ERROR:", str(e))
            traceback.print_exc()
            print("=================================")

        return redirect(f"{reverse('thank_you')}?type=valuation")

    return render(request, "main/sell.html")
def flipbook(request):
    return render(request, 'main/flipbook.html')


# =========================================================
# PAGINATION HELPER
# =========================================================

def _build_page_numbers(current_page, total_pages):
    page_numbers = []
    if total_pages <= 7:
        return list(range(1, total_pages + 1))

    page_numbers.append(1)
    if current_page > 4:
        page_numbers.append("...")

    start_page = max(2, current_page - 2)
    end_page = min(total_pages - 1, current_page + 2)
    for page in range(start_page, end_page + 1):
        if page not in page_numbers:
            page_numbers.append(page)

    if current_page < total_pages - 3:
        page_numbers.append("...")
    if total_pages not in page_numbers:
        page_numbers.append(total_pages)

    return page_numbers


# =========================================================
# AREA VIEW
# =========================================================

def area(request):

    api = XOpperpAPI()

    current_page = request.GET.get("page", 1)
    try:
        current_page = int(current_page)
    except (TypeError, ValueError):
        current_page = 1
    if current_page < 1:
        current_page = 1

    search_area = request.GET.get("search_area", "").strip()

    try:
        all_properties = get_all_properties(api)
    except Exception as e:
        print("X-OPPERP AREA API ERROR:", e)
        all_properties = []

    dubai_properties = []
    for p in all_properties:
        city = get_city(p).lower()
        if city == "dubai" or "dubai" in city:
            if get_sales_status_name(p).lower() != "sold out":
                dubai_properties.append(p)

    area_data = {}

    for p in dubai_properties:

        area_name = get_area_name(p)
        if not area_name:
            continue

        area_key = area_name.lower()

        if area_key not in area_data:
            area_data[area_key] = {
                "name": area_name,
                "slug": slugify(area_name),
                "image": "",
                "property_count": 0,
            }


        area_entry = area_data[area_key]
        area_entry["property_count"] += 1

        if not area_entry["image"]:
            cover_image = get_property_cover_image(p)
            if cover_image:
                area_entry["image"] = normalize_image_url(cover_image)

    areas = list(area_data.values())

    if search_area:
        search_lower = search_area.lower()
        areas = [a for a in areas if search_lower in a["name"].lower()]

    areas.sort(key=lambda x: x["property_count"], reverse=True)

    page_size = 6
    total_areas = len(areas)
    total_pages = (
        (total_areas + page_size - 1) // page_size
        if total_areas else 0
    )

    if total_pages and current_page > total_pages:
        current_page = total_pages

    start = (current_page - 1) * page_size
    end = start + page_size
    displayed_areas = areas[start:end]

    previous_page = current_page - 1 if current_page > 1 else None
    next_page = current_page + 1 if current_page < total_pages else None

    page_numbers = _build_page_numbers(current_page, total_pages)

    context = {
        "areas": displayed_areas,
        "total_areas": total_areas,
        "current_page": current_page,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "previous_page": previous_page,
        "next_page": next_page,
        "search_area": search_area,
    }

    return render(request, "main/area.html", context)
# =========================================================
# DEBUG / TEST ENDPOINT
# =========================================================



# =========================================================
# AREA DETAIL VIEW
# Add this function to views.py (e.g. right after area()).
# Shows every property whose district matches the area name,
# with the same filter set used on Buy (minus location/city,
# since both are fixed by the area itself).
# =========================================================
def get_budget_options(properties):
    """
    Same fixed brackets used on Buy, but only returns the ones
    that actually contain a property in this set — so the
    dropdown never shows an empty bracket for a small area.
    """

    brackets = [
        ("0-1000000", "Up to 1M AED"),
        ("1000000-2000000", "1M – 2M AED"),
        ("2000000-5000000", "2M – 5M AED"),
        ("5000000-10000000", "5M – 10M AED"),
        ("10000000-20000000", "10M – 20M AED"),
        ("20000000-", "20M+ AED"),
    ]

    prices = [get_property_price(p) for p in properties]
    prices = [p for p in prices if p]

    if not prices:
        return []

    options = []

    for value, label in brackets:
        lo, hi = parse_budget_range(value)
        lo = lo or 0

        if hi is None:
            match = any(price >= lo for price in prices)
        else:
            match = any(lo <= price <= hi for price in prices)

        if match:
            options.append((value, label))

    return options
def area_detail(request, area_slug):

    api = XOpperpAPI()

    current_page = request.GET.get("page", 1)

    try:
        current_page = int(current_page)
    except (TypeError, ValueError):
        current_page = 1

    if current_page < 1:
        current_page = 1

    # =====================================================
    # FILTERS
    # =====================================================

    property_name = request.GET.get(
        "property_name", ""
    ).strip()

    property_status = request.GET.get(
        "property_status", ""
    ).strip()

    budget = request.GET.get(
        "budget", ""
    ).strip()

    developer = request.GET.get(
        "developer", ""
    ).strip()

    bedrooms = request.GET.get(
        "bedrooms", ""
    ).strip()

    handover = request.GET.get(
        "handover", ""
    ).strip()

    budget_min, budget_max = parse_budget_range(
        budget
    )

    # =====================================================
    # GET PROPERTIES
    # =====================================================

    try:
        all_properties = get_all_properties(api)

    except Exception as e:

        print(
            "X-OPPERP AREA DETAIL API ERROR:",
            e
        )

        all_properties = []

    # =====================================================
    # NORMALIZE URL SLUG
    #
    # /area-detail/jvc/
    # /area-detail/palm-jumeirah/
    # /area-detail/downtown-dubai/
    # =====================================================

    area_slug = area_slug.strip().lower()

    # =====================================================
    # FIND PROPERTIES FOR THIS AREA
    # =====================================================

    base = []

    for p in all_properties:

        property_area = get_area_name(p)

        if not property_area:
            continue

        property_area_slug = slugify(
            property_area
        )

        if property_area_slug != area_slug:
            continue

        # Exclude sold-out properties
        if (
            get_sales_status_name(p)
            .strip()
            .lower()
            == "sold out"
        ):
            continue

        base.append(p)

    # =====================================================
    # AREA DISPLAY NAME
    # =====================================================

    area_display_name = (
        area_slug
        .replace("-", " ")
        .title()
    )

    area_city = ""

    # Use actual API name where available
    for p in base:

        actual_area = get_area_name(p)

        if actual_area:
            area_display_name = actual_area

        city_val = get_city(p)

        if city_val:
            area_city = city_val

        break

    # =====================================================
    # DYNAMIC FILTER OPTIONS
    # =====================================================

    property_names = (
        get_distinct_property_names(base)
    )

    property_statuses = (
        get_distinct_property_statuses(base)
    )

    developers = (
        get_distinct_developers(base)
    )

    bedroom_options = (
        get_distinct_bedrooms(base)
    )

    handover_options = (
        get_distinct_handover_options(base)
    )

    budget_options = (
        get_budget_options(base)
    )

    # =====================================================
    # APPLY FILTERS
    # =====================================================

    filtered = base

    # Property name
    if property_name:

        pname_lower = property_name.lower()

        filtered = [
            p
            for p in filtered
            if pname_lower
            in api_text(
                p.get("title")
            ).lower()
        ]

    # Property status
    if property_status:

        pstatus_lower = (
            property_status.lower()
        )

        filtered = [
            p
            for p in filtered
            if pstatus_lower
            in get_property_status_name(
                p
            ).lower()
        ]

    # Developer
    if developer:

        developer_lower = (
            developer.lower()
        )

        filtered = [
            p
            for p in filtered
            if developer_lower
            in get_developer_name(
                p
            ).lower()
        ]

    # Bedrooms
    if bedrooms:

        filtered = [
            p
            for p in filtered
            if bedrooms
            in get_bedroom_list(p)
        ]

    # Handover
    if handover:

        filtered = [
            p
            for p in filtered
            if get_handover_code(p)
            == handover
        ]

    # Budget minimum
    if budget_min is not None:

        filtered = [
            p
            for p in filtered
            if (
                get_property_price(p)
                or 0
            ) >= budget_min
        ]

    # Budget maximum
    if budget_max is not None:

        filtered = [
            p
            for p in filtered
            if (
                get_property_price(p)
                or 0
            ) <= budget_max
        ]

    # =====================================================
    # BUILD DISPLAY PROPERTIES
    # =====================================================

    properties_display = []

    for p in filtered:

        cover_image = (
            get_property_cover_image(p)
        )

        title = (
            api_text(
                p.get("title")
            )
            or "Luxury Property"
        )

        properties_display.append({

            "id": (
                p.get("id")
                or p.get("external_id")
            ),

            "slug": get_property_slug(p),

            "title": title,

            "cover": normalize_image_url(
                cover_image
            ),

            "property_status_name":
                get_property_status_name(p),

            "sales_status_name":
                get_sales_status_name(p),

            "city":
                get_city(p),

            "district":
                get_area_name(p),

            "area_from":
                p.get("area_from")
                or p.get("area_to"),

            "property_type":
                get_property_type(p),

            "price_from":
                get_property_price(p),

            "developer":
                get_developer_name(p),

            "bedrooms":
                get_bedroom_list(p),

            "handover":
                get_handover(p),
        })

    # =====================================================
    # PAGINATION
    # =====================================================

    page_size = 9

    total_properties = len(
        properties_display
    )

    total_pages = (
        (
            total_properties
            + page_size
            - 1
        )
        // page_size
        if total_properties
        else 0
    )

    if (
        total_pages
        and current_page > total_pages
    ):
        current_page = total_pages

    start = (
        current_page - 1
    ) * page_size

    end = start + page_size

    properties = properties_display[
        start:end
    ]

    previous_page = (
        current_page - 1
        if current_page > 1
        else None
    )

    next_page = (
        current_page + 1
        if current_page < total_pages
        else None
    )

    page_numbers = _build_page_numbers(
        current_page,
        total_pages
    )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        # URL slug
        "area_slug":
            area_slug,

        # Human-readable area name
        "area_name":
            area_display_name,

        "area_display_name":
            area_display_name,

        "area_city":
            area_city,

        # Properties
        "properties":
            properties,

        "total_properties":
            total_properties,

        # Pagination
        "current_page":
            current_page,

        "total_pages":
            total_pages,

        "page_numbers":
            page_numbers,

        "previous_page":
            previous_page,

        "next_page":
            next_page,

        # Filters
        "property_names":
            property_names,

        "property_statuses":
            property_statuses,

        "developers":
            developers,

        "bedroom_options":
            bedroom_options,

        "handover_options":
            handover_options,

        "budget_options":
            budget_options,

        "filters": {

            "property_name":
                property_name,

            "property_status":
                property_status,

            "budget":
                budget,

            "developer":
                developer,

            "bedrooms":
                bedrooms,

            "handover":
                handover,
        },
    }

    return render(
        request,
        "main/areadetail.html",
        context
    )

def test_opperp(request):

    api = XOpperpAPI()

    response = api.get_properties({
        "page": 1,
        "page_size": 5,
    })

    return JsonResponse(
        {
            "status_code": response.status_code,
            "success": response.ok,
            "data": response.json() if response.content else {},
        },
        status=response.status_code
    )
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
import requests
import logging

from .forms import ValuationForm, ContactForm, PropertyEnquiryForm
from .utils import send_enquiry_email

logger = logging.getLogger(__name__)


def _save_and_notify(request, form, form_type):
    enquiry = form.save(commit=False)
    enquiry.form_type = form_type
    enquiry.save()  # DB write happens regardless of Brevo's outcome

    try:
        send_enquiry_email(enquiry)
        enquiry.sent_to_brevo = True
        enquiry.save(update_fields=["sent_to_brevo"])
    except requests.exceptions.RequestException:
        logger.exception("Brevo email failed for enquiry id=%s", enquiry.id)
        # don't fail the request — the enquiry is already saved

    return enquiry


@require_POST
def submit_valuation(request):
    form = ValuationForm(request.POST)
    if form.is_valid():
        _save_and_notify(request, form, "valuation")
        messages.success(request, "Thanks! We'll send your valuation shortly.")
    else:
        messages.error(request, "Please check the form and try again.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@require_POST
def submit_contact(request):
    form = ContactForm(request.POST)
    if form.is_valid():
        _save_and_notify(request, form, "contact")
        messages.success(request, "Thanks! Your enquiry has been sent.")
    else:
        messages.error(request, "Please check the form and try again.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@require_POST
def submit_property_enquiry(request):
    form = PropertyEnquiryForm(request.POST)
    if form.is_valid():
        _save_and_notify(request, form, "property")
        messages.success(request, "Thanks! We'll get back to you about this property.")
    else:
        messages.error(request, "Please check the form and try again.")
    return redirect(request.META.get("HTTP_REFERER", "/"))

def thank_you(request):

    # Lets one thank-you page serve all your forms with a tailored message
    form_type = request.GET.get("type", "general")

    messages_map = {
        "valuation": {
            "eyebrow": "REQUEST RECEIVED",
            "title": "Your valuation",
            "title_em": "is underway.",
            "description": (
                "One of our advisors is reviewing your property details "
                "and will be in touch shortly with a considered, "
                "market-informed valuation."
            ),
        },
        "contact": {
            "eyebrow": "MESSAGE RECEIVED",
            "title": "Thank you for",
            "title_em": "reaching out.",
            "description": (
                "Your enquiry has been received. A member of our team "
                "will respond to you shortly."
            ),
        },
        "property": {
            "eyebrow": "ENQUIRY RECEIVED",
            "title": "We've got",
            "title_em": "your enquiry.",
            "description": (
                "An advisor familiar with this property will be in "
                "touch shortly with the details you requested."
            ),
        },
        "general": {
            "eyebrow": "SUBMISSION RECEIVED",
            "title": "Thank",
            "title_em": "you.",
            "description": (
                "We've received your submission and will be in touch shortly."
            ),
        },
    }

    context = messages_map.get(form_type, messages_map["general"])

    return render(request, "main/thankyou.html", context)


def property_map_search(request):

    api = XOpperpAPI()

    try:
        all_properties = get_all_properties(api)
    except Exception as e:
        print("X-OPPERP PROPERTY LIST ERROR:", e)
        all_properties = []

    q = request.GET.get("q", "").strip().lower()
    property_type = request.GET.get("property_type", "").strip().lower()
    city = request.GET.get("city", "").strip().lower()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    bedrooms = request.GET.get("bedrooms", "").strip().lower()

    def to_number(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    min_price_val = to_number(min_price)
    max_price_val = to_number(max_price)

    listings = []
    city_set = set()
    type_set = set()

    for item in all_properties:

        if get_sales_status_name(item).lower() == "sold out":
            continue

        raw_lat = item.get("latitude")
        raw_lng = item.get("longitude")

        try:
            lat = float(raw_lat)
            lng = float(raw_lng)
        except (TypeError, ValueError):
            continue

        if lat == 0 and lng == 0:
            continue

        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            continue

        item_city = (get_city(item) or "").strip()
        item_type = (get_property_type(item) or "").strip()
        item_price = get_property_price(item)
        item_slug = get_property_slug(item)
        item_name = api_text(item.get("title")) or "Luxury Property"
        item_bedrooms = get_bedroom_list(item)

        if item_city:
            city_set.add(item_city)
        if item_type:
            type_set.add(item_type)

        if q and q not in item_name.lower() and q not in item_city.lower():
            continue

        if property_type and item_type.lower() != property_type:
            continue

        if city and item_city.lower() != city:
            continue

        if min_price_val is not None and (item_price is None or item_price < min_price_val):
            continue

        if max_price_val is not None and (item_price is None or item_price > max_price_val):
            continue

        if bedrooms:
            bedroom_strs = [str(b).strip().lower() for b in item_bedrooms]
            if bedrooms not in bedroom_strs:
                continue

        listings.append({
            "id": item.get("id"),
            "slug": item_slug,
            "name": item_name,
            "place": get_area_name(item) or item_city,
            "city": item_city,
            "type": item_type or "Residence",
            "price": format_price_display(item_price),
            "price_raw": item_price,
            "bedrooms": ", ".join(item_bedrooms) if item_bedrooms else "Studio",
            "image": normalize_image_url(get_property_cover_image(item)),
            "lat": lat,
            "lng": lng,
            "url": reverse("propertydetail", args=[item_slug]) if item_slug else "",
        })

    context = {
        "listings_json": json.dumps(listings),
        "listings_count": len(listings),
        "featured_listings": listings[:3],
        "cities": sorted(city_set),
        "property_types": sorted(type_set),
        "filters": {
            "q": request.GET.get("q", ""),
            "property_type": request.GET.get("property_type", ""),
            "city": request.GET.get("city", ""),
            "min_price": min_price,
            "max_price": max_price,
            "bedrooms": request.GET.get("bedrooms", ""),
        },
    }

    return render(request, "main/property_map_search.html", context)


def blog(request, page=1):

    # ==========================================
    # NEWSLETTER SUBSCRIPTION
    # ==========================================

    if request.method == "POST":

        form_type = request.POST.get(
            "form_type",
            ""
        ).strip()

        if form_type == "newsletter":

            email = request.POST.get(
                "email",
                ""
            ).strip()

            if email:

                enquiry = Enquiry.objects.create(
                    form_type="newsletter",
                    name="Newsletter Subscriber",
                    email=email,
                    phone="",
                    message="Newsletter subscription",
                    interest="Newsletter",
                )

                print("================================")
                print("NEWSLETTER SUBSCRIBER CREATED")
                print("ID:", enquiry.id)
                print("EMAIL:", enquiry.email)
                print("================================")

                try:

                    result = send_enquiry_email(enquiry)

                    print("BREVO NEWSLETTER SUCCESS:")
                    print(result)

                    enquiry.sent_to_brevo = True

                    enquiry.save(
                        update_fields=["sent_to_brevo"]
                    )

                except Exception as e:

                    print("========== BREVO NEWSLETTER ERROR ==========")
                    print("ERROR:", str(e))
                    traceback.print_exc()
                    print("============================================")

            return redirect(
                f"{reverse('thank_you')}?type=newsletter"
            )

    # ==========================================
    # BLOG LISTING
    # ==========================================

    search_query = request.GET.get(
        "search",
        ""
    ).strip()

    sort_by = request.GET.get(
        "sort",
        "-created_at"
    )

    page_size = int(
        request.GET.get(
            "page_size",
            9
        )
    )

    posts = BlogPost.objects.all()

    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    sort_map = {
        "-publish_date": "-created_at",
        "publish_date": "created_at",
        "title": "title",
    }

    posts = posts.order_by(
        sort_map.get(
            sort_by,
            "-created_at"
        )
    )

    # First post = featured
    featured_post = posts.first()

    if featured_post:
        other_posts = posts.exclude(
            pk=featured_post.pk
        )
    else:
        other_posts = posts.none()

    paginator = Paginator(
        other_posts,
        page_size
    )

    posts_page = paginator.get_page(
        page
    )

    context = {
        "featured_post": featured_post,
        "posts": posts_page,
        "search_query": search_query,
        "sort_by": sort_by,
        "page_size": page_size,
        "current_page": posts_page.number,
    }

    return render(
        request,
        "main/blog.html",
        context
    )

def blog_detail(request, slug):

    post = get_object_or_404(
        BlogPost,
        slug=slug
    )

    if request.method == "POST":

        form_type = request.POST.get("form_type", "").strip()

        # ==========================================
        # NEWSLETTER SUBSCRIPTION
        # ==========================================

        if form_type == "newsletter":

            email = request.POST.get("email", "").strip()

            if email:

                enquiry = Enquiry.objects.create(
                    form_type="newsletter",
                    name="Newsletter Subscriber",
                    email=email,
                    phone="",
                    message="Newsletter subscription",
                    property_slug=post.slug,
                    property_name=post.title,
                    interest="Newsletter",
                )

                print("NEWSLETTER CREATED:", enquiry.id)

                try:

                    result = send_enquiry_email(enquiry)

                    print("BREVO NEWSLETTER SUCCESS:", result)

                    enquiry.sent_to_brevo = True

                    enquiry.save(
                        update_fields=["sent_to_brevo"]
                    )

                except Exception as e:

                    print("========== BREVO NEWSLETTER ERROR ==========")
                    print("ERROR:", str(e))
                    traceback.print_exc()
                    print("============================================")

            return redirect(
                f"{reverse('thank_you')}?type=newsletter"
            )

        # ==========================================
        # BLOG ENQUIRY
        # ==========================================

        enquiry = Enquiry.objects.create(
            form_type="blog",

            name=request.POST.get("name", "").strip(),

            email=request.POST.get("email", "").strip(),

            phone=request.POST.get("phone", "").strip(),

            message=request.POST.get("message", "").strip(),

            property_slug=post.slug,

            property_name=post.title,

            interest="Blog Enquiry",
        )

        print("BLOG ENQUIRY CREATED:", enquiry.id)

        try:

            result = send_enquiry_email(enquiry)

            print("BREVO SUCCESS:", result)

            enquiry.sent_to_brevo = True

            enquiry.save(
                update_fields=["sent_to_brevo"]
            )

        except Exception as e:

            print("========== BREVO ERROR ==========")
            print("ERROR:", str(e))
            traceback.print_exc()
            print("=================================")

        return redirect(
            f"{reverse('thank_you')}?type=blog"
        )

    related_posts = BlogPost.objects.exclude(
        id=post.id
    ).order_by("-created_at")[:3]

    context = {
        "post": post,
        "related_posts": related_posts,
    }

    return render(
        request,
        "main/blog_detail.html",
        context
    )
