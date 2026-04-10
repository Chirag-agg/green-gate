/**
 * API client for GreenGate backend.
 * Axios instance with JWT auth interceptor.
 */

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token to every request if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('greengate_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses (token expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('greengate_token');
      localStorage.removeItem('greengate_user');
      if (window.location.pathname !== '/login' && window.location.pathname !== '/') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ──── Auth ────

export const registerUser = (data) => api.post('/auth/register', data);
export const loginUser = (data) => api.post('/auth/login', data);
export const getMe = () => api.get('/auth/me');

// ──── Calculator ────

export const calculateEmissions = (data) => api.post('/api/calculate', data);
export const runCompanyIntelligence = (data) => api.post('/api/company-intelligence', data);
export const discoverProductSupplyChain = (data) => api.post('/api/products/discover', data);
export const confirmProductSupplyChain = (productId, data) => api.post(`/api/products/${productId}/confirm-supply-chain`, data);
export const getProductDetail = (productId) => api.get(`/api/products/${productId}`);
export const analyzeProductFactories = (productId) => api.post(`/api/products/${productId}/analyze-factories`);
export const aggregateProductCarbon = (productId, productQuantity = 1000) =>
  api.post(`/api/products/${productId}/aggregate-carbon`, null, {
    params: { product_quantity: productQuantity },
  });
export const optimizeProductSupplyChain = (productId, data) =>
  api.post(`/api/products/${productId}/optimize`, data);
export const attestProductNode = (productId, nodeId, data) =>
  api.post(`/api/products/${productId}/nodes/${nodeId}/attest`, data);

// ──── Reports ────

export const getReports = () => api.get('/api/reports');
export const getReport = (reportId) => api.get(`/api/reports/${reportId}`);
export const certifyReport = (reportId) => api.post(`/api/reports/${reportId}/certify`);
export const downloadReport = (reportId, format = 'xml') =>
  api.get(`/api/reports/${reportId}/download`, {
    params: { format },
    responseType: 'blob',
  });
export const uploadEvidence = (reportId, formData) =>
  api.post(`/api/reports/${reportId}/upload-evidence`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

// ──── Verification (public) ────

export const verifyReportHash = (hash) => api.get(`/api/verify/${hash}`);

// ──── Voice AI ────

export const processVoiceAudio = (audioFile, sessionId = null) => {
  const formData = new FormData();
  formData.append('audio', audioFile);
  if (sessionId) {
    formData.append('session_id', sessionId);
  }
  return api.post('/chat-voice', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const synthesizeVoiceResponse = (text, language = null) =>
  api.post('/tts', { text, language }, { responseType: 'blob' });

// ──── Health ────

export const healthCheck = () => api.get('/api/health');

export default api;
