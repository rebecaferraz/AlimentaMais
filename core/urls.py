from django.urls import path
from . import views

urlpatterns = [
    path('nutritionist/register/', views.register_nutritionist),
    path('mealplan/create/', views.create_mealplan),
]