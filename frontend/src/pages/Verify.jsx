/**
 * Verify page — Public certificate verification for EU importers.
 * No authentication required.
 */

import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ShieldCheck, ShieldX, Search, ExternalLink, Loader2, Globe } from 'lucide-react';
import { verifyReportHash } from '../utils/api';
import toast from 'react-hot-toast';

export default function Verify() {
  const [searchParams] = useSearchParams();
  const [hash, setHash] = useState(searchParams.get('hash') || '');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [searched, setSearched] = useState(false);

  // Auto-verify if hash provided in URL
  useEffect(() => {
    if (searchParams.get('hash')) {
      handleVerify();
    }
  }, []);

  const handleVerify = async () => {
    if (!hash.trim()) {
      toast.error('Please enter a report hash');
      return;
    }

    setLoading(true);
    setSearched(true);
    setResult(null);

    try {
      const res = await verifyReportHash(hash.trim());
      setResult(res.data);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Verification failed';
      toast.error(msg);
      setResult({ is_valid: false, message: msg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-surface-50 to-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 animate-fade-in">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-full px-4 py-1.5 mb-6">
            <Globe className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-semibold text-blue-700">Public Verification — No Login Required</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            Verify a GreenGate <span className="text-primary-700">Carbon Certificate</span>
          </h1>
          <p className="text-lg text-gray-500 max-w-xl mx-auto">
            Enter a report hash to verify its authenticity on the Polygon blockchain. 
            This verification is trustless — data is permanently stored on-chain.
          </p>
        </div>

        {/* Search Box */}
        <div className="card p-8 mb-8">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Report Hash (bytes32 hex string)
          </label>
          <div className="flex gap-3">
            <input
              className="input-field flex-1 font-mono text-sm"
              placeholder="0x1234abcd...ef56"
              value={hash}
              onChange={(e) => setHash(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
            />
            <button
              onClick={handleVerify}
              disabled={loading}
              className="btn-primary gap-2 flex-shrink-0"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Verify
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            The report hash is a SHA-256 hash of the CBAM report data. Ask your Indian exporter for this hash.
          </p>
        </div>

        {/* Result */}
        {searched && !loading && result && (
          <div className="animate-slide-up">
            {result.is_valid ? (
              <div className="card p-8 bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
                <div className="text-center mb-6">
                  <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4 shadow-xl shadow-green-500/30">
                    <ShieldCheck className="w-10 h-10 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold text-green-800">Valid Certificate</h2>
                </div>
                <div className="space-y-4 max-w-md mx-auto">
                  <div className="bg-white rounded-xl p-4 border border-green-100">
                    <p className="text-xs text-gray-500 font-medium mb-1">Report ID</p>
                    <p className="text-lg font-bold text-gray-900 font-mono">{result.report_id}</p>
                  </div>
                  <div className="bg-white rounded-xl p-4 border border-green-100">
                    <p className="text-xs text-gray-500 font-medium mb-1">Certification Date</p>
                    <p className="text-lg font-bold text-gray-900">{result.timestamp_readable}</p>
                  </div>
                  <div className="bg-white rounded-xl p-4 border border-green-100">
                    <p className="text-xs text-gray-500 font-medium mb-1">Report Hash</p>
                    <p className="text-xs font-mono text-gray-700 break-all">{hash}</p>
                  </div>
                  <div className="pt-4">
                    <a
                      href={`https://amoy.polygonscan.com`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary w-full justify-center gap-2"
                    >
                      <ExternalLink className="w-4 h-4" /> View on Polygonscan
                    </a>
                  </div>
                </div>
                <p className="text-center text-sm text-green-700 mt-6">
                  {result.message}
                </p>
              </div>
            ) : (
              <div className="card p-8 bg-gradient-to-br from-red-50 to-pink-50 border-red-200">
                <div className="text-center">
                  <div className="w-20 h-20 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4 shadow-xl shadow-red-500/30">
                    <ShieldX className="w-10 h-10 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold text-red-800 mb-3">Not Verified</h2>
                  <p className="text-red-600">{result.message}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Trust note */}
        <div className="mt-12 text-center">
          <p className="text-sm text-gray-400">
            This verification is <span className="font-semibold">trustless</span> — data is permanently stored on the Polygon blockchain. 
            No one, including GreenGate, can alter or delete certified reports.
          </p>
        </div>
      </div>
    </div>
  );
}
