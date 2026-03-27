from django.urls import path
from .views import cadastro_paciente

urlpatterns = [
    path('cadastro/', cadastro_paciente, name='cadastro_paciente'),
]