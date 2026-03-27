from django import forms
from .models import Paciente

class PacienteForm(forms.ModelForm):
    senha = forms.CharField(widget=forms.PasswordInput)
    confirmar_senha = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Paciente
        fields = [
            'senha',
            'peso',
            'altura',
            'idade',
            'objetivo',
            'restricoes'
        ]

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get("senha")
        confirmar = cleaned_data.get("confirmar_senha")

        if senha != confirmar:
            raise forms.ValidationError("As senhas não coincidem")