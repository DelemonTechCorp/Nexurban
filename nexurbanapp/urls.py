from django.urls import path
from . import views

urlpatterns = [
       path('', views.home, name='home'),
       path('offplan', views.offplan, name='offplan'),
       path('ready', views.ready, name='ready'),
       path('about/', views.about, name='about'),
       path('contact/', views.contact, name='contact'),
       path('area/', views.area, name='area'),
      path('area-detail/<slug:area_slug>/', views.area_detail, name='area_detail'),

      path("property/<slug:slug>/", views.propertydetail, name="propertydetail"),
      path('sell', views.sell, name='sell'),
      path('invest', views.invest, name='invest'),
       path('investment-advisory', views.investmentadvisory, name='investmentadvisory'),
      path('luxury', views.luxury, name='luxury'),
      path('joint-development', views.Jd, name='joint-development'),
      path('joint-ventures', views.JointVentures, name='joint-ventures'),
        path('property-advisory', views.propertyadvisory, name='property-advisory'),
      path('land-deals', views.landdeal, name='land-deals'),
      path('flipbook', views.flipbook, name='flipbook'),
      path('buy', views.buy, name='buy'),
      path("test-opperp/", views.test_opperp, name="test_opperp"),
      path("thank-you/", views.thank_you, name="thank_you"),
      path("map-search/", views.property_map_search, name="property_map_search"),
    

      path('blog/', views.blog, name='blog'),
      path('blog/page/<int:page>/', views.blog, name='blog_paginated'),
      path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
  ]