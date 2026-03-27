from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Nutritionist, Patient, MealPlan

# H2: Cadastro de nutricionista
@csrf_exempt
def register_nutritionist(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        crn = data.get('crn')
        email = data.get('email')
        password = data.get('password')

        if not all([name, crn, email, password]):
            return JsonResponse({'message': 'Todos os campos são obrigatórios'}, status=400)

        if Nutritionist.objects.filter(crn=crn).exists():
            return JsonResponse({'message': 'Esse CRN já está cadastrado no sistema'}, status=400)

        nutritionist = Nutritionist.objects.create(name=name, crn=crn, email=email, password=password)
        return JsonResponse({'message': 'Bem-vindo(a) ao Alimenta+!', 'nutritionist': {'id': nutritionist.id, 'name': nutritionist.name}})

# H3: Criar plano alimentar
@csrf_exempt
def create_mealplan(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        title = data.get('title')
        patient_id = data.get('patient_id')
        meals = data.get('meals')

        if not title or not meals or not patient_id:
            return JsonResponse({'message': 'O plano precisa ter ao menos uma refeição e paciente'}, status=400)

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({'message': 'Paciente não encontrado'}, status=404)

        plan = MealPlan.objects.create(title=title, patient=patient, meals=meals)
        return JsonResponse({'message': 'Plano criado com sucesso', 'plan': {'id': plan.id, 'title': plan.title}})