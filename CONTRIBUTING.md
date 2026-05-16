# Como contribuir

## Configurando o ambiente

Clone o repositório e crie um ambiente virtual:

```bash
git clone https://github.com/rebecaferraz/AlimentaMais.git
cd AlimentaMais
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install selenium webdriver-manager
```

Suba o banco e o servidor:

```bash
python manage.py migrate
python manage.py runserver
```

## Rodando os testes

```bash
python manage.py test pacientes --verbosity=2
```

Precisa ter o Google Chrome instalado. O ChromeDriver é baixado automaticamente.

## Branches e commits

Não commite direto na `main`. Crie uma branch para cada coisa que for fazer:

```bash
git checkout -b feature/nome-da-funcionalidade
git checkout -b fix/descricao-do-bug
```

Mensagens de commit em português, direto ao ponto:

```
feat: adiciona histórico de refeições (H8)
fix: corrige percentual de adesão ao plano
test: cobre cenários de H7 e H8
ci: corrige ordem dos jobs no workflow
docs: atualiza README com entrega 04
```

## Pull Requests

- Abra PR para a `main` quando terminar
- Descreva o que foi feito e qual história cobre
- Só mergeia se o pipeline passar

## CI/CD

A cada push na `main`, o GitHub Actions roda os testes e faz o deploy na Azure automaticamente. Acompanhe em [github.com/rebecaferraz/AlimentaMais/actions](https://github.com/rebecaferraz/AlimentaMais/actions).

## Issues

Use as issues do GitHub para reportar bugs. Informe o que aconteceu, o que era esperado e como reproduzir.
