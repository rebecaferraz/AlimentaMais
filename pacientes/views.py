from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.utils.timezone import localdate
from datetime import timedelta
from .models import Paciente, Nutricionista, PlanoAlimentar, Refeicao, MetaNutricional, ConsumoRefeicao
from .forms import MetaNutricionalForm


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
    nutricionistas = Nutricionista.objects.all()
    ctx = {'nutricionistas': nutricionistas}

    if request.method == 'POST':
        tipo            = request.POST.get('tipo', 'paciente')
        nome            = request.POST.get('nome', '').strip()
        email           = request.POST.get('email', '').strip()
        senha           = request.POST.get('senha', '')
        confirmar_senha = request.POST.get('confirmar_senha', '')

        if len(senha) < 8:
            messages.error(request, 'A senha precisa ter pelo menos 8 caracteres.')
            return render(request, 'pacientes/cadastro.html', ctx)

        if senha != confirmar_senha:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'pacientes/cadastro.html', ctx)

        # H1: Cadastro de Paciente
        if tipo == 'paciente':
            if Paciente.objects.filter(email=email).exists():
                messages.error(request, 'Este e-mail já está cadastrado. Faça login ou use outro e-mail.')
                return render(request, 'pacientes/cadastro.html', ctx)

            nutricionista_id = request.POST.get('nutricionista_id') or None
            Paciente.objects.create(
                nome             = nome,
                email            = email,
                senha            = senha,
                peso             = float(request.POST.get('peso', 0)),
                altura           = float(request.POST.get('altura', 0)),
                idade            = int(request.POST.get('idade', 0)),
                objetivo         = request.POST.get('objetivo', ''),
                restricoes       = request.POST.get('restricoes', ''),
                nutricionista_id = nutricionista_id,
            )
            messages.success(request, 'Conta criada com sucesso!')
            return redirect('login')

        # H2: Cadastro de Nutricionista
        else:
            crn = request.POST.get('crn', '').strip()
            if not crn:
                messages.error(request, 'O campo CRN é obrigatório.')
                return render(request, 'pacientes/cadastro.html', ctx)

            if Nutricionista.objects.filter(crn=crn).exists():
                messages.error(request, 'Esse CRN já está cadastrado no sistema.')
                return render(request, 'pacientes/cadastro.html', ctx)

            if Nutricionista.objects.filter(email=email).exists():
                messages.error(request, 'Este e-mail já está cadastrado. Faça login ou use outro e-mail.')
                return render(request, 'pacientes/cadastro.html', ctx)

            Nutricionista.objects.create(nome=nome, crn=crn, email=email, senha=senha)
            messages.success(request, 'Bem-vindo(a) ao Alimenta+!')
            return redirect('login')

    return render(request, 'pacientes/cadastro.html', ctx)


# PAINÉIS
def painel_paciente(request):
    paciente_id = request.session.get('paciente_id')
    if not paciente_id:
        return redirect('login')
    paciente = Paciente.objects.get(id=paciente_id)
    plano_ativo = paciente.planos.filter(ativo=True).first()
    refeicoes_por_dia = {}
    hoje = localdate()
    if plano_ativo:
        if (timezone.now() - plano_ativo.atualizado_em).days > 30:
            messages.warning(request, 'Seu plano não é atualizado há 30 dias. Entre em contato com seu nutricionista')
        for refeicao in plano_ativo.refeicoes.all():
            dia = refeicao.get_dia_semana_display()
            if dia not in refeicoes_por_dia:
                refeicoes_por_dia[dia] = []
            consumida_hoje = ConsumoRefeicao.objects.filter(
                refeicao=refeicao,
                paciente=paciente,
                data_hora__date=hoje
            ).exists()
            refeicoes_por_dia[dia].append({
                'refeicao': refeicao,
                'consumida_hoje': consumida_hoje
            })
    meta = getattr(paciente, 'meta_nutricional', None)
    return render(request, 'pacientes/painel_paciente.html', {
        'paciente': paciente,
        'plano_ativo': plano_ativo,
        'refeicoes_por_dia': refeicoes_por_dia,
        'meta': meta,
    })


def marcar_consumida(request):
    if request.method == 'POST':
        paciente_id = request.session.get('paciente_id')
        if not paciente_id:
            return redirect('login')
        paciente = Paciente.objects.get(id=paciente_id)
        
        # Check if patient has an active plan
        plano_ativo = paciente.planos.filter(ativo=True).first()
        if not plano_ativo:
            messages.error(request, 'Você não tem um plano alimentar ativo. Aguarde seu nutricionista criar seu plano')
            return redirect('painel_paciente')
        
        refeicao_id = request.POST.get('refeicao_id')
        if refeicao_id:
            try:
                refeicao = Refeicao.objects.get(id=refeicao_id)
                # Check if the refeicao belongs to the patient's active plan
                if refeicao.plano != plano_ativo:
                    messages.error(request, 'Refeição não pertence ao seu plano ativo.')
                    return redirect('painel_paciente')
                
                hoje = localdate()
                # Check if already consumed today
                if not ConsumoRefeicao.objects.filter(
                    refeicao=refeicao,
                    paciente=paciente,
                    data_hora__date=hoje
                ).exists():
                    ConsumoRefeicao.objects.create(refeicao=refeicao, paciente=paciente)
                    messages.success(request, f'Refeição "{refeicao.nome}" marcada como consumida!')
                else:
                    messages.warning(request, 'Você já registrou esta refeição hoje')
            except Refeicao.DoesNotExist:
                messages.error(request, 'Refeição não encontrada.')
        return redirect('painel_paciente')
    return redirect('painel_paciente')


def painel_nutricionista(request):
    nutri_id = request.session.get('nutricionista_id')
    if not nutri_id:
        return redirect('login')
    nutri     = Nutricionista.objects.get(id=nutri_id)
    pacientes = Paciente.objects.filter(nutricionista=nutri)
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
    pacientes     = Paciente.objects.filter(nutricionista=nutricionista)

    if request.method == 'POST':
        titulo      = request.POST.get('titulo', '').strip()
        paciente_id = request.POST.get('paciente_id')
        nomes       = request.POST.getlist('refeicao_nome')
        horarios    = request.POST.getlist('refeicao_horario')
        descricoes  = request.POST.getlist('refeicao_descricao')
        dias        = request.POST.getlist('refeicao_dia')

        if not paciente_id:
            messages.error(request, 'Paciente não encontrado.')
            return render(request, 'pacientes/criar_plano.html', {'pacientes': pacientes})

        refeicoes_validas = [n for n in nomes if n.strip()]
        if not refeicoes_validas:
            messages.error(request, 'O plano precisa ter ao menos uma refeição cadastrada.')
            return render(request, 'pacientes/criar_plano.html', {'pacientes': pacientes})

        paciente = Paciente.objects.get(id=paciente_id)
        PlanoAlimentar.objects.filter(paciente=paciente).update(ativo=False)
        plano = PlanoAlimentar.objects.create(
            titulo=titulo,
            paciente=paciente,
            nutricionista=nutricionista,
            ativo=True,
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


def calcular_relatorio_adesao(paciente, plano, dias=7):
    if not plano:
        return {
            'plano': None,
            'taxa_percentual': 0,
            'total_esperado': 0,
            'total_realizado': 0,
            'dias': [],
        }

    hoje = localdate()
    inicio = hoje - timedelta(days=dias - 1)
    dias_da_semana = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
    refeicoes_por_dia = {dia: 0 for dia in dias_da_semana}
    for refeicao in plano.refeicoes.all():
        refeicoes_por_dia[refeicao.dia_semana] += 1

    consumos = ConsumoRefeicao.objects.filter(
        paciente=paciente,
        refeicao__plano=plano,
        data_hora__date__gte=inicio,
        data_hora__date__lte=hoje,
    ).values('refeicao_id', 'data_hora__date')

    consumos_por_dia = {}
    for registro in consumos:
        data = registro['data_hora__date']
        consumos_por_dia.setdefault(data, set()).add(registro['refeicao_id'])

    historico = []
    total_esperado = 0
    total_realizado = 0

    for delta in range(dias):
        data = inicio + timedelta(days=delta)
        codigo_dia = dias_da_semana[data.weekday()]
        esperado = refeicoes_por_dia.get(codigo_dia, 0)
        realizado = len(consumos_por_dia.get(data, set()))
        percentual = round((realizado / esperado) * 100) if esperado else 0

        historico.append({
            'data': data,
            'label': data.strftime('%a, %d/%m'),
            'esperado': esperado,
            'realizado': realizado,
            'percentual': percentual,
        })

        total_esperado += esperado
        total_realizado += realizado

    taxa_percentual = round((total_realizado / total_esperado) * 100) if total_esperado else 0

    return {
        'plano': plano,
        'taxa_percentual': taxa_percentual,
        'total_esperado': total_esperado,
        'total_realizado': total_realizado,
        'dias': historico,
        'inicio': inicio,
        'fim': hoje,
    }


# ESQUECI MINHA SENHA
def esqueci_senha(request):
    email_validado = request.session.get('reset_email')
    tipo_validado  = request.session.get('reset_tipo')

    if email_validado and request.method == 'POST' and 'nova_senha' in request.POST:
        nova_senha = request.POST.get('nova_senha', '')

        if len(nova_senha) < 8:
            messages.error(request, 'A senha precisa ter pelo menos 8 caracteres.')
            return render(request, 'pacientes/esqueci_senha.html', {
                'passo': 2, 'email': email_validado,
            })

        if tipo_validado == 'paciente':
            Paciente.objects.filter(email=email_validado).update(senha=nova_senha)
        else:
            Nutricionista.objects.filter(email=email_validado).update(senha=nova_senha)

        del request.session['reset_email']
        del request.session['reset_tipo']

        messages.success(request, 'Senha redefinida com sucesso! Faça login com a nova senha.')
        return redirect('login')

    if request.method == 'POST' and 'email' in request.POST:
        email = request.POST.get('email', '').strip()

        paciente = Paciente.objects.filter(email=email).first()
        if paciente:
            request.session['reset_email'] = email
            request.session['reset_tipo'] = 'paciente'
            return render(request, 'pacientes/esqueci_senha.html', {
                'passo': 2, 'email': email,
            })

        nutri = Nutricionista.objects.filter(email=email).first()
        if nutri:
            request.session['reset_email'] = email
            request.session['reset_tipo'] = 'nutricionista'
            return render(request, 'pacientes/esqueci_senha.html', {
                'passo': 2, 'email': email,
            })

        messages.error(request, 'Nenhuma conta encontrada com esse e-mail.')

    request.session.pop('reset_email', None)
    request.session.pop('reset_tipo', None)

    return render(request, 'pacientes/esqueci_senha.html', {'passo': 1})


# PERFIL DO PACIENTE
def perfil_paciente(request, paciente_id):
    nutri_id = request.session.get('nutricionista_id')
    if not nutri_id:
        return redirect('login')

    try:
        paciente = Paciente.objects.get(id=paciente_id, nutricionista_id=nutri_id)
    except Paciente.DoesNotExist:
        messages.error(request, 'Paciente não encontrado.')
        return redirect('painel_nutricionista')

    plano_ativo = paciente.planos.filter(ativo=True).first()
    meta_form = MetaNutricionalForm()
    if request.method == 'POST':
        meta_form = MetaNutricionalForm(request.POST)
        if meta_form.is_valid():
            meta, created = MetaNutricional.objects.get_or_create(paciente=paciente, defaults=meta_form.cleaned_data)
            if not created:
                for field in meta_form.cleaned_data:
                    setattr(meta, field, meta_form.cleaned_data[field])
                meta.save()
            messages.success(request, 'Metas nutricionais salvas com sucesso!')
            return redirect('perfil_paciente', paciente_id=paciente_id)
        else:
            messages.error(request, 'Erro ao salvar metas. Verifique os dados.')

    meta = getattr(paciente, 'meta_nutricional', None)
    relatorio_adesao = calcular_relatorio_adesao(paciente, plano_ativo)
    return render(request, 'pacientes/perfil_paciente.html', {
        'paciente': paciente,
        'meta_form': meta_form,
        'meta': meta,
        'relatorio_adesao': relatorio_adesao,
    })
