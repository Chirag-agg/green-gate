/**
 * GreenGate — Main Application Entry Point
 * React Router v6 with protected routes.
 */

import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Calculator from './pages/Calculator';
import Report from './pages/Report';
import Verify from './pages/Verify';
import ProductNew from './pages/ProductNew';
import ProductDetail from './pages/ProductDetail';
import ProductOptimize from './pages/ProductOptimize';
import VoiceTest from './pages/VoiceTest';
import LoadingSpinner from './components/LoadingSpinner';
import { useAuth } from './context/AuthContext';

/**
 * Protected route wrapper — redirects to login if not authenticated.
 */
function ProtectedRoute() {
  const { authLoading, isAuthenticated } = useAuth();

  if (authLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24">
        <LoadingSpinner message="Checking your session..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

/**
 * Layout with Navbar for authenticated pages.
 */
function AppLayout() {
  return (
    <div className="min-h-screen pt-28">
      <Navbar />
      <Outlet />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#fff',
            color: '#1f2937',
            borderRadius: '12px',
            border: '1px solid #e5e7eb',
            boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
            fontSize: '14px',
          },
          success: {
            iconTheme: { primary: '#1A6B3A', secondary: '#fff' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#fff' },
          },
        }}
      />

      <Routes>
        {/* Public routes with navbar */}
        <Route element={<AppLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/verify" element={<Verify />} />
        </Route>

        {/* Auth routes (no navbar) */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected routes with navbar */}
        <Route element={<AppLayout />}>
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/calculator" element={<Calculator />} />
            <Route path="/products" element={<Navigate to="/products/new" replace />} />
            <Route path="/products/new" element={<ProductNew />} />
            <Route path="/product/:productId" element={<ProductDetail />} />
            <Route path="/product/:productId/optimize" element={<ProductOptimize />} />
            <Route path="/report/:reportId" element={<Report />} />
            <Route path="/voice-test" element={<VoiceTest />} />
          </Route>
        </Route>

        {/* 404 fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
