from django.urls import path
from . import views

urlpatterns = [
    path('', views.calculer, name='calculer'),
    path('supprimer/<int:id>/', views.supprimer_historique, name='supprimer_historique'),
]