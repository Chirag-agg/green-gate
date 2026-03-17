/**
 * Report page — Full carbon compliance report viewer.
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Factory, Flame, Zap, BarChart3, AlertTriangle, Download,
  ShieldCheck, TrendingUp, TrendingDown, ArrowLeft, Cpu, Link as LinkIcon
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { getReport, certifyReport, downloadReport, uploadEvidence } from '../utils/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ResultCard from '../components/ResultCard';
import RecommendationCard from '../components/RecommendationCard';
import BlockchainBadge from '../components/BlockchainBadge';

const COLORS = ['#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6', '#6b7280'];

export default function Report() {
  const { reportId } = useParams();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [certifying, setCertifying] = useState(false);
  const [uploadingEvidence, setUploadingEvidence] = useState(false);
  const [evidence, setEvidence] = useState({
    electricity_bill: null,
    energy_audit_report: null,
    renewable_energy_certificate: null,
  });

  useEffect(() => {
    loadReport();
  }, [reportId]);

  const loadReport = async () => {
    try {
      const res = await getReport(reportId);
      setReport(res.data);
    } catch (err) {
      toast.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const handleCertify = async () => {
    setCertifying(true);
    try {
      const res = await certifyReport(reportId);
      toast.success('Report certified on blockchain!');
      // Reload to get updated data
      await loadReport();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Certification failed';
      toast.error(msg);
    } finally {
      setCertifying(false);
    }
  };

  const handleDownload = async () => {
    try {
      const res = await downloadReport(reportId);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportId}_cbam_report.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Report downloaded!');
    } catch (err) {
      toast.error('Download failed');
    }
  };

  const handleEvidenceUpload = async () => {
    const hasAny = evidence.electricity_bill || evidence.energy_audit_report || evidence.renewable_energy_certificate;
    if (!hasAny) {
      toast.error('Please attach at least one PDF file');
      return;
    }

    const formData = new FormData();
    if (evidence.electricity_bill) formData.append('electricity_bill', evidence.electricity_bill);
    if (evidence.energy_audit_report) formData.append('energy_audit_report', evidence.energy_audit_report);
    if (evidence.renewable_energy_certificate) formData.append('renewable_energy_certificate', evidence.renewable_energy_certificate);

    setUploadingEvidence(true);
    try {
      await uploadEvidence(reportId, formData);
      toast.success('Evidence uploaded successfully');
      setEvidence({ electricity_bill: null, energy_audit_report: null, renewable_energy_certificate: null });
      await loadReport();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Evidence upload failed';
      toast.error(msg);
    } finally {
      setUploadingEvidence(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20">
        <LoadingSpinner message="Loading report..." />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Report Not Found</h2>
        <Link to="/dashboard" className="btn-primary">Back to Dashboard</Link>
      </div>
    );
  }

  const safeParse = (value, fallback) => {
    try {
      return value ? JSON.parse(value) : fallback;
    } catch {
      return fallback;
    }
  };

  const fullOutput = safeParse(report.full_output_json, {});
  const recommendations = safeParse(report.recommendations_json, []);
  const breakdown = fullOutput.breakdown || {};

  // Pie chart data
  const pieData = [
    { name: 'Electricity', value: breakdown.electricity_co2_tonnes || 0 },
    { name: 'Coal', value: breakdown.coal_co2_tonnes || 0 },
    { name: 'Diesel', value: breakdown.diesel_co2_tonnes || 0 },
    { name: 'Natural Gas', value: breakdown.gas_co2_tonnes || 0 },
    { name: 'Other', value: breakdown.other_co2_tonnes || 0 },
  ].filter((d) => d.value > 0);

  const benchmarkPositive = report.vs_benchmark_pct >= 0;
  const evidenceFiles = safeParse(report.evidence_files, []);
  const hasEvidence = evidenceFiles.length > 0;
  const requiresEvidence = Boolean(report.requires_evidence) || (report.credibility_score ?? 1) < 0.5;
  const canCertify = report.is_blockchain_certified || (report.confidence_score ?? 0) >= 0.75;

  const scope3Breakdown = safeParse(report.scope3_breakdown, []);
  const validScope3Entries = scope3Breakdown.filter((item) => (item.emission_factor || 0) > 0).length;
  const supplyChainValidation = scope3Breakdown.length > 0
    ? validScope3Entries / scope3Breakdown.length
    : 0.8;

  const integrityRows = [
    { label: 'Benchmark Match', value: report.credibility_score ?? 0 },
    { label: 'Machinery Physics', value: report.machinery_score ?? 0 },
    { label: 'Regional Energy', value: report.regional_energy_score ?? 0 },
    { label: 'Temporal Consistency', value: report.temporal_score ?? 0 },
    { label: 'Supply Chain Validation', value: supplyChainValidation },
  ];

  const estimatedEmissions = report.estimated_emissions ?? 0;
  const reportedEmissions = report.total_co2_tonnes ?? 0;
  const twinDeviationRatio = report.deviation_ratio ?? 0;
  const twinDeviationPct = ((twinDeviationRatio - 1) * 100);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">
      {/* Back button & Header */}
      <div className="mb-8">
        <Link to="/dashboard" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
              {report.company_name}
            </h1>
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <span className="badge-info">{report.sector}</span>
              <span className="text-sm text-gray-500">{report.state} • Report {report.report_id}</span>
              <span className="text-sm text-gray-400">
                {new Date(report.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
              </span>
            </div>
          </div>
          <button onClick={handleDownload} className="btn-secondary gap-2">
            <Download className="w-4 h-4" /> Download CBAM Report
          </button>
        </div>
      </div>

      {/* CBAM Risk Card */}
      <div className={`rounded-2xl p-6 mb-8 border ${report.cbam_liability_eur > 1000
          ? 'bg-gradient-to-r from-red-50 to-amber-50 border-red-200'
          : 'bg-gradient-to-r from-amber-50 to-yellow-50 border-amber-200'
        }`}>
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-6 h-6 text-amber-600" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900 mb-1 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" /> CBAM Liability
            </h3>
            <p className="text-3xl font-extrabold text-amber-700">
              €{report.cbam_liability_eur?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              <span className="text-lg font-normal text-gray-500 ml-3">
                (₹{report.cbam_liability_inr?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })})
              </span>
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Based on {report.eu_embedded_co2_tonnes?.toFixed(2)} tonnes embedded CO₂
              in {report.eu_export_tonnes} tonnes of EU exports at €90/tonne
            </p>
          </div>
        </div>
      </div>

      {/* Emissions Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <ResultCard
          icon={Factory}
          label="Scope 1 (Direct)"
          value={`${report.scope1_co2_tonnes?.toFixed(2)} t`}
          subtext="Fuel combustion"
          color="red"
        />
        <ResultCard
          icon={Zap}
          label="Scope 2 (Electricity)"
          value={`${report.scope2_co2_tonnes?.toFixed(2)} t`}
          subtext="Grid electricity"
          color="blue"
        />
        <ResultCard
          icon={Flame}
          label="Total CO₂"
          value={`${report.total_co2_tonnes?.toFixed(2)} t`}
          subtext="Annual emissions"
          color="primary"
        />
        <ResultCard
          icon={BarChart3}
          label="Intensity"
          value={`${report.co2_per_tonne_product?.toFixed(3)} t/t`}
          subtext="CO₂ per tonne product"
          color="accent"
        />
      </div>

      {/* Chart + Benchmark */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Emissions Breakdown Chart */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Emissions Breakdown</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={110}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}
                >
                  {pieData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                      strokeWidth={0}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => [`${value.toFixed(2)} tonnes`, 'CO₂']}
                  contentStyle={{ borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">No breakdown data</div>
          )}
        </div>

        {/* Benchmark Comparison */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Benchmark</h3>
          <div className={`rounded-2xl p-8 text-center ${benchmarkPositive ? 'bg-red-50' : 'bg-green-50'
            }`}>
            <div className={`w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center ${benchmarkPositive ? 'bg-red-100' : 'bg-green-100'
              }`}>
              {benchmarkPositive ? (
                <TrendingUp className="w-8 h-8 text-red-500" />
              ) : (
                <TrendingDown className="w-8 h-8 text-green-500" />
              )}
            </div>
            <p className={`text-4xl font-extrabold mb-2 ${benchmarkPositive ? 'text-red-600' : 'text-green-600'
              }`}>
              {benchmarkPositive ? '+' : ''}{report.vs_benchmark_pct?.toFixed(1)}%
            </p>
            <p className="text-gray-600 font-medium">
              {benchmarkPositive ? 'Above' : 'Below'} sector benchmark
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Your intensity: {report.co2_per_tonne_product?.toFixed(3)} tCO₂/t product
            </p>
          </div>
        </div>
      </div>

      {/* Digital Factory Twin */}
      <div className="card p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Digital Factory Twin</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-xl bg-gray-50 p-4">
            <p className="text-xs text-gray-500 mb-1">Estimated Emissions</p>
            <p className="text-lg font-semibold text-gray-900">{estimatedEmissions.toFixed(2)} tCO₂</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-4">
            <p className="text-xs text-gray-500 mb-1">Reported Emissions</p>
            <p className="text-lg font-semibold text-gray-900">{reportedEmissions.toFixed(2)} tCO₂</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-4">
            <p className="text-xs text-gray-500 mb-1">Deviation %</p>
            <p className="text-lg font-semibold text-gray-900">{twinDeviationPct.toFixed(1)}%</p>
          </div>
        </div>
        {twinDeviationRatio < 0.5 && (
          <p className="mt-3 text-sm text-yellow-700 font-medium">
            Reported emissions are significantly below independent digital twin estimates.
          </p>
        )}
      </div>

      {/* AI Recommendations */}
      {recommendations.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2"><Cpu className="w-6 h-6 text-primary-600" /> AI Recommendations</h2>
          <p className="text-gray-500 mb-6">Ranked by ROI — implement the top recommendation first for maximum impact.</p>
          <div className="grid grid-cols-1 gap-4">
            {recommendations.map((rec, i) => (
              <RecommendationCard key={i} rec={rec} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Data Integrity Analysis */}
      <div className="card p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Data Integrity Analysis</h2>
        <div className="space-y-4">
          {integrityRows.map((row) => {
            const percent = Math.max(0, Math.min(100, (row.value || 0) * 100));
            return (
              <div key={row.label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700 font-medium">{row.label}</span>
                  <span className="text-gray-600">{(row.value || 0).toFixed(2)}</span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-primary-500" style={{ width: `${percent}%` }} />
                </div>
              </div>
            );
          })}
        </div>

        <p className="mt-5 text-sm font-semibold text-gray-800">
          Final Confidence Score: {(report.confidence_score ?? 0).toFixed(2)}
        </p>

        {report.verification_notes && (
          <div className="mt-4 rounded-xl border border-yellow-200 bg-yellow-50 p-4">
            <p className="text-sm font-semibold text-yellow-800 mb-1">Verification Explanation</p>
            <p className="text-sm text-yellow-700">{report.verification_notes}</p>
          </div>
        )}
      </div>

      {/* Evidence Upload */}
      {requiresEvidence && (
        <div className="card p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Upload Supporting Evidence</h2>
          <p className="text-sm text-gray-500 mb-4">
            This report was flagged for low credibility indicators. Upload PDF evidence to support your data.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Electricity Bill (PDF)</label>
              <input
                type="file"
                accept="application/pdf"
                className="input-field"
                onChange={(e) => setEvidence((prev) => ({ ...prev, electricity_bill: e.target.files?.[0] || null }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Energy Audit Report (PDF)</label>
              <input
                type="file"
                accept="application/pdf"
                className="input-field"
                onChange={(e) => setEvidence((prev) => ({ ...prev, energy_audit_report: e.target.files?.[0] || null }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Renewable Energy Certificate (PDF)</label>
              <input
                type="file"
                accept="application/pdf"
                className="input-field"
                onChange={(e) => setEvidence((prev) => ({ ...prev, renewable_energy_certificate: e.target.files?.[0] || null }))}
              />
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between gap-4">
            <p className="text-xs text-gray-500">
              Uploaded files: {hasEvidence ? evidenceFiles.length : 0}
            </p>
            <button
              onClick={handleEvidenceUpload}
              disabled={uploadingEvidence}
              className="btn-secondary"
            >
              {uploadingEvidence ? 'Uploading...' : 'Upload Evidence'}
            </button>
          </div>
        </div>
      )}

      {/* Blockchain Section */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2"><LinkIcon className="w-6 h-6 text-primary-600" /> Blockchain Certification</h2>
        {report.is_blockchain_certified ? (
          <BlockchainBadge
            certified={true}
            txHash={report.tx_hash}
            blockNumber={report.block_number}
            polygonscanUrl={report.polygonscan_url}
            reportHash={report.report_hash}
          />
        ) : (
          <div className="card p-8 text-center">
            <div className="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <ShieldCheck className="w-8 h-8 text-primary-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Ready to Certify?</h3>
            <p className="text-gray-500 max-w-md mx-auto mb-6">
              Store your report hash on the Polygon blockchain for immutable, trustless verification.
              Your EU importer can independently verify this certificate.
            </p>
            <button
              onClick={handleCertify}
              disabled={certifying || !canCertify}
              className="btn-primary gap-2"
            >
              {certifying ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  Certifying on Blockchain...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-5 h-5" />
                  Certify This Report
                </>
              )}
            </button>
            {!canCertify && (
              <p className="text-sm text-yellow-700 mt-3 font-medium">
                Confidence score too low for blockchain certification.
                Improve data quality or provide supporting evidence.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
