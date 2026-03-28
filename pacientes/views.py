from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Paciente, Nutricionista, PlanoAlimentar, Refeicao
 
 
# TELA DE LOGIN
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')
 
        paciente = Paciente.objects.filter(email=email, senha=senha).first()
        if paciente:
            request.session['paciente_id'] = paciente.id
            request.session['tipo'] = 'paciente'
            return redirect('painel_paciente')
 
        nutri = Nutricionista.objects.filter(email=email, senha=senha).first()
        if nutri:
            request.session['nutricionista_id'] = nutri.id
            request.session['tipo'] = 'nutricionista'
            return redirect('painel_nutricionista')
 
        messages.error(request, 'E-mail ou senha incorretos.')
 
    return render(request, 'pacientes/login.html')
 
 
# H1 + H2: CADASTRO 
def cadastro(request):
    if request.method == 'POST':
        tipo  = request.POST.get('tipo', 'paciente')
        nome  = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '')
 
        if len(senha) < 8:
            messages.error(request, 'A senha precisa ter pelo menos 8 caracteres.')
            return render(request, 'pacientes/cadastro.html')
 
        #  H1: Cadastro de Paciente 
        if tipo == 'paciente':
            if Paciente.objects.filter(email=email).exists():
                messages.error(request, 'Este e-mail já está cadastrado. Faça login ou use outro e-mail.')
                return render(request, 'pacientes/cadastro.html')
 
            Paciente.objects.create(
                nome       = nome,
                email      = email,
                senha      = senha,
                peso       = float(request.POST.get('peso', 0)),
                altura     = float(request.POST.get('altura', 0)),
                idade      = int(request.POST.get('idade', 0)),
                objetivo   = request.POST.get('objetivo', ''),
                restricoes = request.POST.get('restricoes', ''),
            )
            messages.success(request, 'Conta criada com sucesso!')
            return redirect('login')
 
        #  H2: Cadastro de Nutricionista 
        else:
            crn = request.POST.get('crn', '').strip()
            if not crn:
                messages.error(request, 'O campo CRN é obrigatório.')
                return render(request, 'pacientes/cadastro.html')
 
            if Nutricionista.objects.filter(crn=crn).exists():
                messages.error(request, 'Esse CRN já está cadastrado no sistema.')
                return render(request, 'pacientes/cadastro.html')
 
            if Nutricionista.objects.filter(email=email).exists():
                messages.error(request, 'Este e-mail já está cadastrado. Faça login ou use outro e-mail.')
                return render(request, 'pacientes/cadastro.html')
 
            Nutricionista.objects.create(nome=nome, crn=crn, email=email, senha=senha)
            messages.success(request, 'Bem-vindo(a) ao Alimenta+!')
            return redirect('login')
 
    return render(request, 'pacientes/cadastro.html')
 
 
# PAINÉIS 
def painel_paciente(request):
    paciente_id = request.session.get('paciente_id')
    if not paciente_id:
        return redirect('login')
    paciente = Paciente.objects.get(id=paciente_id)
    return render(request, 'pacientes/painel_paciente.html', {'paciente': paciente})
 
 
def painel_nutricionista(request):
    nutri_id = request.session.get('nutricionista_id')
    if not nutri_id:
        return redirect('login')
    nutri    = Nutricionista.objects.get(id=nutri_id)
    pacientes = Paciente.objects.all()
    return render(request, 'pacientes/painel_nutricionista.html', {
        'nutricionista': nutri,
        'pacientes': pacientes,
    })
 
 
# H3: CRIAR PLANO ALIMENTAR
def criar_plano(request):
    nutri_id = request.session.get('nutricionista_id')
    if not nutri_id:
        return redirect('login')
 
    nutricionista = Nutricionista.objects.get(id=nutri_id)
    pacientes     = Paciente.objects.all()
 
    if request.method == 'POST':
        titulo     = request.POST.get('titulo', '').strip()
        paciente_id = request.POST.get('paciente_id')
        nomes      = request.POST.getlist('refeicao_nome')
        horarios   = request.POST.getlist('refeicao_horario')
        descricoes = request.POST.getlist('refeicao_descricao')
        dias       = request.POST.getlist('refeicao_dia')
 
        if not paciente_id:
            messages.error(request, 'Paciente não encontrado.')
            return render(request, 'pacientes/criar_plano.html', {'pacientes': pacientes})
 
        refeicoes_validas = [n for n in nomes if n.strip()]
        if not refeicoes_validas:
            messages.error(request, 'O plano precisa ter ao menos uma refeição cadastrada.')
            return render(request, 'pacientes/criar_plano.html', {'pacientes': pacientes})
 
        paciente = Paciente.objects.get(id=paciente_id)
        plano    = PlanoAlimentar.objects.create(
            titulo=titulo,
            paciente=paciente,
            nutricionista=nutricionista,
        )
 
        for nome, horario, descricao, dia in zip(nomes, horarios, descricoes, dias):
            if nome.strip():
                Refeicao.objects.create(
                    plano=plano,
                    nome=nome,
                    horario=horario,
                    descricao=descricao,
                    dia_semana=dia,
                )
 
        messages.success(request, f'Plano "{titulo}" criado com sucesso para {paciente.nome}!')
        return redirect('painel_nutricionista')
 
    return render(request, 'pacientes/criar_plano.html', {'pacientes': pacientes})