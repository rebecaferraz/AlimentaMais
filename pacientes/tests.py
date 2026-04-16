from django.test import TestCase, Client
from .models import Paciente, Nutricionista, PlanoAlimentar


class CenarioNegativoPacienteSemPlanoBDD(TestCase):
    """
    Cenário 2 (Negativo): Paciente sem plano cadastrado
    
    Dado que: o paciente 'Carlos Souza' está logado e não possui nenhum plano alimentar associado à sua conta
    Quando: o paciente acessa a seção 'Meu Plano Alimentar'
    Então: o sistema consulta o banco de dados e não encontra nenhum plano vinculado
    E: é exibida a mensagem 'Nenhum plano alimentar disponível. Aguarde seu nutricionista criar seu plano.'
    """
    
    def setUp(self):
        """Dado: criar um paciente para teste"""
        self.client = Client()
        self.paciente = Paciente.objects.create(
            nome='Carlos Souza',
            email='carlos@example.com',
            senha='senha123456',
            peso=75.0,
            altura=1.75,
            idade=30,
            objetivo='Ganhar massa muscular',
            restricoes='Sem intolerâncias'
        )
    
    def test_paciente_sem_plano_vê_mensagem_correta(self):
        """Quando: o paciente acessa a seção 'Meu Plano Alimentar'"""
        # Dado paciente logado - configurar sessão manualmente
        session = self.client.session
        session['paciente_id'] = self.paciente.id
        session['tipo'] = 'paciente'
        session.save()
        
        # Então: acessa o painel
        response = self.client.get('/painel/')
        
        # Então: verifica a resposta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pacientes/painel_paciente.html')
    
    def test_banco_de_dados_é_consultado_para_plano_ativo(self):
        """Então: o sistema consulta o banco de dados e não encontra nenhum plano"""
        # Verifica que não há planos ativos para o paciente
        plano_ativo = self.paciente.planos.filter(ativo=True).first()
        self.assertIsNone(plano_ativo, "Paciente não deve ter plano ativo")
    
    def test_mensagem_exata_é_exibida(self):
        """E: é exibida a mensagem correta"""
        # Dado paciente logado - configurar sessão manualmente
        session = self.client.session
        session['paciente_id'] = self.paciente.id
        session['tipo'] = 'paciente'
        session.save()
        
        # Então: acessa o painel
        response = self.client.get('/painel/')
        
        # E: verifica se a mensagem exata aparece no conteúdo
        self.assertEqual(response.status_code, 200)
        conteudo = response.content.decode('utf-8')
        self.assertIn('Nenhum plano alimentar disponível.', conteudo)
        self.assertIn('Aguarde seu nutricionista criar seu plano.', conteudo)
    
    def test_paciente_com_plano_nao_vê_mensagem_de_vazio(self):
        """Testa contraste: paciente COM plano não vê a mensagem de vazio"""
        # Criar um nutricionista
        nutricionista = Nutricionista.objects.create(
            nome='Dr. João',
            crn='123456',
            email='joao@example.com',
            senha='senha123456'
        )
        
        # Criar um plano alimentar ativo
        plano = PlanoAlimentar.objects.create(
            titulo='Plano de Ganho de Massa',
            paciente=self.paciente,
            nutricionista=nutricionista,
            ativo=True
        )
        
        # Dado paciente logado - configurar sessão manualmente
        session = self.client.session
        session['paciente_id'] = self.paciente.id
        session['tipo'] = 'paciente'
        session.save()
        
        # Quando: acessa o painel
        response = self.client.get('/painel/')
        
        # Então: não vê a mensagem de vazio
        self.assertEqual(response.status_code, 200)
        conteudo = response.content.decode('utf-8')
        self.assertNotIn('Nenhum plano alimentar disponível.', conteudo)
        self.assertIn(plano.titulo, conteudo)
