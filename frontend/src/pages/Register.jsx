/**
 * Register page for GreenGate MSME onboarding.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, Building2, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { registerUser } from '../utils/api';
import { useAuth } from '../context/AuthContext';

const SECTORS = [
  { value: 'steel_bfbof', label: 'Steel (BF-BOF)' },
  { value: 'steel_eaf', label: 'Steel (EAF)' },
  { value: 'cement', label: 'Cement' },
  { value: 'aluminium_primary', label: 'Aluminium (Primary)' },
  { value: 'aluminium_secondary', label: 'Aluminium (Secondary)' },
  { value: 'fertilizer_urea', label: 'Fertilizer (Urea)' },
  { value: 'hydrogen_grey', label: 'Hydrogen (Grey)' },
  { value: 'hydrogen_blue', label: 'Hydrogen (Blue)' },
  { value: 'hydrogen_green', label: 'Hydrogen (Green)' },
];

const STATES = [
  'Maharashtra', 'Gujarat', 'Punjab', 'Rajasthan', 'Odisha',
  'Tamil Nadu', 'Karnataka', 'West Bengal', 'Uttar Pradesh', 'Haryana',
];

export default function Register() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    company_name: '',
    gstin: '',
    iec_number: '',
    state: 'Maharashtra',
    sector: 'steel_bfbof',
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { refreshSession } = useAuth();

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await registerUser(formData);
      localStorage.setItem('greengate_token', res.data.access_token);
      localStorage.setItem('greengate_user', JSON.stringify({
        user_id: res.data.user_id,
        company_name: res.data.company_name,
      }));
      await refreshSession();
      toast.success('Account created! Welcome to GreenGate.');
      navigate('/calculator');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg animate-slide-up">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-surface-900">Create Your Account</h2>
          <p className="text-surface-600 mt-2">Start your CBAM compliance journey</p>
        </div>

        {/* Form */}
        <div className="card p-8 border-2">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-surface-700 mb-1">Company Name *</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
                  <input
                    className="input-field !pl-10"
                    placeholder="Sharma Steel Works"
                    value={formData.company_name}
                    onChange={(e) => updateField('company_name', e.target.value)}
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Email *</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
                  <input
                    type="email"
                    className="input-field !pl-10"
                    placeholder="you@company.com"
                    value={formData.email}
                    onChange={(e) => updateField('email', e.target.value)}
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Password *</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
                  <input
                    type="password"
                    className="input-field !pl-10"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => updateField('password', e.target.value)}
                    required
                    minLength={6}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Sector</label>
                <select className="input-field" value={formData.sector} onChange={(e) => updateField('sector', e.target.value)}>
                  {SECTORS.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">State</label>
                <select className="input-field" value={formData.state} onChange={(e) => updateField('state', e.target.value)}>
                  {STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">GSTIN</label>
                <input className="input-field" placeholder="22AAAAA0000A1Z5" value={formData.gstin} onChange={(e) => updateField('gstin', e.target.value)} />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">IEC Number</label>
                <input className="input-field" placeholder="0123456789" value={formData.iec_number} onChange={(e) => updateField('iec_number', e.target.value)} />
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full !py-3 mt-4">
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'Create Account & Start'
              )}
            </button>
          </form>
          <p className="text-sm text-surface-600 text-center mt-6">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-primary-700 hover:text-primary-800">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
