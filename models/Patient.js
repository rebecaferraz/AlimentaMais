const mongoose = require('mongoose');

const patientSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  plans: [{ type: mongoose.Schema.Types.ObjectId, ref: 'MealPlan' }]
});

module.exports = mongoose.model('Patient', patientSchema);

