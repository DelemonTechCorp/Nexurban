import logging
import math

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from .models import BlogPost
from .services import XOpperpAPI, get_all_properties
from .views import (
    get_property_slug,
    get_area_name,
    get_city,
    get_property_status_name,
    get_sales_status_name,
)

logger = logging.getLogger(__name__)

BLOG_PER_PAGE = 9


def parse_date(value):
    if not value:
        return None
    try:
        return parse_datetime(str(value))
    except (ValueError, TypeError):
        return None


def fetch_all():
    try:
        return get_all_properties(XOpperpAPI())
    except Exception:
        logger.exception("Sitemap: XOpperp fetch failed")
        return []


def is_sold_out(p):
    return get_sales_status_name(p).strip().lower() == "sold out"


class BaseSitemap(Sitemap):
    protocol = "http" if settings.DEBUG else "https"


class StaticViewSitemap(BaseSitemap):
    changefreq = "weekly"

    PRIORITIES = {
        "home": 1.0, "offplan": 0.9, "ready": 0.9,
        "buy": 0.9, "blog": 0.8, "property_map_search": 0.8,
    }

    def items(self):
        return [
            "home", "offplan", "ready", "buy", "sell", "invest",
            "investmentadvisory", "luxury", "joint-development",
            "joint-ventures", "property-advisory", "land-deals",
            "flipbook", "about", "contact", "area", "blog",
            "property_map_search",
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.PRIORITIES.get(item, 0.7)


class PropertySitemap(BaseSitemap):
    changefreq = "daily"
    priority = 0.9
    limit = 5000

    def items(self):
        seen = set()
        items = []
        for p in fetch_all():
            if get_property_status_name(p) not in ("Off Plan", "Ready"):
                continue
            if is_sold_out(p):
                continue
            slug = get_property_slug(p)
            if slug and slug not in seen:
                seen.add(slug)
                items.append({"slug": slug, "created_at": p.get("created_at")})
        return items

    def location(self, item):
        return reverse("propertydetail", kwargs={"slug": item["slug"]})

    def lastmod(self, item):
        return parse_date(item["created_at"])


class AreaSitemap(BaseSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        slugs = set()
        for p in fetch_all():
            if "dubai" not in get_city(p).lower():
                continue
            if is_sold_out(p):
                continue
            name = get_area_name(p)
            if name:
                slugs.add(slugify(name))
        return sorted(slugs)

    def location(self, slug):
        return reverse("area_detail", kwargs={"area_slug": slug})


class BlogPostSitemap(BaseSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return BlogPost.objects.exclude(slug="").order_by("-created_at")

    def location(self, obj):
        return reverse("blog_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return getattr(obj, "updated_at", None) or obj.created_at


class BlogListingSitemap(BaseSitemap):
    changefreq = "daily"
    priority = 0.6

    def items(self):
        total = BlogPost.objects.exclude(slug="").count()
        pages = math.ceil(total / BLOG_PER_PAGE) if total else 0
        return list(range(2, pages + 1))

    def location(self, page):
        return reverse("blog_paginated", kwargs={"page": page})


sitemaps = {
    "static": StaticViewSitemap,
    "properties": PropertySitemap,
    "areas": AreaSitemap,
    "blog": BlogPostSitemap,
    "blog-pages": BlogListingSitemap,
}