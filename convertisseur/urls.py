from django.urls import path
from . import views

urlpatterns = [
    # Pages principales
    path('', views.methode_simple, name='methode_simple'),
    path('methode-avancee/', views.methode_avancee, name='methode_avancee'),
    path('produits/', views.produits, name='produits'),
    path('obligations/', views.obligations, name='obligations'),
    path('contact/', views.contact, name='contact'),

    # Export PDF
    path('export-pdf/', views.export_pdf, name='export_pdf'),
]