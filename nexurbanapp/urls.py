from django.urls import path
from . import views
from django.contrib.sitemaps.views import sitemap, index
from nexurbanapp.sitemaps import sitemaps
from .views import robots_txt

urlpatterns = [
       path('', views.home, name='home'),
      # OLD URL → redirect
       path('offplan',views.offplan_old,name='offplan_old'),

       path('offplan/',views.offplan_old,name='offplan_old_slash'),

        # NEW SEO URL
       path('off-plan-properties-dubai/', views.offplan,name='offplan'),

        # Pagination
       path('off-plan-properties-dubai/page/<int:page>/',views.offplan,name='offplan_paginated'),

       path('ready', views.ready, name='ready_old'),
       path('ready/', views.ready, name='ready'),

       path('ready/page/<int:page>/', views.ready, name='ready_paginated'),

       path('about/', views.about_old, name='about_old'),
       path('about-nexurban-properties/', views.about, name='about'),

       # OLD URL → redirect
        path('contact/',views.contact_old,name='contact_old'),

  # NEW SEO URL
        path('contact-nexurban-properties/',views.contact,name='contact'),
    
        path('area/', views.area, name='area'),
        path('area/page/<int:page>/', views.area, name='area_paginated'),



        # OLD URL → redirect
        path('area-detail/<slug:area_slug>/',views.area_detail_old,name='area_detail_old'),

        # NEW SEO URL
        path('<slug:area_slug>-properties/',views.area_detail,name='area_detail'),

        # NEW SEO pagination
        path('<slug:area_slug>-properties/page/<int:page>/',views.area_detail,name='area_detail_paginated'),

      
        path("property/<slug:slug>/", views.propertydetail, name="propertydetail"),
        path('sell', views.sell, name='sell'),

        path('invest', views.invest, name='invest'),
        path('investment-advisory', views.investmentadvisory, name='investmentadvisory'),

      
        path('luxury', views.luxury, name='luxury_old'),
        path('luxury/', views.luxury, name='luxury'),
        path('luxury/page/<int:page>/', views.luxury, name='luxury_paginated'),
      

        path('joint-development', views.Jd, name='joint-development'),
        path('joint-ventures', views.JointVentures, name='joint-ventures'),


        path('property-advisory', views.propertyadvisory, name='property-advisory'),
# OLD URL → redirect
        path('land-deals',views.land_deals_old,name='land_deals_old'),

  # NEW SEO URL
        path('land-for-sale-dubai/',views.landdeal, name='land-deals'),

      #   path('flipbook', views.flipbook, name='flipbook'),


  # OLD BUY URLS → REDIRECT
        path('buy',views.buy_old,name='buy_old'),

        path('buy/',views.buy_old,name='buy_old_slash'),

  # NEW SEO BUY URL
        path('buy-properties-dubai/',views.buy,name='buy'),

  # NEW SEO PAGINATION
        path('buy-properties-dubai/page/<int:page>/',views.buy,name='buy_paginated'),


        path("test-opperp/", views.test_opperp, name="test_opperp"),
        path("thank-you/", views.thank_you, name="thank_you"),
        path("map-search/", views.property_map_search, name="property_map_search"),
  # Blog listing
        path('blog/',views.blog_old,name='blog_old'),

        path('dubai-real-estate-blog/',views.blog,name='blog'),

        path('dubai-real-estate-blog/page/<int:page>/',views.blog,name='blog_paginated'),

  # Blog detail
        path('dubai-real-estate-blog/<slug:slug>/',views.blog_detail,name='blog_detail'),

        path("sitemap.xml", sitemap, {"sitemaps": sitemaps},name="django.contrib.sitemaps.views.sitemap"),
        path('robots.txt', robots_txt, name='robots_txt'),
  ]