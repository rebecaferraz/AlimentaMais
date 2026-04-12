from django.db import models
 
 
# H1: Paciente
class Paciente(models.Model):
    nome       = models.CharField(max_length=255)
    email      = models.EmailField(unique=True)
    senha      = models.CharField(max_length=255)
    peso       = models.FloatField()
    altura     = models.FloatField()
    idade      = models.IntegerField()
    objetivo   = models.CharField(max_length=100)
    restricoes = models.TextField(blank=True, default='')
 
    def __str__(self):
        return self.nome
 
 
# H2: Nutricionista
class Nutricionista(models.Model):
    nome  = models.CharField(max_length=255)
    crn   = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=255)
 
    def __str__(self):
        return self.nome
 
 
# H3: Plano Alimentar
class PlanoAlimentar(models.Model):
    titulo        = models.CharField(max_length=255)
    paciente      = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='planos')
    nutricionista = models.ForeignKey(Nutricionista, on_delete=models.CASCADE, related_name='planos')
    ativo         = models.BooleanField(default=True)
    criado_em     = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f'{self.titulo} — {self.paciente.nome}'
 
 
# H3: Refeição
class Refeicao(models.Model):
    DIAS = [
        ('seg', 'Segunda'), ('ter', 'Terça'), ('qua', 'Quarta'),
        ('qui', 'Quinta'),  ('sex', 'Sexta'), ('sab', 'Sábado'), ('dom', 'Domingo'),
    ]
    plano      = models.ForeignKey(PlanoAlimentar, on_delete=models.CASCADE, related_name='refeicoes')
    nome       = models.CharField(max_length=255)
    horario    = models.TimeField()
    descricao  = models.TextField()
    dia_semana = models.CharField(max_length=3, choices=DIAS)
 
    def __str__(self):
        return f'{self.nome} ({self.dia_semana})'
 