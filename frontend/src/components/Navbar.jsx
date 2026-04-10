/**
 * Navbar component — top navigation bar for GreenGate.
 */

import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Menu, X, LogOut, LayoutDashboard, Calculator, ShieldCheck, Network, Volume2, Mic } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const { isAuthenticated, user, logout } = useAuth();
  const isLoggedIn = isAuthenticated;

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isActive = (path) => {
    if (path === '/products/new') {
      return location.pathname === '/products/new' || location.pathname.startsWith('/product/');
    }
    return location.pathname === path;
  };

  return (
    <div className="fixed top-0 inset-x-0 z-50 flex justify-center px-4 pt-4 pb-2 pointer-events-none">
      <nav className="w-full max-w-7xl bg-white border border-surface-200 shadow-md rounded-2xl pointer-events-auto transition-all duration-200">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-3 group">
              <span className="text-2xl font-semibold text-surface-900 tracking-tight">GreenGate</span>
            </Link>

            {/* Desktop Nav */}
            <div className="hidden lg:flex items-center gap-2">
              <button
                className="p-3 mr-4 rounded-xl text-surface-500 hover:text-primary-700 hover:bg-primary-50 transition-colors"
                title="Read Aloud Help"
                aria-label="Audio Help"
              >
                <Volume2 className="w-6 h-6" />
              </button>

              {isLoggedIn ? (
                <>
                  <Link
                    to="/dashboard"
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl text-base font-semibold transition-all duration-300 ${isActive('/dashboard')
                        ? 'bg-primary-100 text-primary-900 shadow-sm'
                      : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                      }`}
                  >
                    <LayoutDashboard className="w-5 h-5" />
                    Dashboard
                  </Link>
                  <Link
                    to="/calculator"
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl text-base font-semibold transition-all duration-300 ${isActive('/calculator')
                        ? 'bg-primary-100 text-primary-900 shadow-sm'
                      : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                      }`}
                  >
                    <Calculator className="w-5 h-5" />
                    Calculator
                  </Link>
                  <Link
                    to="/products/new"
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl text-base font-semibold transition-all duration-300 ${isActive('/products/new')
                        ? 'bg-primary-100 text-primary-900 shadow-sm'
                      : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                      }`}
                  >
                    <Network className="w-5 h-5" />
                    Products
                  </Link>
                  <Link
                    to="/verify"
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl text-base font-semibold transition-all duration-300 ${isActive('/verify')
                        ? 'bg-primary-100 text-primary-900 shadow-sm'
                      : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                      }`}
                  >
                    <ShieldCheck className="w-5 h-5" />
                    Verify
                  </Link>
                  <Link
                    to="/voice-test"
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl text-base font-semibold transition-all duration-300 ${isActive('/voice-test')
                        ? 'bg-primary-100 text-primary-900 shadow-sm'
                      : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900'
                      }`}
                  >
                    <Mic className="w-5 h-5" />
                    Voice Test
                  </Link>
                  <div className="w-px h-8 bg-surface-200 mx-2" />
                  <span className="text-base font-medium text-surface-600 mr-2 bg-surface-50 px-4 py-2 rounded-xl">
                    {user?.company_name || user?.email || 'User'}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 px-5 py-3 rounded-xl text-base font-semibold text-red-600 hover:bg-red-50 transition-all duration-300"
                  >
                    <LogOut className="w-5 h-5" />
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/verify"
                    className="flex items-center gap-2 px-6 py-3 rounded-xl text-base font-semibold text-surface-600 hover:bg-surface-100 hover:text-surface-900 transition-all duration-300"
                  >
                    <ShieldCheck className="w-5 h-5" />
                    Verify
                  </Link>
                  <Link
                    to="/login"
                    className="px-6 py-3 rounded-xl text-base font-semibold text-surface-600 hover:bg-surface-100 hover:text-surface-900 transition-all duration-300"
                  >
                    Login
                  </Link>
                  <Link to="/register" className="btn-primary ml-2">
                    Get Started
                  </Link>
                </>
              )}
            </div>

            {/* Mobile Hamburger */}
            <div className="flex items-center gap-4 lg:hidden">
              <button
                className="p-2 rounded-xl text-surface-500 hover:text-primary-700 hover:bg-primary-50 transition-colors"
                aria-label="Audio Help"
              >
                <Volume2 className="w-6 h-6" />
              </button>
              <button
                className="p-3 rounded-xl bg-surface-100 hover:bg-surface-200 text-surface-700 transition-colors"
                onClick={() => setMobileOpen(!mobileOpen)}
              >
                {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileOpen && (
          <div className="lg:hidden border-t border-surface-200 bg-surface-50 rounded-b-2xl p-4 animate-slide-up">
            <div className="space-y-2">
              {isLoggedIn ? (
                <>
                  <Link to="/dashboard" className="flex items-center gap-3 px-5 py-4 rounded-2xl text-lg font-semibold text-surface-800 hover:bg-white" onClick={() => setMobileOpen(false)}>
                    <LayoutDashboard className="w-6 h-6 text-primary-600" /> Dashboard
                  </Link>
                  <Link to="/calculator" className="flex items-center gap-3 px-5 py-4 rounded-2xl text-lg font-semibold text-surface-800 hover:bg-white" onClick={() => setMobileOpen(false)}>
                    <Calculator className="w-6 h-6 text-primary-600" /> Calculator
                  </Link>
                  <Link to="/products/new" className="flex items-center gap-3 px-5 py-4 rounded-2xl text-lg font-semibold text-surface-800 hover:bg-white" onClick={() => setMobileOpen(false)}>
                    <Network className="w-6 h-6 text-primary-600" /> Products
                  </Link>
                  <Link to="/verify" className="flex items-center gap-3 px-5 py-4 rounded-2xl text-lg font-semibold text-surface-800 hover:bg-white" onClick={() => setMobileOpen(false)}>
                    <ShieldCheck className="w-6 h-6 text-primary-600" /> Verify
                  </Link>
                  <Link to="/voice-test" className="flex items-center gap-3 px-5 py-4 rounded-2xl text-lg font-semibold text-surface-800 hover:bg-white" onClick={() => setMobileOpen(false)}>
                    <Mic className="w-6 h-6 text-primary-600" /> Voice Test
                  </Link>
                  <button onClick={() => { handleLogout(); setMobileOpen(false); }} className="flex items-center gap-3 w-full text-left px-5 py-4 rounded-2xl text-lg font-semibold text-red-600 hover:bg-red-50">
                    <LogOut className="w-6 h-6" /> Logout
                  </button>
                </>
              ) : (
                <>
                  <Link to="/verify" className="flex items-center gap-3 px-5 py-4 rounded-2xl text-lg font-semibold text-surface-800 hover:bg-white" onClick={() => setMobileOpen(false)}>
                    <ShieldCheck className="w-6 h-6 text-primary-600" /> Verify Certificate
                  </Link>
                  <Link to="/login" className="flex items-center gap-3 px-5 py-4 rounded-2xl text-lg font-semibold text-surface-800 hover:bg-white" onClick={() => setMobileOpen(false)}>
                    Login
                  </Link>
                  <Link to="/register" className="block w-full text-center px-5 py-4 rounded-2xl text-lg font-semibold text-white bg-primary-700 mt-4 shadow-lg shadow-primary-700/20" onClick={() => setMobileOpen(false)}>
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </nav>
    </div>
  );
}
