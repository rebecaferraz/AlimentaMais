from django import forms
from .models import Paciente, MetaNutricional

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


class MetaNutricionalForm(forms.ModelForm):
    class Meta:
        model = MetaNutricional
        fields = ['calorias_diarias', 'proteina', 'carboidratos']

    def clean_calorias_diarias(self):
        calorias = self.cleaned_data.get('calorias_diarias')
        if calorias is not None and calorias <= 0:
            raise forms.ValidationError('O valor de calorias deve ser um número positivo')
        return calorias

    def clean(self):
        cleaned_data = super().clean()
        campos = ['calorias_diarias', 'proteina', 'carboidratos']
        if any(cleaned_data.get(c) is None for c in campos):
            raise forms.ValidationError('Todos os campos de meta são obrigatórios')
        return cleaned_data