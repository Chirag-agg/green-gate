/**
 * Dashboard page — Main MSME dashboard with summary stats and recent reports.
 */

import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FileText, ShieldCheck, Activity, DollarSign, Plus, ChevronRight, FolderOpen } from 'lucide-react';
import { getReports } from '../utils/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ResultCard from '../components/ResultCard';

export default function Dashboard() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const user = JSON.parse(localStorage.getItem('greengate_user') || '{}');

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const res = await getReports();
      setReports(res.data);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  };

  // Compute summary stats
  const totalReports = reports.length;
  const certifiedReports = reports.filter((r) => r.is_blockchain_certified).length;
  const avgCo2 = totalReports > 0
    ? (reports.reduce((sum, r) => sum + r.total_co2_tonnes, 0) / totalReports).toFixed(2)
    : '0.00';
  const totalCbam = reports.reduce((sum, r) => sum + r.cbam_liability_eur, 0).toFixed(2);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-32 flex justify-center">
        <LoadingSpinner message="Loading your dashboard..." />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 animate-fade-in mt-24">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-12 gap-6 bg-white p-8 rounded-[2rem] shadow-sm border border-surface-200">
        <div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-surface-900 tracking-tight">
            Welcome, <span className="text-primary-700">{user.company_name || 'User'}</span>
          </h1>
          <p className="text-lg text-surface-600 mt-2 font-medium">Your compliance overview at a glance.</p>
        </div>
        <Link to="/calculator" className="btn-primary flex items-center gap-3 text-lg !px-8 !py-4 shadow-lg shadow-primary-700/20">
          <Plus className="w-6 h-6" />
          Start New Report
        </Link>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
        <ResultCard
          icon={FileText}
          label="Total Reports"
          value={totalReports}
          color="blue"
        />
        <ResultCard
          icon={ShieldCheck}
          label="Certified secure"
          value={certifiedReports}
          subtext={totalReports > 0 ? `${Math.round((certifiedReports / totalReports) * 100)}% certified` : ''}
          color="green"
        />
        <ResultCard
          icon={Activity}
          label="Average Carbon"
          value={`${avgCo2} t`}
          color="primary"
        />
        <ResultCard
          icon={DollarSign}
          label="Total EU Tax Est."
          value={`€${parseFloat(totalCbam).toLocaleString()}`}
          color="accent"
        />
      </div>

      {/* Recent Reports Table */}
      <div className="card-glass overflow-hidden shadow-2xl shadow-surface-200/50">
        <div className="px-8 py-6 border-b border-surface-200/50 bg-surface-50/50 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-surface-900 flex items-center gap-3">
            <FolderOpen className="w-7 h-7 text-primary-700" />
            Your Recent Reports
          </h2>
          <span className="badge-info text-base !px-5 !py-2 bg-white">{totalReports} total</span>
        </div>

        {reports.length === 0 ? (
          <div className="text-center py-24 px-4 bg-white/50">
            <div className="w-24 h-24 bg-surface-100 rounded-[2rem] flex items-center justify-center mx-auto mb-6 shadow-inner">
              <FileText className="w-12 h-12 text-surface-400" />
            </div>
            <h3 className="text-2xl font-bold text-surface-800 mb-3 tracking-tight">Your folder is empty</h3>
            <p className="text-lg text-surface-600 mb-8 max-w-md mx-auto relative">
              Start your first AI-assisted carbon calculation to see your reports here.
            </p>
            <Link to="/calculator" className="btn-primary text-lg !px-10 !py-5 gap-3 shadow-lg shadow-primary-700/20">
              <Plus className="w-6 h-6" />
              Start My First Report
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto bg-white/50 backdrop-blur-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-50/80 border-b-2 border-surface-200">
                  <th className="px-8 py-5 text-sm font-bold text-surface-500 uppercase tracking-widest">Report ID</th>
                  <th className="px-8 py-5 text-sm font-bold text-surface-500 uppercase tracking-widest">Company</th>
                  <th className="px-8 py-5 text-sm font-bold text-surface-500 uppercase tracking-widest">Sector</th>
                  <th className="px-8 py-5 text-sm font-bold text-surface-500 uppercase tracking-widest">CO₂ (t)</th>
                  <th className="px-8 py-5 text-sm font-bold text-surface-500 uppercase tracking-widest">Tax (EUR)</th>
                  <th className="px-8 py-5 text-sm font-bold text-surface-500 uppercase tracking-widest">Status</th>
                  <th className="px-8 py-5"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {reports.map((r) => (
                  <tr
                    key={r.report_id}
                    className="hover:bg-primary-50 transition-colors duration-200 cursor-pointer group"
                    onClick={() => navigate(`/report/${r.report_id}`)}
                  >
                    <td className="px-8 py-6">
                      <span className="text-base font-bold font-mono text-primary-700 bg-primary-50 px-3 py-1.5 rounded-lg group-hover:bg-white transition-colors">{r.report_id}</span>
                    </td>
                    <td className="px-8 py-6 text-base font-medium text-surface-800">{r.company_name}</td>
                    <td className="px-8 py-6">
                      <span className="badge-info text-sm font-bold">{r.sector}</span>
                    </td>
                    <td className="px-8 py-6 text-base font-bold text-surface-900">{r.total_co2_tonnes?.toFixed(2)}</td>
                    <td className="px-8 py-6 text-base font-bold text-surface-900">€{r.cbam_liability_eur?.toLocaleString()}</td>
                    <td className="px-8 py-6">
                      {r.is_blockchain_certified ? (
                        <span className="badge-success text-sm font-bold px-4 py-2 border-2 border-green-200 bg-green-50 shadow-sm text-green-800 flex flex-row items-center gap-2 max-w-fit">
                          <ShieldCheck className="w-4 h-4" /> Certified
                        </span>
                      ) : (
                        <span className="badge-warning text-sm font-bold flex flex-row items-center gap-2 max-w-fit">
                          Draft
                        </span>
                      )}
                    </td>
                    <td className="px-8 py-6 text-right">
                      <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm group-hover:bg-primary-100 group-hover:text-primary-700 transition-colors ml-auto">
                        <ChevronRight className="w-6 h-6 text-surface-400 group-hover:text-primary-700" />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
