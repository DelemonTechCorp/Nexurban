from django.urls import path
from django.views.generic import RedirectView
from . import views
from django.contrib.sitemaps.views import sitemap
from nexurbanapp.sitemaps import sitemaps
from .views import robots_txt

urlpatterns = [

    # ---------- 301 REDIRECTS (keep these at the very top) ----------
    path(
        'al-barsha-south-fourth-properties/',
        RedirectView.as_view(url='/al-barsha-1-properties/', permanent=True),
    ),
    path(
        'aljadaf-properties/',
        RedirectView.as_view(url='/al-jaddaf-properties/', permanent=True),
    ),
    path(
    'al-jadaf-properties/',
    RedirectView.as_view(url='/al-jaddaf-properties/', permanent=True),
),

    # ---------- HOME ----------
    path('', views.home, name='home'),

    # ---------- OFF-PLAN ----------
    path('offplan', views.offplan_old, name='offplan_old'),
    path('offplan/', views.offplan_old, name='offplan_old_slash'),
    path('off-plan-properties-dubai/', views.offplan, name='offplan'),
    path('off-plan-properties-dubai/page/<int:page>/', views.offplan, name='offplan_paginated'),

    # ---------- READY ----------
    path('ready', views.ready, name='ready_old'),
    path('ready/', views.ready, name='ready'),
    path('ready/page/<int:page>/', views.ready, name='ready_paginated'),

    # ---------- ABOUT / CONTACT ----------
    path('about/', views.about_old, name='about_old'),
    path('about-nexurban-properties/', views.about, name='about'),
    path('contact/', views.contact_old, name='contact_old'),
    path('contact-nexurban-properties/', views.contact, name='contact'),

    # ---------- AREA ----------
      
    path('area/', RedirectView.as_view(pattern_name='area', permanent=True), name='area_old'),
    path('area/page/<int:page>/', RedirectView.as_view(pattern_name='area_paginated', permanent=True), name='area_paginated_old'),

    path('dubai-communities/', views.area, name='area'),
    path('dubai-communities/page/<int:page>/', views.area, name='area_paginated'),
    path('area-detail/<slug:area_slug>/', views.area_detail_old, name='area_detail_old'),
    path('<slug:area_slug>-properties/', views.area_detail, name='area_detail'),
    path('<slug:area_slug>-properties/page/<int:page>/', views.area_detail, name='area_detail_paginated'),

    # ---------- PROPERTY ----------
    path('property/<slug:slug>/', views.propertydetail, name='propertydetail'),

    # ---------- OTHER PAGES ----------
    path('sell', views.sell, name='sell'),
    path('invest', views.invest, name='invest'),
    path('investment-advisory', views.investmentadvisory, name='investmentadvisory'),

    path('luxury', views.luxury, name='luxury_old'),
    path('luxury/', views.luxury, name='luxury'),
    path('luxury/page/<int:page>/', views.luxury, name='luxury_paginated'),

    path('joint-development', views.Jd, name='joint-development'),
    path('joint-ventures', views.JointVentures, name='joint-ventures'),
    path('property-advisory', views.propertyadvisory, name='property-advisory'),

    path('land-deals', views.land_deals_old, name='land_deals_old'),
    path('land-for-sale-dubai/', views.landdeal, name='land-deals'),

    path('buy', views.buy_old, name='buy_old'),
    path('buy/', views.buy_old, name='buy_old_slash'),
    path('buy-properties-dubai/', views.buy, name='buy'),
    path('buy-properties-dubai/page/<int:page>/', views.buy, name='buy_paginated'),

    path('test-opperp/', views.test_opperp, name='test_opperp'),
    path('thank-you/', views.thank_you, name='thank_you'),
    path('map-search/', views.property_map_search, name='property_map_search'),

    path('blog/', views.blog_old, name='blog_old'),
    path('dubai-real-estate-blog/', views.blog, name='blog'),
    path('dubai-real-estate-blog/page/<int:page>/', views.blog, name='blog_paginated'),
    path('dubai-real-estate-blog/<slug:slug>/', views.blog_detail, name='blog_detail'),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
]