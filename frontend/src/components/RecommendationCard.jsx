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

  return (
    <div className="card p-6 hover:shadow-lg transition-all duration-300">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white text-sm font-bold shadow-md">
            {rec.rank || index + 1}
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">{rec.title}</h4>
            <span className={`badge mt-1 ${difficultyColors[rec.difficulty] || difficultyColors.Medium}`}>
              {rec.difficulty}
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
            {rec.emission_reduction_tonnes?.toFixed(1)} t
          </p>
          <p className="text-xs text-green-500">({rec.emission_reduction_pct?.toFixed(1)}%)</p>
        </div>
        <div className="bg-blue-50 rounded-xl p-3 text-center">
          <DollarSign className="w-4 h-4 text-blue-600 mx-auto mb-1" />
          <p className="text-xs text-blue-600 font-medium">Cost Saving</p>
          <p className="text-sm font-bold text-blue-700">
            ₹{(rec.annual_cost_saving_inr || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div className="bg-amber-50 rounded-xl p-3 text-center">
          <Zap className="w-4 h-4 text-amber-600 mx-auto mb-1" />
          <p className="text-xs text-amber-600 font-medium">CBAM Saving</p>
          <p className="text-sm font-bold text-amber-700">
            €{(rec.cbam_saving_eur || 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-purple-50 rounded-xl p-3 text-center">
          <Clock className="w-4 h-4 text-purple-600 mx-auto mb-1" />
          <p className="text-xs text-purple-600 font-medium">Payback</p>
          <p className="text-sm font-bold text-purple-700">
            {rec.payback_months} months
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
