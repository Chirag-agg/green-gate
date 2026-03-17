/**
 * Calculator page — Multi-step carbon footprint calculator.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Settings, Network } from 'lucide-react';
import EmissionForm from '../components/EmissionForm';
import LoadingSpinner from '../components/LoadingSpinner';
import { calculateEmissions } from '../utils/api';

export default function Calculator() {
  const [loading, setLoading] = useState(false);
  const [showCalcAnimation, setShowCalcAnimation] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (data) => {
    setLoading(true);
    setShowCalcAnimation(true);

    try {
      const res = await calculateEmissions(data);
      toast.success(`Report ${res.data.report_id} created successfully!`);
      navigate(`/report/${res.data.report_id}`);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Calculation failed. Please try again.';
      toast.error(msg);
      setShowCalcAnimation(false);
    } finally {
      setLoading(false);
    }
  };

  if (showCalcAnimation && loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-32 mt-20">
        <div className="text-center card-glass p-16 max-w-2xl mx-auto rounded-[3rem]">
          <div className="relative inline-block mb-10">
            <div className="w-28 h-28 rounded-full bg-primary-100 flex items-center justify-center mx-auto animate-float">
              <div className="w-20 h-20 rounded-full bg-primary-700 flex items-center justify-center shadow-2xl shadow-primary-700/40 animate-spin" style={{ animationDuration: '4s' }}>
                <Settings className="text-white w-10 h-10" />
              </div>
            </div>
          </div>
          <h2 className="text-3xl font-extrabold text-surface-900 mb-4 tracking-tight">Calculating Carbon Footprint...</h2>
          <p className="text-xl text-surface-600 max-w-md mx-auto leading-relaxed">
            Our secure engine is processing your data, applying certified emission factors,
            and generating personalized reduction recommendations.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <div className="w-3 h-3 rounded-full bg-primary-700 animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-3 h-3 rounded-full bg-primary-700 animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-3 h-3 rounded-full bg-primary-700 animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 animate-fade-in mt-24">
      <div className="text-center mb-12">
        <h1 className="text-4xl sm:text-5xl font-extrabold text-surface-900 mb-4 tracking-tight">Carbon Calculator</h1>
        <p className="text-xl text-surface-600 max-w-2xl mx-auto font-medium">
          Enter your production and energy data to calculate your CBAM-compliant carbon
          emissions report.
        </p>
      </div>

      <div className="card-glass p-8 mb-10 border-2 border-primary-100 bg-white/60">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <p className="text-xl font-bold text-surface-900 mb-1">Need supply chain tracking?</p>
            <p className="text-base text-surface-600 font-medium">Map your suppliers and calculate product-level emissions before generating a final report.</p>
          </div>
          <Link to="/products/new" className="btn-secondary whitespace-nowrap text-center text-lg !px-8 !py-4 gap-3 shadow-sm">
            <Network className="w-6 h-6" />
            Supply Chain Tools
          </Link>
        </div>
      </div>

      <EmissionForm onSubmit={handleSubmit} loading={loading} />
    </div>
  );
}
