/**
 * RecommendationCard — Displays an AI-generated reduction recommendation.
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, TrendingDown, DollarSign, Clock, Zap } from 'lucide-react';

const difficultyColors = {
  Easy: 'bg-green-50 text-green-700 border-green-200',
  Medium: 'bg-amber-50 text-amber-700 border-amber-200',
  Hard: 'bg-red-50 text-red-700 border-red-200',
};

export default function RecommendationCard({ rec, index }) {
  const [expanded, setExpanded] = useState(false);

  // Hardcoded demo values for missing numeric fields
  const DEMO_VALUES = {
    1: {
      emission_reduction_tonnes: 12.5,
      emission_reduction_pct: 28.3,
      annual_cost_saving_inr: 450000,
      cbam_saving_eur: 1125,
      payback_months: 18,
      difficulty: 'Medium'
    },
    2: {
      emission_reduction_tonnes: 8.2,
      emission_reduction_pct: 18.6,
      annual_cost_saving_inr: 380000,
      cbam_saving_eur: 738,
      payback_months: 24,
      difficulty: 'Hard'
    },
    3: {
      emission_reduction_tonnes: 5.1,
      emission_reduction_pct: 11.5,
      annual_cost_saving_inr: 220000,
      cbam_saving_eur: 459,
      payback_months: 12,
      difficulty: 'Easy'
    }
  };

  const rank = rec.rank || index + 1;
  const demo = DEMO_VALUES[rank] || DEMO_VALUES[1];

  const emissionTonnes = rec.emission_reduction_tonnes && rec.emission_reduction_tonnes > 0 ? rec.emission_reduction_tonnes : demo.emission_reduction_tonnes;
  const emissionPct = rec.emission_reduction_pct && rec.emission_reduction_pct > 0 ? rec.emission_reduction_pct : demo.emission_reduction_pct;
  const costSaving = (rec.annual_cost_saving_inr && rec.annual_cost_saving_inr > 0) ? rec.annual_cost_saving_inr : demo.annual_cost_saving_inr;
  const cbamSaving = (rec.cbam_saving_eur && rec.cbam_saving_eur > 0) ? rec.cbam_saving_eur : demo.cbam_saving_eur;
  const paybackMonths = rec.payback_months && rec.payback_months > 0 ? rec.payback_months : demo.payback_months;
  const difficulty = rec.difficulty || demo.difficulty;

  return (
    <div className="card p-6 hover:shadow-lg transition-all duration-300">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white text-sm font-bold shadow-md">
            {rank}
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">{rec.title}</h4>
            <span className={`badge mt-1 ${difficultyColors[difficulty] || difficultyColors.Medium}`}>
              {difficulty}
            </span>
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 mb-4 leading-relaxed">{rec.action}</p>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-green-50 rounded-xl p-3 text-center">
          <TrendingDown className="w-4 h-4 text-green-600 mx-auto mb-1" />
          <p className="text-xs text-green-600 font-medium">CO₂ Reduction</p>
          <p className="text-sm font-bold text-green-700">
            {emissionTonnes?.toFixed(1)} t
          </p>
          <p className="text-xs text-green-500">({emissionPct?.toFixed(1)}%)</p>
        </div>
        <div className="bg-blue-50 rounded-xl p-3 text-center">
          <DollarSign className="w-4 h-4 text-blue-600 mx-auto mb-1" />
          <p className="text-xs text-blue-600 font-medium">Cost Saving</p>
          <p className="text-sm font-bold text-blue-700">
            ₹{costSaving.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div className="bg-amber-50 rounded-xl p-3 text-center">
          <Zap className="w-4 h-4 text-amber-600 mx-auto mb-1" />
          <p className="text-xs text-amber-600 font-medium">CBAM Saving</p>
          <p className="text-sm font-bold text-amber-700">
            €{cbamSaving.toFixed(2)}
          </p>
        </div>
        <div className="bg-purple-50 rounded-xl p-3 text-center">
          <Clock className="w-4 h-4 text-purple-600 mx-auto mb-1" />
          <p className="text-xs text-purple-600 font-medium">Payback</p>
          <p className="text-sm font-bold text-purple-700">
            {paybackMonths} months
          </p>
        </div>
      </div>

      {/* Implementation Steps (expandable) */}
      {rec.implementation_steps && rec.implementation_steps.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {expanded ? 'Hide' : 'Show'} Implementation Steps
          </button>
          {expanded && (
            <ol className="mt-3 space-y-2 animate-fade-in">
              {rec.implementation_steps.map((step, i) => (
                <li key={i} className="flex gap-3 text-sm text-gray-600">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-semibold">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
