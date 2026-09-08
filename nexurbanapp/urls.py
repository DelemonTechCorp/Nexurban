from django.urls import path
from . import views

urlpatterns = [
       path('', views.home, name='home'),
       path('offplan', views.offplan, name='offplan'),
       path('ready', views.ready, name='ready'),
       path('about/', views.about, name='about'),
       path('contact/', views.contact, name='contact'),
       path('area/', views.area, name='area'),
       path('area_detail/<str:area_name>/', views.area_detail, name='area_detail'),
path("property/<slug:slug>/", views.propertydetail, name="propertydetail"),
      path('sell', views.sell, name='sell'),
      path('luxury', views.luxury, name='luxury'),
      path('joint-development', views.Jd, name='joint-development'),
      path('joint-ventures', views.JointVentures, name='joint-ventures'),
        path('property-advisory', views.propertyadvisory, name='property-advisory'),
      path('land-deals', views.landdeal, name='land-deals'),
      path('flipbook', views.flipbook, name='flipbook'),
      path('buy', views.buy, name='buy'),
      path("test-opperp/", views.test_opperp, name="test_opperp"),
      
]