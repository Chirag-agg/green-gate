/**
 * Login page for GreenGate.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Leaf, Mail, Lock, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { loginUser, registerUser } from '../utils/api';

const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL || 'demo@greengate.app';
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || 'Demo@12345';
const DEMO_COMPANY = import.meta.env.VITE_DEMO_COMPANY || 'GreenGate Demo Industries';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const saveSession = (authData) => {
    localStorage.setItem('greengate_token', authData.access_token);
    localStorage.setItem('greengate_user', JSON.stringify({
      user_id: authData.user_id,
      company_name: authData.company_name,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await loginUser({ email, password });
      saveSession(res.data);
      toast.success('Welcome back!');
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const fillDemoValues = () => {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
  };

  const handleDemoAccess = async () => {
    setLoading(true);
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);

    try {
      const loginRes = await loginUser({
        email: DEMO_EMAIL,
        password: DEMO_PASSWORD,
      });
      saveSession(loginRes.data);
      toast.success('Signed in with demo account');
      navigate('/dashboard');
      return;
    } catch (loginErr) {
      // Continue to registration fallback when demo account is missing.
      if (loginErr.response?.status && loginErr.response.status !== 401) {
        toast.error(loginErr.response?.data?.detail || 'Demo login failed');
        setLoading(false);
        return;
      }
    }

    try {
      const registerRes = await registerUser({
        email: DEMO_EMAIL,
        password: DEMO_PASSWORD,
        company_name: DEMO_COMPANY,
      });
      saveSession(registerRes.data);
      toast.success('Demo account created and signed in');
      navigate('/dashboard');
    } catch (registerErr) {
      const msg = registerErr.response?.data?.detail || 'Demo access failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-green-50 px-4">
      <div className="w-full max-w-md animate-slide-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl flex items-center justify-center mx-auto shadow-lg shadow-primary-500/20 mb-4">
            <Leaf className="w-7 h-7 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Welcome Back</h2>
          <p className="text-gray-500 mt-1">Sign in to your GreenGate account</p>
        </div>

        {/* Form */}
        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="rounded-xl border border-primary-200 bg-primary-50/50 p-3 text-sm text-primary-800">
              <p className="font-semibold">Demo access</p>
              <p className="mt-1 break-all">{DEMO_EMAIL}</p>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={fillDemoValues}
                  disabled={loading}
                  className="btn-secondary !py-2 !px-3 text-xs"
                >
                  Use Demo Values
                </button>
                <button
                  type="button"
                  onClick={handleDemoAccess}
                  disabled={loading}
                  className="btn-primary !py-2 !px-3 text-xs"
                >
                  Skip Login
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  className="input-field !pl-10"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="password"
                  className="input-field !pl-10"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full !py-3">
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'Sign In'
              )}
            </button>
          </form>
          <p className="text-sm text-gray-500 text-center mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-primary-600 hover:text-primary-700">
              Register here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
