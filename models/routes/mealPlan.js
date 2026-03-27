const express = require('express');
const router = express.Router();
const MealPlan = require('../models/MealPlan');
const Patient = require('../models/Patient');

// Criar plano alimentar
router.post('/', async (req, res) => {
  const { title, meals, patientId } = req.body;

  try {
    const patient = await Patient.findById(patientId);
    if (!patient) return res.status(404).json({ message: 'Paciente não encontrado' });

    if (!meals || meals.length === 0) {
      return res.status(400).json({ message: 'O plano precisa ter ao menos uma refeição cadastrada' });
    }

    const plan = new MealPlan({ title, meals, patient: patient._id });
    await plan.save();

    patient.plans.push(plan._id);
    await patient.save();

    res.status(201).json({ message: 'Plano criado com sucesso', plan });
  } catch (err) {
    res.status(500).json({ message: 'Erro ao criar plano', error: err.message });
  }
});

module.exports = router;