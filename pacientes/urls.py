from django.urls import path
from . import views
 
urlpatterns = [
    path('',              views.login,               name='login'),
    path('cadastro/',     views.cadastro,             name='cadastro'),
    path('painel/',       views.painel_paciente,      name='painel_paciente'),
    path('marcar-consumida/', views.marcar_consumida, name='marcar_consumida'),
    path('nutricionista/',views.painel_nutricionista, name='painel_nutricionista'),
    path('plano/criar/',  views.criar_plano,          name='criar_plano'),
    path('esqueci-senha/',views.esqueci_senha,        name='esqueci_senha'),
    path('paciente/<int:paciente_id>/', views.perfil_paciente, name='perfil_paciente'),
]