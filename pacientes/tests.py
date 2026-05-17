from importlib import import_module
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from django.utils import timezone
from django.test import TestCase
from django.urls import reverse
from datetime import timedelta

from pacientes.models import (
    Paciente, Nutricionista, PlanoAlimentar, Refeicao, MetaNutricional,
    ConsumoRefeicao,
)


def criar_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


class BaseSeleniumTest(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = criar_driver()
        cls.driver.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        self.driver.delete_all_cookies()
        self.driver.get('about:blank')

    def get(self, path):
        self.driver.get(f'{self.live_server_url}{path}')

    def corpo(self):
        return self.driver.find_element(By.TAG_NAME, 'body').text

    def aguardar_texto(self, texto, timeout=25):
        WebDriverWait(self.driver, timeout,
                      ignored_exceptions=[StaleElementReferenceException]).until(
            lambda d: texto in d.find_element(By.TAG_NAME, 'body').text
        )

    def preencher(self, name, value):
        el = self.driver.find_element(By.NAME, name)
        el.clear()
        el.send_keys(str(value))

    def submeter(self):
        self.driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

    def injetar_sessao(self, **dados):
        """Injeta sessão Django diretamente no browser, sem precisar de login via UI."""
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        for k, v in dados.items():
            store[k] = v
        store.save()
        self.get('/')
        self.driver.add_cookie({
            'name': settings.SESSION_COOKIE_NAME,
            'value': store.session_key,
        })

    def login(self, email, senha):
        self.get('/')
        url_antes = self.driver.current_url
        self.preencher('email', email)
        self.preencher('senha', senha)
        self.submeter()
        WebDriverWait(self.driver, 10).until(
            lambda d: d.current_url != url_antes
        )

    def cadastrar_paciente_ui(self, nome, email, senha, confirmar=None,
                               peso='70', altura='1.70', idade='25'):
        self.get('/cadastro/')
        self.preencher('nome', nome)
        self.preencher('email', email)
        self.preencher('senha', senha)
        self.preencher('confirmar_senha', confirmar or senha)
        self.preencher('peso', peso)
        self.preencher('altura', altura)
        self.preencher('idade', idade)
        self.submeter()

    def cadastrar_nutricionista_ui(self, nome, crn, email, senha):
        self.get('/cadastro/')
        self.driver.find_element(By.ID, 'btn-nutri').click()
        self.preencher('nome', nome)
        self.preencher('crn', crn)
        self.preencher('email', email)
        self.preencher('senha', senha)
        self.preencher('confirmar_senha', senha)
        self.submeter()

    # helpers para criar dados via ORM
    def criar_nutri(self, nome='Dra. Ana', crn='12345-PE',
                    email='ana@nutri.com', senha='senha123'):
        return Nutricionista.objects.create(
            nome=nome, crn=crn, email=email, senha=senha
        )

    def criar_paciente(self, nutri, nome='João Silva',
                        email='joao@email.com', senha='senha123'):
        return Paciente.objects.create(
            nome=nome, email=email, senha=senha,
            peso=70, altura=1.70, idade=25,
            objetivo='emagrecimento', nutricionista=nutri
        )

    def criar_plano(self, paciente, nutri, titulo='Plano Teste', defasagem_dias=0):
        plano = PlanoAlimentar.objects.create(
            titulo=titulo, paciente=paciente,
            nutricionista=nutri, ativo=True
        )
        if defasagem_dias:
            PlanoAlimentar.objects.filter(id=plano.id).update(
                atualizado_em=timezone.now() - timedelta(days=defasagem_dias)
            )
            plano.refresh_from_db()
        return plano

    def criar_refeicao(self, plano, nome='Café da manhã', dia='seg'):
        return Refeicao.objects.create(
            plano=plano, nome=nome,
            horario='08:00', descricao='Pão integral e ovo',
            dia_semana=dia
        )

    def remover_required(self, seletor_css):
        self.driver.execute_script(
            f"document.querySelector('{seletor_css}').removeAttribute('required')"
        )

    def remover_atributo(self, seletor_css, atributo):
        self.driver.execute_script(
            f"document.querySelector('{seletor_css}').removeAttribute('{atributo}')"
        )

    def post_via_js(self, action, campos):
        """Submete um POST via JavaScript com os campos informados."""
        csrf = self.driver.execute_script(
            "return document.cookie.match(/csrftoken=([^;]+)/)[1]"
        )
        inputs = ''.join(
            f"var i{i}=document.createElement('input');"
            f"i{i}.name='{k}';i{i}.value='{v}';f.appendChild(i{i});"
            for i, (k, v) in enumerate(campos.items())
        )
        self.driver.execute_script(f"""
            var f=document.createElement('form');
            f.method='POST';
            f.action='{self.live_server_url}{action}';
            var c=document.createElement('input');
            c.name='csrfmiddlewaretoken';c.value='{csrf}';f.appendChild(c);
            {inputs}
            document.body.appendChild(f);f.submit();
        """)


# =============================================================================
# H1 — CADASTRO DE PACIENTE
# =============================================================================

class H1CadastroPacienteTest(BaseSeleniumTest):

    def test_cenario1_cadastro_com_sucesso(self):
        """Cenário 1 (Positivo): conta criada e redirecionada para login com mensagem"""
        self.cadastrar_paciente_ui(
            nome='Maria Silva',
            email='maria@email.com',
            senha='senhaforte1'
        )
        self.aguardar_texto('Conta criada com sucesso')

    def test_cenario2_email_ja_cadastrado(self):
        """Cenário 2 (Negativo): e-mail já existente exibe mensagem de erro"""
        nutri = self.criar_nutri()
        self.criar_paciente(nutri, email='joao@email.com')

        self.cadastrar_paciente_ui(
            nome='Outro João',
            email='joao@email.com',
            senha='senhaforte1'
        )
        self.aguardar_texto('Este e-mail já está cadastrado')

    def test_cenario3_senha_fraca(self):
        """Cenário 3 (Negativo): senha com menos de 8 caracteres é rejeitada"""
        self.cadastrar_paciente_ui(
            nome='Maria Silva',
            email='maria@email.com',
            senha='curta'
        )
        self.aguardar_texto('pelo menos 8 caracteres')

    def test_senhas_nao_coincidem(self):
        """Extra: confirmar senha diferente da senha exibe erro"""
        self.cadastrar_paciente_ui(
            nome='Maria Silva',
            email='maria@email.com',
            senha='senhaforte1',
            confirmar='outrasenha'
        )
        self.aguardar_texto('senhas não coincidem')


# =============================================================================
# H2 — CADASTRO DE NUTRICIONISTA
# =============================================================================

class H2CadastroNutricionistaTest(BaseSeleniumTest):

    def test_cenario1_cadastro_com_sucesso(self):
        """Cenário 1 (Positivo): nutricionista cadastrada e redirecionada com boas-vindas"""
        self.cadastrar_nutricionista_ui(
            nome='Dra. Ana',
            crn='12345-PE',
            email='ana@nutri.com',
            senha='senhaforte1'
        )
        self.aguardar_texto('Bem-vindo(a) ao Alimenta+')

    def test_cenario2_crn_obrigatorio(self):
        """Cenário 2 (Negativo): CRN vazio exibe mensagem de campo obrigatório"""
        self.get('/cadastro/')
        self.driver.find_element(By.ID, 'btn-nutri').click()
        self.driver.find_element(By.NAME, 'nome').send_keys('Dra. Ana')
        self.driver.find_element(By.NAME, 'email').send_keys('ana@nutri.com')
        self.driver.find_element(By.NAME, 'senha').send_keys('senhaforte1')
        self.driver.find_element(By.NAME, 'confirmar_senha').send_keys('senhaforte1')
        self.remover_required('#crn')
        self.driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        self.aguardar_texto('CRN é obrigatório')

    def test_cenario3_crn_duplicado(self):
        """Cenário 3 (Negativo): CRN já cadastrado exibe mensagem de erro"""
        self.criar_nutri(crn='12345-PE')
        self.cadastrar_nutricionista_ui(
            nome='Outra Nutri',
            crn='12345-PE',
            email='outra@nutri.com',
            senha='senhaforte1'
        )
        self.aguardar_texto('CRN já está cadastrado')


# =============================================================================
# H3 — CRIAR PLANO ALIMENTAR
# =============================================================================

class H3CriarPlanoTest(BaseSeleniumTest):

    def setUp(self):
        super().setUp()
        self.nutri = self.criar_nutri()
        self.paciente = self.criar_paciente(self.nutri)

    def _abrir_criar_plano(self):
        self.login('ana@nutri.com', 'senha123')
        self.get('/plano/criar/')

    def test_cenario1_plano_criado_com_sucesso(self):
        """Cenário 1 (Positivo): plano criado e associado ao paciente"""
        self._abrir_criar_plano()

        self.driver.execute_script(f"""
            document.querySelector('[name=titulo]').value = 'Plano Emagrecimento';
            document.querySelector('[name=paciente_id]').value = '{self.paciente.id}';
            document.querySelector('[name=refeicao_nome]').value = 'Cafe da manha';
            document.querySelector('[name=refeicao_horario]').value = '08:00';
            document.querySelector('[name=refeicao_descricao]').value = 'Pao integral';
        """)
        self.driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

        self.aguardar_texto('criado com sucesso')
        self.assertTrue(PlanoAlimentar.objects.filter(titulo='Plano Emagrecimento').exists())

    def test_cenario2_plano_sem_refeicao(self):
        """Cenário 2 (Negativo): plano sem refeições não é salvo"""
        self._abrir_criar_plano()

        self.driver.find_element(By.NAME, 'titulo').send_keys('Plano Vazio')
        Select(self.driver.find_element(By.NAME, 'paciente_id')).select_by_value(
            str(self.paciente.id)
        )
        self.driver.execute_script("""
            document.querySelector('[name=refeicao_nome]').removeAttribute('required');
            document.querySelector('[name=refeicao_nome]').value = '';
            document.querySelector('[name=refeicao_horario]').removeAttribute('required');
            document.querySelector('[name=refeicao_descricao]').removeAttribute('required');
        """)
        self.driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

        self.aguardar_texto('ao menos uma refeição')
        self.assertFalse(PlanoAlimentar.objects.filter(titulo='Plano Vazio').exists())

    def test_cenario3_paciente_nao_encontrado(self):
        """Cenário 3 (Negativo): submit sem paciente selecionado exibe erro"""
        self._abrir_criar_plano()

        # preenche campos obrigatórios via JS para não bloquear HTML5 validation
        self.driver.execute_script("""
            document.querySelector('[name=titulo]').value = 'Plano Fantasma';
            document.querySelector('[name=paciente_id]').removeAttribute('required');
            document.querySelector('[name=paciente_id]').value = '';
            document.querySelector('[name=refeicao_nome]').value = 'Cafe';
            document.querySelector('[name=refeicao_horario]').value = '08:00';
            document.querySelector('[name=refeicao_descricao]').value = 'Teste';
        """)
        self.driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()

        self.aguardar_texto('Paciente não encontrado')


# =============================================================================
# H4 — VISUALIZAR PLANO ALIMENTAR
# =============================================================================

class H4VisualizarPlanoTest(BaseSeleniumTest):

    def setUp(self):
        super().setUp()
        self.nutri = self.criar_nutri()
        self.paciente = self.criar_paciente(self.nutri)

    def test_cenario1_plano_exibido_com_sucesso(self):
        """Cenário 1 (Positivo): refeições organizadas por dia aparecem no painel"""
        plano = self.criar_plano(self.paciente, self.nutri)
        self.criar_refeicao(plano, nome='Almoço', dia='seg')

        self.injetar_sessao(paciente_id=self.paciente.id, tipo='paciente')  
        self.get('/painel/') 

        corpo = self.corpo()
        self.assertIn('Meu Plano Alimentar', corpo)
        self.assertIn('Almoço', corpo)
        self.assertIn('Segunda', corpo)

    def test_cenario2_sem_plano_cadastrado(self):
        """Cenário 2 (Negativo): sem plano exibe mensagem de espera"""
        self.injetar_sessao(paciente_id=self.paciente.id, tipo='paciente')  # ← troca
        self.get('/painel/') 
        self.aguardar_texto('Nenhum plano alimentar disponível')

    def test_cenario3_aviso_plano_desatualizado(self):
        """Cenário 3 (Neutro): plano com mais de 30 dias exibe aviso"""
        plano = self.criar_plano(self.paciente, self.nutri, defasagem_dias=31)
        self.criar_refeicao(plano)

        self.injetar_sessao(paciente_id=self.paciente.id, tipo='paciente')  # ← troca
        self.get('/painel/') 
        self.aguardar_texto('30 dias')


# =============================================================================
# H5 — REGISTRAR REFEIÇÃO CONSUMIDA
# =============================================================================

class H5RegistrarRefeicaoTest(BaseSeleniumTest):

    def setUp(self):
        super().setUp()
        self.nutri = self.criar_nutri()
        self.paciente = self.criar_paciente(self.nutri)

    def test_cenario1_refeicao_marcada_com_sucesso(self):
        """Cenário 1 (Positivo): refeição marcada e salva com data/hora"""
        plano = self.criar_plano(self.paciente, self.nutri)
        self.criar_refeicao(plano, nome='Café da manhã')

        self.injetar_sessao(paciente_id=self.paciente.id, tipo='paciente')  # ← troca
        self.get('/painel/') 
        self.driver.find_element(By.CSS_SELECTOR, '.btn-marcar').click()

        self.aguardar_texto('marcada como consumida')

    def test_cenario2_refeicao_ja_registrada_hoje(self):
        """Cenário 2 (Negativo): segunda marcação no mesmo dia exibe aviso"""
        plano = self.criar_plano(self.paciente, self.nutri)
        refeicao = self.criar_refeicao(plano, nome='Café da manhã')

        self.injetar_sessao(paciente_id=self.paciente.id, tipo='paciente')  # ← troca
        self.get('/painel/')
        self.driver.find_element(By.CSS_SELECTOR, '.btn-marcar').click()
        self.aguardar_texto('marcada como consumida')  # aguarda redirect completar

        # tenta marcar de novo via POST direto (botão some após primeiro consumo)
        self.post_via_js('/marcar-consumida/', {'refeicao_id': str(refeicao.id)})
        self.aguardar_texto('já registrou esta refeição hoje')

    def test_cenario3_sem_plano_ativo(self):
        """Cenário 3 (Negativo): paciente sem plano não vê botão; backend rejeita POST direto"""
        self.injetar_sessao(paciente_id=self.paciente.id, tipo='paciente')
        self.get('/painel/')

        self.aguardar_texto('Nenhum plano alimentar disponível')

        # garante que o backend também protege
        self.post_via_js('/marcar-consumida/', {'refeicao_id': '999'})
        self.aguardar_texto('plano alimentar ativo')


# =============================================================================
# H6 — DEFINIR METAS NUTRICIONAIS
# =============================================================================

class H6MetasNutricionaisTest(BaseSeleniumTest):

    def setUp(self):
        super().setUp()
        self.nutri = self.criar_nutri()
        self.paciente = self.criar_paciente(self.nutri)

    def _abrir_perfil(self):
        self.injetar_sessao(nutricionista_id=self.nutri.id, tipo='nutricionista')
        self.get(f'/paciente/{self.paciente.id}/')
        self.aguardar_texto('Salvar Metas')

    def _preencher_metas(self, calorias, proteina, carboidratos):
        for nome, val in [('calorias_diarias', calorias), ('proteina', proteina), ('carboidratos', carboidratos)]:
            el = self.driver.find_element(By.NAME, nome)
            el.clear()
            if val is not None:
                el.send_keys(str(val))

    def test_cenario1_meta_salva_com_sucesso(self):
        """Cenário 1 (Positivo): metas salvas e vinculadas ao paciente"""
        self._abrir_perfil()
        self._preencher_metas('2300', '150', '250')
        self.submeter()
        self.aguardar_texto('Metas nutricionais salvas')

    def _setar_e_disparar(self, seletor, valor):
        self.driver.execute_script(f"""
            var el = document.querySelector('{seletor}');
            el.value = '{valor}';
            el.dispatchEvent(new Event('input', {{bubbles:true}}));
            el.dispatchEvent(new Event('change', {{bubbles:true}}));
        """)

    def test_cenario2_caloria_negativa(self):
        """Cenário 2 (Negativo): caloria negativa exibe mensagem de erro"""
        self._abrir_perfil()
        for nome, val in [('calorias_diarias', '-500'), ('proteina', '150'), ('carboidratos', '250')]:
            el = self.driver.find_element(By.NAME, nome)
            el.clear()
            el.send_keys(val)
        self.submeter()
        self.aguardar_texto('número positivo')
        self.assertFalse(MetaNutricional.objects.filter(paciente=self.paciente).exists())

    def test_cenario3_campo_obrigatorio_vazio(self):
        """Cenário 3 (Negativo): campo proteína vazio exibe mensagem de obrigatório"""
        self._abrir_perfil()
        self.driver.execute_script(
            "document.querySelector('[name=proteina]').removeAttribute('required')"
        )
        for nome, val in [('calorias_diarias', '2300'), ('carboidratos', '250')]:
            el = self.driver.find_element(By.NAME, nome)
            el.clear()
            el.send_keys(val)
        self.driver.find_element(By.NAME, 'proteina').clear()
        self.driver.find_element(By.TAG_NAME, 'form').submit()
        self.aguardar_texto('campos de meta são obrigatórios')
        self.assertFalse(MetaNutricional.objects.filter(paciente=self.paciente).exists())


class AdesaoRelatorioTest(TestCase):

    def setUp(self):
        self.nutri = Nutricionista.objects.create(
            nome='Dra. Ana', crn='12345-PE', email='ana@nutri.com', senha='senha123'
        )
        self.paciente = Paciente.objects.create(
            nome='Maria Silva', email='maria@cliente.com', senha='senha123',
            peso=65, altura=1.65, idade=32,
            objetivo='Saúde', nutricionista=self.nutri
        )
        self.plano = PlanoAlimentar.objects.create(
            titulo='Plano Teste', paciente=self.paciente, nutricionista=self.nutri, ativo=True
        )

    def test_relatorio_adesao_exibe_percentual_e_historico(self):
        data_consumo = timezone.localdate() - timedelta(days=3)
        dias_da_semana = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
        dia_semana_esperado = dias_da_semana[data_consumo.weekday()]
        self.refeicao = Refeicao.objects.create(
            plano=self.plano,
            nome='Café da manhã',
            horario='08:00',
            descricao='Frutas e aveia',
            dia_semana=dia_semana_esperado
        )
        ConsumoRefeicao.objects.create(
            refeicao=self.refeicao,
            paciente=self.paciente,
            data_hora=timezone.now() - timedelta(days=3)
        )

        session = self.client.session
        session['nutricionista_id'] = self.nutri.id
        session.save()

        url = reverse('perfil_paciente', args=[self.paciente.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('relatorio_adesao', response.context)
        relatorio = response.context['relatorio_adesao']
        self.assertEqual(relatorio['total_realizado'], 1)
        self.assertGreaterEqual(relatorio['taxa_percentual'], 0)
        self.assertEqual(len(relatorio['dias']), 7)
        self.assertContains(response, 'Relatório de Adesão')

    def test_relatorio_adesao_sem_registro_plano_ativo_exibe_mensagem(self):
        paciente_sem_plano = Paciente.objects.create(
            nome='Pedro Lima', email='pedro@cliente.com', senha='senha123',
            peso=70, altura=1.75, idade=28,
            objetivo='Saúde', nutricionista=self.nutri
        )

        session = self.client.session
        session['nutricionista_id'] = self.nutri.id
        session.save()

        url = reverse('perfil_paciente', args=[paciente_sem_plano.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Relatório de Adesão')
        self.assertContains(response, 'Este paciente ainda não possui um plano alimentar ativo.')


class HistoricoRefeicoesTest(TestCase):

    def setUp(self):
        self.nutri = Nutricionista.objects.create(
            nome='Dra. Ana', crn='12345-PE', email='ana@nutri.com', senha='senha123'
        )
        self.paciente = Paciente.objects.create(
            nome='Luciana Costa', email='luciana@cliente.com', senha='senha123',
            peso=62, altura=1.64, idade=29,
            objetivo='Energia', nutricionista=self.nutri
        )
        self.plano = PlanoAlimentar.objects.create(
            titulo='Plano Energia', paciente=self.paciente, nutricionista=self.nutri, ativo=True
        )
        self.refeicao1 = Refeicao.objects.create(
            plano=self.plano,
            nome='Almoço',
            horario='12:30',
            descricao='Salada e proteína',
            dia_semana='seg'
        )
        self.refeicao2 = Refeicao.objects.create(
            plano=self.plano,
            nome='Jantar',
            horario='19:30',
            descricao='Peixe e legumes',
            dia_semana='seg'
        )

    def test_historico_exibe_registros_ordenados_por_data(self):
        registro_antigo = ConsumoRefeicao.objects.create(
            refeicao=self.refeicao1,
            paciente=self.paciente,
            data_hora=timezone.now() - timedelta(days=5, hours=3)
        )
        registro_recente = ConsumoRefeicao.objects.create(
            refeicao=self.refeicao2,
            paciente=self.paciente,
            data_hora=timezone.now() - timedelta(days=1, hours=2)
        )

        session = self.client.session
        session['paciente_id'] = self.paciente.id
        session.save()

        response = self.client.get(reverse('painel_paciente'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Histórico de Refeições')
        self.assertContains(response, self.refeicao2.nome)
        self.assertContains(response, self.refeicao1.nome)
        content = response.content.decode('utf-8')
        history_section = content.split('Histórico de Refeições', 1)[1]
        self.assertTrue(history_section.index(self.refeicao2.nome) < history_section.index(self.refeicao1.nome))
        self.assertContains(response, timezone.localtime(registro_recente.data_hora).strftime('%d/%m/%Y'))
        self.assertContains(response, timezone.localtime(registro_antigo.data_hora).strftime('%d/%m/%Y'))
        self.assertContains(response, 'Registrado às')

    def test_historico_sem_registros_ha_mais_de_30_dias_exibe_aviso(self):
        registro_antigo = ConsumoRefeicao.objects.create(
            refeicao=self.refeicao1,
            paciente=self.paciente,
        )
        ConsumoRefeicao.objects.filter(pk=registro_antigo.pk).update(
            data_hora=timezone.now() - timedelta(days=40)
        )

        session = self.client.session
        session['paciente_id'] = self.paciente.id
        session.save()

        response = self.client.get(reverse('painel_paciente'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Histórico de Refeições')
        self.assertContains(response, self.refeicao1.nome)
        self.assertContains(response, 'Você não registra refeições há 30 dias. Que tal registrar agora?')

 
# ---------------------------------------------------------------------------
# Helpers (mesmo padrão do teste_views.py)
# ---------------------------------------------------------------------------
def make_nutri(nome='Dra. Ana', crn='12345-PE', email='ana@nutri.com', senha='senha123'):
    return Nutricionista.objects.create(nome=nome, crn=crn, email=email, senha=senha)
 
 
def make_paciente(nutri=None, nome='Maria Silva', email='maria@cliente.com', senha='senha123'):
    return Paciente.objects.create(
        nome=nome, email=email, senha=senha,
        peso=65.0, altura=1.65, idade=32,
        objetivo='saude', nutricionista=nutri,
    )
 
 
def make_plano(paciente, nutricionista, ativo=True):
    return PlanoAlimentar.objects.create(
        titulo='Plano Teste', paciente=paciente,
        nutricionista=nutricionista, ativo=ativo,
    )
 
 
def make_refeicao(plano, nome='Café da manhã', dia='seg'):
    return Refeicao.objects.create(
        plano=plano, nome=nome,
        horario='08:00', descricao='Frutas e aveia',
        dia_semana=dia,
    )
 
 
# =============================================================================
# H7 — VISUALIZAR ADESÃO AO PLANO (complemento)
# =============================================================================
 
class H7AdesaoComplementoTest(TestCase):
    """
    Completa a cobertura de AdesaoRelatorioTest (pacientes/tests.py).
    Adiciona o Cenário 2: paciente com plano mas sem nenhum consumo registrado.
    """
 
    def setUp(self):
        self.nutri = make_nutri()
        self.paciente = make_paciente(self.nutri, nome='José Souza', email='jose@cliente.com')
        self.plano = make_plano(self.paciente, self.nutri)
        make_refeicao(self.plano)
 
        session = self.client.session
        session['nutricionista_id'] = self.nutri.id
        session.save()
 
        self.url = reverse('perfil_paciente', args=[self.paciente.id])
 
    def test_cenario2_paciente_sem_consumos_exibe_sem_dados_adesao(self):
        """
        Cenário 2 (Negativo): 'José Souza' tem plano ativo mas nunca registrou
        nenhuma refeição → sem_dados_adesao=True e mensagem na página.
        """
        response = self.client.get(self.url)
 
        self.assertEqual(response.status_code, 200)
        relatorio = response.context['relatorio_adesao']
 
        self.assertIsNotNone(relatorio['plano'])
        self.assertTrue(relatorio['sem_dados_adesao'])
        self.assertEqual(relatorio['total_realizado'], 0)
        self.assertContains(response, 'Não há dados de adesão disponíveis para este paciente ainda')
 
    def test_cenario3_plano_inativo_tratado_como_sem_plano(self):
        """
        Extra: plano com ativo=False não deve ser considerado no relatório,
        exibindo a mensagem de 'sem plano ativo'.
        """
        self.plano.ativo = False
        self.plano.save()
 
        response = self.client.get(self.url)
 
        relatorio = response.context['relatorio_adesao']
        self.assertIsNone(relatorio['plano'])
        self.assertContains(response, 'Este paciente ainda não possui um plano alimentar ativo')
 
 
# =============================================================================
# H8 — VISUALIZAR HISTÓRICO DE REFEIÇÕES (complemento)
# =============================================================================
 
class H8HistoricoComplementoTest(TestCase):
    """
    Completa a cobertura de HistoricoRefeicoesTest (pacientes/tests.py).
    Adiciona o Cenário 2: paciente sem nenhum registro de refeição.
    """
 
    def setUp(self):
        self.nutri = make_nutri()
        self.paciente = make_paciente(self.nutri, nome='Ana Lima', email='ana@cliente.com')
        self.plano = make_plano(self.paciente, self.nutri)
        self.refeicao = make_refeicao(self.plano)
 
        session = self.client.session
        session['paciente_id'] = self.paciente.id
        session.save()
 
        self.url = reverse('painel_paciente')
 
    def test_cenario2_historico_vazio_exibe_mensagem(self):
        """
        Cenário 2 (Negativo): paciente sem nenhum consumo registrado
        → mensagem 'Nenhuma refeição registrada ainda...' e sem aviso de 30 dias.
        """
        response = self.client.get(self.url)
 
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Nenhuma refeição registrada ainda. Comece registrando sua próxima refeição!',
        )
        self.assertFalse(response.context['historico_refeicoes'].exists())
        self.assertFalse(response.context['historico_aviso'])
 
    def test_cenario3_aviso_nao_exibido_com_registro_recente(self):
        """
        Extra: registro de ontem não deve disparar o aviso de 30 dias.
        """
        ConsumoRefeicao.objects.create(
            refeicao=self.refeicao,
            paciente=self.paciente,
            data_hora=timezone.now() - timedelta(days=1),
        )
 
        response = self.client.get(self.url)
 
        self.assertFalse(response.context['historico_aviso'])
        self.assertNotContains(response, 'Você não registra refeições há 30 dias')