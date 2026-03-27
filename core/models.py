from django.db import models

# H2: Nutricionista
class Nutritionist(models.Model):
    name = models.CharField(max_length=255)
    crn = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # você pode adicionar hash depois

    def __str__(self):
        return self.name

# H3: Paciente
class Patient(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name

# H3: Plano Alimentar
class MealPlan(models.Model):
    title = models.CharField(max_length=255)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='plans')
    meals = models.JSONField()  # lista de refeições

    def __str__(self):
        return f"{self.title} - {self.patient.name}"
    