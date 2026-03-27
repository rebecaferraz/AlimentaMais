from django.shortcuts import render, redirect
from .forms import PacienteForm

def cadastro_paciente(request):
    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('painel_paciente')
    else:
        form = PacienteForm()

    return render(request, 'pacientes/cadastro.html', {'form': form})