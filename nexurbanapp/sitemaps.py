from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import BlogPost
from .services import XOpperpAPI, get_all_properties


# =========================================================
# STATIC PAGES
# =========================================================

class StaticViewSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "home",
            "offplan",
            "ready",
            "about",
            "contact",
            "area",
            "sell",
            "invest",
            "investmentadvisory",
            "luxury",
            "joint-development",
            "joint-ventures",
            "property-advisory",
            "land-deals",
            "flipbook",
            "buy",
            "property_map_search",
        ]

    def location(self, item):
        return reverse(item)


# =========================================================
# BLOG DETAIL PAGES
# =========================================================

class BlogSitemap(Sitemap):
    protocol = "https"
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return (
            BlogPost.objects
            .exclude(slug__isnull=True)
            .exclude(slug="")
            .order_by("-pk")
        )

    def location(self, obj):
        return reverse(
            "blog_detail",
            kwargs={
                "slug": obj.slug
            }
        )

    def lastmod(self, obj):
        for field in [
            "updated_at",
            "modified_at",
            "created_at",
            "created",
        ]:
            value = getattr(obj, field, None)

            if value:
                return value

        return None


# =========================================================
# PROPERTY DETAIL PAGES
# =========================================================

class PropertySitemap(Sitemap):
    protocol = "https"
    changefreq = "daily"
    priority = 0.9

    def items(self):
        api = XOpperpAPI()

        properties = get_all_properties(api)

        # Only properties having slug
        return [
            obj
            for obj in properties
            if obj.get("slug")
        ]

    def location(self, obj):
        return reverse(
            "propertydetail",
            kwargs={
                "slug": obj["slug"]
            }
        )

    def lastmod(self, obj):
        for field in [
            "updated_at",
            "modified_at",
            "updated",
            "created_at",
            "created",
        ]:
            value = obj.get(field)

            if value:
                return value

        return None


# =========================================================
# SITEMAP REGISTRY
# =========================================================

sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogSitemap,
    "properties": PropertySitemap,
}