const mongoose = require('mongoose');

const mealPlanSchema = new mongoose.Schema({
  title: { type: String, required: true },
  meals: [{ day: String, meal: String }],
  patient: { type: mongoose.Schema.Types.ObjectId, ref: 'Patient', required: true }
});

module.exports = mongoose.model('MealPlan', mealPlanSchema);