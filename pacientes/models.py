from django.db import models
from django.contrib.auth.models import User

class Paciente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    idade = models.IntegerField()
    peso = models.FloatField()
    altura = models.FloatField()
    objetivo = models.CharField(max_length=200)
    restricoes = models.TextField()
    
    def __str__(self):
        return self.user.username