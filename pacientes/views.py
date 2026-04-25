from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Paciente, Nutricionista, PlanoAlimentar, Refeicao, MetaNutricional
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
    if plano_ativo:
        if (timezone.now() - plano_ativo.atualizado_em).days > 30:
            messages.warning(request, 'Seu plano não é atualizado há 30 dias. Entre em contato com seu nutricionista')
        for refeicao in plano_ativo.refeicoes.all():
            dia = refeicao.get_dia_semana_display()
            if dia not in refeicoes_por_dia:
                refeicoes_por_dia[dia] = []
            refeicoes_por_dia[dia].append(refeicao)
    meta = getattr(paciente, 'meta_nutricional', None)
    return render(request, 'pacientes/painel_paciente.html', {
        'paciente': paciente,
        'plano_ativo': plano_ativo,
        'refeicoes_por_dia': refeicoes_por_dia,
        'meta': meta,
    })


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
    return render(request, 'pacientes/perfil_paciente.html', {
        'paciente': paciente,
        'meta_form': meta_form,
        'meta': meta,
    })
