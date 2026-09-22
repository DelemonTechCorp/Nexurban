from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import BlogPost

# Optional models: loaded only if they exist in models.py.
# Python is case-sensitive, so the class is most likely "Area", not "area".
try:
    from .models import Area
except ImportError:
    Area = None

try:
    from .models import Property
except ImportError:
    Property = None


def _lastmod(obj):
    """Return the best available timestamp field on an object."""
    for field in ("updated_at", "modified_at", "updated", "created_at", "created", "date"):
        value = getattr(obj, field, None)
        if value:
            return value
    return None


def _has_field(model, name):
    return any(f.name == name for f in model._meta.get_fields())


class StaticViewSitemap(Sitemap):
    protocol = "https"

    # (url_name, priority, changefreq)
    pages = [
        ("home", 1.0, "daily"),
        ("offplan", 0.9, "daily"),
        ("ready", 0.9, "daily"),
        ("buy", 0.9, "daily"),
        ("luxury", 0.8, "weekly"),
        ("area", 0.8, "weekly"),
        ("property_map_search", 0.7, "weekly"),
        ("sell", 0.7, "monthly"),
        ("invest", 0.7, "monthly"),
        ("investmentadvisory", 0.7, "monthly"),
        ("property-advisory", 0.7, "monthly"),
        ("joint-development", 0.6, "monthly"),
        ("joint-ventures", 0.6, "monthly"),
        ("land-deals", 0.6, "monthly"),
        ("flipbook", 0.5, "monthly"),
        ("blog", 0.8, "daily"),
        ("about", 0.5, "monthly"),
        ("contact", 0.5, "monthly"),
    ]
    # Deliberately excluded: test_opperp, thank_you, blog_paginated

    def items(self):
        return self.pages

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class BlogSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return BlogPost.objects.exclude(slug__isnull=True).exclude(slug="").order_by("-pk")

    def location(self, obj):
        return reverse("blog_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return _lastmod(obj)


class AreaSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Area.objects.exclude(slug__isnull=True).exclude(slug="").order_by("pk")

    def location(self, obj):
        return reverse("area_detail", kwargs={"area_slug": obj.slug})

    def lastmod(self, obj):
        return _lastmod(obj)


class PropertySitemap(Sitemap):
    protocol = "https"
    changefreq = "daily"
    priority = 0.8
    limit = 5000

    def items(self):
        return Property.objects.exclude(slug__isnull=True).exclude(slug="").order_by("-pk")

    def location(self, obj):
        return reverse("propertydetail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return _lastmod(obj)


sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogSitemap,
}

if Area is not None and _has_field(Area, "slug"):
    sitemaps["areas"] = AreaSitemap

if Property is not None and _has_field(Property, "slug"):
    sitemaps["properties"] = PropertySitemap