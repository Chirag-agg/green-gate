/**
 * Product-level factory intelligence + carbon aggregation dashboard.
 * Phase 2: Factory analysis. Phase 3: Carbon aggregation, EU CBAM compliance.
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import { ShieldCheck, AlertTriangle, X, MessageSquareShare } from 'lucide-react';
import {
    Bar,
    BarChart,
    Cell,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import {
    aggregateProductCarbon,
    analyzeProductFactories,
    getProductDetail,
    attestProductNode,
} from '../utils/api';

const ANALYSIS_STEPS = [
    'Validating factories',
    'Scraping manufacturing data',
    'Detecting machinery',
    'Running emission verification',
    'Aggregating supply chain emissions',
];

function roleLabel(role) {
    return String(role || '').replaceAll('_', ' ');
}

function confidenceColor(confidence) {
    const v = Number(confidence || 0);
    if (v > 0.8) return { bg: '#ecfdf5', border: '#10b981', text: '#065f46' };
    if (v >= 0.6) return { bg: '#fffbeb', border: '#f59e0b', text: '#92400e' };
    return { bg: '#fef2f2', border: '#ef4444', text: '#991b1b' };
}

function emissionNodeColor(emissions, maxEmissions) {
    if (maxEmissions <= 0) return confidenceColor(0.9);
    const ratio = emissions / maxEmissions;
    if (ratio >= 0.6) return { bg: '#fef2f2', border: '#ef4444', text: '#991b1b' };
    if (ratio >= 0.25) return { bg: '#fffbeb', border: '#f59e0b', text: '#92400e' };
    return { bg: '#ecfdf5', border: '#10b981', text: '#065f46' };
}

function cbamRiskStyle(risk) {
    switch (String(risk).toLowerCase()) {
        case 'low': return { bg: '#ecfdf5', border: '#10b981', text: '#065f46', label: 'Low Risk' };
        case 'moderate': return { bg: '#fffbeb', border: '#f59e0b', text: '#92400e', label: 'Moderate Risk' };
        case 'high': return { bg: '#fff7ed', border: '#f97316', text: '#9a3412', label: 'High Risk' };
        case 'critical': return { bg: '#fef2f2', border: '#ef4444', text: '#991b1b', label: 'Critical Risk' };
        default: return { bg: '#f8fafc', border: '#94a3b8', text: '#475569', label: 'Unknown' };
    }
}

function barColor(pct) {
    if (pct >= 40) return '#ef4444';
    if (pct >= 20) return '#f59e0b';
    return '#10b981';
}

export default function ProductDetail() {
    const { productId } = useParams();
    const [loadingProduct, setLoadingProduct] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [analysisStep, setAnalysisStep] = useState(0);
    const [product, setProduct] = useState(null);
    const [factories, setFactories] = useState([]);
    const [carbonReport, setCarbonReport] = useState(null);

    const [attestingNode, setAttestingNode] = useState(null);
    const [attestForm, setAttestForm] = useState({
        machinery_type: '',
        production_capacity: '',
        energy_sources: [],
        has_uploaded_evidence: true
    });
    const [isSubmittingAttest, setIsSubmittingAttest] = useState(false);

    const factoriesByNode = useMemo(() => {
        return new Map(factories.map((f) => [f.node_id, f]));
    }, [factories]);

    const maxEmissions = useMemo(() => {
        if (!factories.length) return 0;
        return Math.max(...factories.map((f) => Number(f.emissions?.total || 0)));
    }, [factories]);

    // ── React Flow nodes colored by emissions ───────────────────────────────
    const graphNodes = useMemo(() => {
        if (!product?.nodes) return [];
        return product.nodes.map((node, index) => {
            const intel = factoriesByNode.get(node.id);
            const emissions = Number(intel?.emissions?.total ?? 0);
            const confidence = Number(intel?.confidence ?? node.confidence_score ?? 0);
            let color =
                intel && maxEmissions > 0 && intel?.verification_status !== 'pending_attestation'
                    ? emissionNodeColor(emissions, maxEmissions)
                    : confidenceColor(confidence);
                    
            const isPendingAttestation = intel?.verification_status === 'pending_attestation';
            if (isPendingAttestation) {
                color = { bg: '#fffbeb', border: '#f59e0b', text: '#d97706' };
            }

            return {
                id: node.id,
                position: { x: 70 + index * 280, y: 80 },
                data: {
                    label: (
                        <div className="flex flex-col h-full w-full justify-center">
                            <p className="text-base font-bold text-gray-900 leading-snug">{node.company_name}</p>
                            <p className="text-xs text-gray-600 mt-0.5">{node.location}</p>
                            <p className="text-xs font-semibold uppercase tracking-wide mt-2" style={{ color: color.text }}>{roleLabel(node.role)}</p>
                            
                            <div className="mt-auto pt-2 border-t border-black/10 flex justify-between items-end">
                                <div>
                                    <p className="text-xs text-gray-500 uppercase tracking-wide">Emissions</p>
                                    <p className="text-sm font-bold" style={{ color: color.text }}>
                                        {emissions > 0 ? `${emissions.toLocaleString(undefined, {maximumFractionDigits: 0})} tCO₂` : '—'}
                                    </p>
                                </div>
                                <div className="text-right">
                                    <p className="text-xs text-gray-500 uppercase tracking-wide">Confidence</p>
                                    <p className="text-sm font-semibold" style={{ color: color.text }}>
                                        {isPendingAttestation ? 'Pending' : `${(confidence * 100).toFixed(0)}%`}
                                    </p>
                                </div>
                            </div>
                            
                            {isPendingAttestation && (
                                <button
                                    onMouseDown={(e) => {
                                        e.stopPropagation();
                                        setAttestingNode(node);
                                    }}
                                    className="mt-2 w-full flex items-center justify-center gap-1.5 py-1.5 rounded-md bg-orange-100 text-orange-700 hover:bg-orange-200 transition-colors border border-orange-200 text-xs font-bold shadow-sm"
                                >
                                    <MessageSquareShare className="w-3.5 h-3.5" />
                                    Awaiting Attestation
                                </button>
                            )}
                        </div>
                    ),
                },
                style: {
                    width: 280,
                    height: 140,
                    borderRadius: 16,
                    border: `2px solid ${color.border}`,
                    background: color.bg,
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                    padding: '14px 18px',
                    display: 'flex',
                    flexDirection: 'column',
                    wordWrap: 'break-word',
                    overflow: 'hidden'
                },
            };
        });
    }, [product?.nodes, factoriesByNode, maxEmissions]);

    const graphEdges = useMemo(() => {
        if (!product?.edges) return [];
        return product.edges.map((edge) => ({
            id: edge.id,
            source: edge.from_node_id,
            target: edge.to_node_id,
            label: edge.relation,
            style: { stroke: '#94a3b8', strokeWidth: 2 },
        }));
    }, [product?.edges]);

    // ── API calls ────────────────────────────────────────────────────────────
    const loadProduct = async () => {
        if (!productId) return;
        setLoadingProduct(true);
        try {
            const res = await getProductDetail(productId);
            setProduct(res.data);
            setFactories(res.data.factory_analysis || []);
            if (res.data.carbon_report) {
                setCarbonReport(res.data.carbon_report);
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to load product');
        } finally {
            setLoadingProduct(false);
        }
    };

    const runAggregation = async () => {
        try {
            const res = await aggregateProductCarbon(productId);
            setCarbonReport(res.data);
            toast.success('Product carbon certificate generated');
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Carbon aggregation failed');
        }
    };

    const runFactoryAnalysis = async () => {
        if (!productId) return;
        setAnalyzing(true);
        setAnalysisStep(0);
        const interval = setInterval(() => {
            setAnalysisStep((prev) => (prev + 1) % (ANALYSIS_STEPS.length - 1));
        }, 1000);
        try {
            const res = await analyzeProductFactories(productId);
            setFactories(res.data.factories || []);
            clearInterval(interval);
            setAnalysisStep(ANALYSIS_STEPS.length - 1);
            toast.success('Factory intelligence completed');
            await runAggregation();
            const detail = await getProductDetail(productId);
            setProduct(detail.data);
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Factory analysis failed');
        } finally {
            clearInterval(interval);
            setAnalyzing(false);
        }
    };

    useEffect(() => { loadProduct(); }, [productId]);
    useEffect(() => {
        if (!loadingProduct && productId) runFactoryAnalysis();
    }, [loadingProduct]);

    const riskStyle = cbamRiskStyle(carbonReport?.cbam_risk);

    const handleAttestSubmit = async (e) => {
        e.preventDefault();
        setIsSubmittingAttest(true);
        try {
            await attestProductNode(productId, attestingNode.id, attestForm);
            toast.success("Primary data successfully attested & verified!");
            setAttestingNode(null);
            
            // Re-fetch everything
            const detail = await getProductDetail(productId);
            setProduct(detail.data);
            setFactories(detail.data.factory_analysis || []);
            if (detail.data.carbon_report) {
                setCarbonReport(detail.data.carbon_report);
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Attestation failed.");
        } finally {
            setIsSubmittingAttest(false);
        }
    };

    // ── Render ───────────────────────────────────────────────────────────────
    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">

            {/* Header */}
            <div className="mb-8 flex items-start justify-between gap-4 flex-wrap">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 mb-1">
                        {product?.product_name || 'Loading product…'}
                    </h1>
                    <p className="text-gray-500 text-sm">
                        Sector: <span className="font-medium text-gray-700">{product?.sector || '…'}</span>
                        {carbonReport && (
                            <span className="ml-4">
                                Certificate hash:&nbsp;
                                <span className="font-mono text-xs text-gray-600">
                                    {carbonReport.report_hash.slice(0, 16)}…
                                </span>
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex gap-2">
                    <Link to={`/product/${productId}/optimize`} className="btn-secondary shrink-0">
                        Optimize Supply Chain
                    </Link>
                    <button
                        onClick={runFactoryAnalysis}
                        disabled={analyzing || loadingProduct}
                        className="btn-primary disabled:opacity-50 shrink-0"
                    >
                        {analyzing ? 'Analyzing…' : 'Re-run Analysis'}
                    </button>
                </div>
            </div>

            {/* Progress indicator */}
            {(loadingProduct || analyzing) && (
                <div className="card p-6 mb-6">
                    <p className="text-sm font-semibold text-gray-800 mb-2">Running intelligence pipeline…</p>
                    <div className="space-y-1">
                        {ANALYSIS_STEPS.map((step, i) => (
                            <p
                                key={step}
                                className={`text-sm flex items-center gap-2 ${i === analysisStep ? 'text-primary-700 font-semibold' : 'text-gray-400'}`}
                            >
                                {i < analysisStep ? <ShieldCheck className="w-4 h-4" /> : i === analysisStep ? <span className="w-4 h-4 rounded-full border-2 border-primary-500 border-t-transparent animate-spin" /> : <span className="w-4 h-4 rounded-full border-2 border-gray-300" />} {step}
                            </p>
                        ))}
                    </div>
                </div>
            )}

            {/* ── Section 1: Product Carbon Summary ────────────────────────── */}
            {carbonReport && (
                <div
                    className="rounded-2xl border p-6 mb-6"
                    style={{ borderColor: riskStyle.border, background: riskStyle.bg }}
                >
                    <h2 className="text-lg font-semibold mb-4" style={{ color: riskStyle.text }}>
                        Product Carbon Footprint
                    </h2>
                    
                    {carbonReport.cbam_savings_eur > 0 && (
                        <div className="mb-6 p-5 rounded-xl border-l-4 border-l-green-500 bg-white shadow-sm border border-gray-100 flex gap-4 items-start">
                            <div className="bg-green-100 text-green-700 p-2 rounded-lg shrink-0 mt-0.5">
                                <ShieldCheck className="w-6 h-6" />
                            </div>
                            <div>
                                <h3 className="text-xl font-extrabold text-gray-900 mb-2 tracking-tight">
                                    Savings via Direct Attestation 
                                </h3>
                                <p className="text-base text-gray-800 leading-relaxed">
                                    EU default for your product category: <span className="font-bold">{carbonReport.eu_default_penalty?.toFixed(2) || '4.32'} tCO₂/t</span>. <br/>
                                    Your calculated actual: <span className="font-bold text-green-700">{carbonReport.emission_intensity.toFixed(2)} tCO₂/t</span>. <br/>
                                    <span className="block mt-2 font-medium text-gray-900 bg-green-50 p-2 rounded text-sm border border-green-100">
                                        At your export volume of {carbonReport.product_quantity} tonnes this year, you default to overpaying <span className="font-bold text-red-600">€{carbonReport.cbam_savings_eur.toLocaleString(undefined, {maximumFractionDigits: 0})} (₹{(carbonReport.cbam_savings_inr / 100000).toFixed(1)} Lakh)</span> by not submitting verified actual data.
                                    </span>
                                </p>
                            </div>
                        </div>
                    )}

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="bg-white rounded-xl border border-gray-100 p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                                {carbonReport.total_emissions.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Total tCO₂</p>
                        </div>
                        <div className="bg-white rounded-xl border border-gray-100 p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                                {carbonReport.emission_intensity.toFixed(2)}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">tCO₂ / ton</p>
                        </div>
                        <div className="bg-white rounded-xl border border-gray-100 p-4 text-center">
                            <p className="text-2xl font-bold text-gray-900">
                                {(carbonReport.product_confidence * 100).toFixed(0)}%
                            </p>
                            <p className="text-xs text-gray-500 mt-1">Confidence</p>
                        </div>
                        <div
                            className="rounded-xl border p-4 text-center"
                            style={{ borderColor: riskStyle.border, background: 'white' }}
                        >
                            <p className="text-2xl font-bold" style={{ color: riskStyle.text }}>
                                {riskStyle.label}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">CBAM Risk</p>
                        </div>
                    </div>
                    <div className="mt-4 grid grid-cols-3 gap-3 text-sm text-gray-700">
                        <div className="bg-white rounded-lg border border-gray-100 p-3">
                            <span className="text-gray-500">Scope 1</span>
                            <p className="font-semibold">{carbonReport.scope1_total.toFixed(1)} tCO₂</p>
                        </div>
                        <div className="bg-white rounded-lg border border-gray-100 p-3">
                            <span className="text-gray-500">Scope 2</span>
                            <p className="font-semibold">{carbonReport.scope2_total.toFixed(1)} tCO₂</p>
                        </div>
                        <div className="bg-white rounded-lg border border-gray-100 p-3">
                            <span className="text-gray-500">Scope 3</span>
                            <p className="font-semibold">{carbonReport.scope3_total.toFixed(1)} tCO₂</p>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Section 3: Supply Chain Emission Map (React Flow) ─────────── */}
            <div className="card p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Supply Chain Emission Map</h2>
                {graphNodes.length > 0 ? (
                    <div className="rounded-xl border border-gray-200 overflow-hidden" style={{ height: 320 }}>
                        <ReactFlow
                            nodes={graphNodes}
                            edges={graphEdges}
                            fitView
                            nodesDraggable={false}
                            nodesConnectable={false}
                            elementsSelectable={false}
                        >
                            <MiniMap zoomable pannable />
                            <Controls showInteractive={false} />
                            <Background gap={20} size={1} color="#e2e8f0" />
                        </ReactFlow>
                    </div>
                ) : (
                    <p className="text-sm text-gray-500">No supply chain nodes found.</p>
                )}
                <p className="text-xs text-gray-400 mt-2">
                    Node color scale: <span className="text-green-600 font-medium">Low (Green)</span> · <span className="text-amber-500 font-medium">Medium (Yellow)</span> · <span className="text-red-500 font-medium">High (Red)</span>
                </p>
            </div>

            {/* ── Section 2 + 4: Charts row ─────────────────────────────────── */}
            {carbonReport && carbonReport.factory_contributions?.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

                    {/* Section 2 — Factory Contribution Chart */}
                    <div className="card p-6">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">Factory Contribution</h2>
                        <ResponsiveContainer width="100%" height={Math.max(180, carbonReport.factory_contributions.length * 52)}>
                            <BarChart
                                layout="vertical"
                                data={carbonReport.factory_contributions}
                                margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
                            >
                                <XAxis
                                    type="number"
                                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                                    tick={{ fontSize: 11 }}
                                />
                                <YAxis
                                    type="category"
                                    dataKey="company"
                                    width={130}
                                    tick={{ fontSize: 11 }}
                                    tickFormatter={(v) => v.length > 18 ? `${v.slice(0, 18)}…` : v}
                                />
                                <Tooltip
                                    formatter={(value, name) => [`${Number(value).toFixed(1)} tCO₂`, 'Total Emissions']}
                                    labelFormatter={(label) => label}
                                />
                                <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                                    {carbonReport.factory_contributions.map((entry, i) => (
                                        <Cell key={i} fill={barColor(entry.percentage)} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                        <div className="flex gap-4 justify-end mt-2 text-xs font-semibold">
                            <span className="text-green-600">&lt;20%</span>
                            <span className="text-amber-500">20–40%</span>
                            <span className="text-red-500">&gt;40%</span>
                        </div>
                    </div>

                    {/* Section 4 — EU Compliance Analysis */}
                    <div className="card p-6">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">EU CBAM Compliance</h2>
                        <div className="space-y-4">
                            {/* Intensity vs benchmark bar */}
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="text-gray-600">Emission Intensity</span>
                                    <span className="font-semibold text-gray-900">
                                        {carbonReport.emission_intensity.toFixed(3)} tCO₂/ton
                                    </span>
                                </div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="text-gray-600">EU Benchmark ({product?.sector})</span>
                                    <span className="font-semibold text-gray-900">
                                        {carbonReport.eu_benchmark.toFixed(2)} tCO₂/ton
                                    </span>
                                </div>
                                <div className="relative h-4 bg-gray-100 rounded-full overflow-hidden mt-2">
                                    <div
                                        className="absolute top-0 left-0 h-full rounded-full"
                                        style={{
                                            width: `${Math.min((carbonReport.emission_intensity / Math.max(carbonReport.eu_benchmark * 2, carbonReport.emission_intensity)) * 100, 100)}%`,
                                            background: carbonReport.emission_intensity > carbonReport.eu_benchmark ? '#ef4444' : '#10b981',
                                        }}
                                    />
                                    {/* benchmark marker */}
                                    <div
                                        className="absolute top-0 h-full border-l-2 border-gray-600"
                                        style={{
                                            left: `${Math.min((carbonReport.eu_benchmark / Math.max(carbonReport.eu_benchmark * 2, carbonReport.emission_intensity)) * 100, 100)}%`,
                                        }}
                                    />
                                </div>
                                <p className="text-xs text-gray-400 mt-1">| = EU benchmark</p>
                            </div>

                            {/* Status badge */}
                            <div
                                className="rounded-lg border px-4 py-3 flex items-center gap-3"
                                style={{ borderColor: riskStyle.border, background: riskStyle.bg }}
                            >
                                <span className="flex items-center justify-center p-2 rounded-xl bg-white/50">
                                    {carbonReport.excess_emissions > 0 ? <AlertTriangle className="w-8 h-8 text-red-600" /> : <ShieldCheck className="w-8 h-8 text-green-600" />}
                                </span>
                                <div>
                                    {carbonReport.excess_emissions > 0 ? (
                                        <>
                                            <p className="text-sm font-semibold" style={{ color: riskStyle.text }}>
                                                Exceeds EU benchmark by&nbsp;
                                                {carbonReport.excess_emissions.toFixed(3)} tCO₂/ton
                                            </p>
                                            <p className="text-sm" style={{ color: riskStyle.text }}>
                                                CBAM tax: ~€{carbonReport.cbam_tax_per_ton.toFixed(2)} per ton
                                            </p>
                                        </>
                                    ) : (
                                        <p className="text-sm font-semibold text-green-800">
                                            Within EU benchmark — no CBAM tax applies
                                        </p>
                                    )}
                                </div>
                            </div>

                            {/* Factory count */}
                            <p className="text-sm text-gray-500">
                                Based on&nbsp;
                                <span className="font-semibold text-gray-700">{carbonReport.factory_count} verified factories</span>
                                &nbsp;·&nbsp;product quantity&nbsp;
                                <span className="font-semibold text-gray-700">
                                    {carbonReport.product_quantity.toLocaleString()} tons
                                </span>
                            </p>

                            {/* Scope breakdown */}
                            <div className="text-xs text-gray-500 space-y-1 border-t pt-3 mt-2">
                                <p className="font-semibold text-gray-700 mb-1">Scope breakdown across supply chain</p>
                                {[
                                    { label: 'Scope 1 (Direct)', value: carbonReport.scope1_total, total: carbonReport.total_emissions },
                                    { label: 'Scope 2 (Energy)', value: carbonReport.scope2_total, total: carbonReport.total_emissions },
                                    { label: 'Scope 3 (Indirect)', value: carbonReport.scope3_total, total: carbonReport.total_emissions },
                                ].map(({ label, value, total }) => (
                                    <div key={label}>
                                        <div className="flex justify-between mb-0.5">
                                            <span>{label}</span>
                                            <span className="font-medium text-gray-600">
                                                {value.toFixed(0)} tCO₂ ({total > 0 ? ((value / total) * 100).toFixed(0) : 0}%)
                                            </span>
                                        </div>
                                        <div className="h-1.5 bg-gray-100 rounded-full">
                                            <div
                                                className="h-full rounded-full bg-primary-500"
                                                style={{ width: `${total > 0 ? Math.min((value / total) * 100, 100) : 0}%` }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Factory Intelligence Cards ─────────────────────────────────── */}
            <div className="card p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Factory Intelligence</h2>
                {factories.length === 0 ? (
                    <p className="text-sm text-gray-500">No factory analysis available yet.</p>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {factories.map((factory) => {
                            const confidence = Number(factory.confidence || 0);
                            const color = confidenceColor(confidence);
                            return (
                                <div key={factory.factory_profile_id} className="rounded-xl border border-gray-200 p-4">
                                    <p className="text-base font-semibold text-gray-900">
                                        {factory.company}
                                        <span className="text-gray-400 font-normal"> — {factory.location}</span>
                                    </p>
                                    <div className="mt-2 space-y-0.5 text-sm text-gray-600">
                                        <p>Machinery: <span className="font-medium text-gray-800">{factory.machinery}</span></p>
                                        <p>Capacity: <span className="font-medium text-gray-800">{Number(factory.production_capacity || 0).toLocaleString()} t/yr</span></p>
                                        <p>
                                            Emissions:&nbsp;
                                            <span className="font-bold text-gray-900">{Number(factory.emissions?.total || 0).toFixed(1)} tCO₂</span>
                                            <span className="text-xs text-gray-400"> (S1 {Number(factory.emissions?.scope1 || 0).toFixed(0)} · S2 {Number(factory.emissions?.scope2 || 0).toFixed(0)} · S3 {Number(factory.emissions?.scope3 || 0).toFixed(0)})</span>
                                        </p>
                                    </div>
                                    <div className="mt-2 flex items-center justify-between">
                                        <p className="text-sm font-medium" style={{ color: color.text }}>
                                            Confidence {(confidence * 100).toFixed(0)}% · {factory.verification_status}
                                        </p>
                                        {factory.verification_status === 'pending_attestation' && (
                                            <button
                                                onClick={() => setAttestingNode(factory)}
                                                className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-semibold rounded hover:bg-amber-200 transition-colors"
                                            >
                                                Awaiting Attestation
                                            </button>
                                        )}
                                    </div>
                                    {confidence < 0.50 && (
                                        <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-lg">
                                            <div className="flex gap-2">
                                                <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                                                <div className="text-xs text-red-800 leading-relaxed">
                                                    <p className="font-semibold mb-1 tracking-tight">Low Confidence Estimate</p>
                                                    <p>This estimate may differ significantly from your actual emissions. Entering your electricity bill data will improve accuracy to 0.85 and reduce your CBAM default risk.</p>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* ── Attestation Modal ─────────────────────────────────────────── */}
            {attestingNode && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between p-4 border-b">
                            <div>
                                <h3 className="text-lg font-bold text-gray-900">Direct Attestation</h3>
                                <p className="text-xs text-gray-500">Track 2: MSME Supply Chain Verification</p>
                            </div>
                            <button
                                onClick={() => setAttestingNode(null)}
                                className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleAttestSubmit} className="p-4 space-y-4">
                            <div className="bg-orange-50 text-orange-800 p-3 rounded-lg text-sm mb-4">
                                <p className="font-semibold mb-1">WhatsApp Form Simulation</p>
                                <p>Simulating the automated MSME outreach via messaging apps when web scraping returns zero footprint for <b>{attestingNode.company_name}</b>.</p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Machinery Used</label>
                                <select
                                    required
                                    className="input focus:ring-primary-500 w-full"
                                    value={attestForm.machinery_type}
                                    onChange={(e) => setAttestForm({...attestForm, machinery_type: e.target.value})}
                                >
                                    <option value="">Select machinery…</option>
                                    <option value="electric_arc_furnace">Electric Arc Furnace</option>
                                    <option value="basic_oxygen_furnace">Basic Oxygen Furnace</option>
                                    <option value="induction_furnace">Induction Furnace</option>
                                    <option value="cnc_machining">CNC Machining</option>
                                    <option value="injection_molding">Injection Molding</option>
                                    <option value="stamping_press">Stamping Press</option>
                                    <option value="other">Other / General Manufacturing</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Annual Production Volume (Tonnes)</label>
                                <input
                                    type="number"
                                    required
                                    min="1"
                                    className="input focus:ring-primary-500 w-full"
                                    placeholder="e.g. 15000"
                                    value={attestForm.production_capacity}
                                    onChange={(e) => setAttestForm({...attestForm, production_capacity: e.target.value})}
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Energy Sources (Select all that apply)</label>
                                <div className="space-y-2">
                                    {['grid electricity', 'solar', 'coal', 'natural gas', 'diesel'].map((src) => (
                                        <label key={src} className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                                                checked={attestForm.energy_sources.includes(src)}
                                                onChange={(e) => {
                                                    const sources = new Set(attestForm.energy_sources);
                                                    if (e.target.checked) sources.add(src);
                                                    else sources.delete(src);
                                                    setAttestForm({...attestForm, energy_sources: Array.from(sources)});
                                                }}
                                            />
                                            <span className="text-sm text-gray-700 capitalize">{src}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                            
                            {/* Dummy file upload */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Provide Evidence (e.g. Electricity Bill)</label>
                                <input
                                    type="file"
                                    className="block w-full text-sm text-gray-500
                                      file:mr-4 file:py-2 file:px-4
                                      file:rounded-full file:border-0
                                      file:text-sm file:font-semibold
                                      file:bg-primary-50 file:text-primary-700
                                      hover:file:bg-primary-100
                                    "
                                    onChange={() => setAttestForm({...attestForm, has_uploaded_evidence: true})}
                                />
                            </div>

                            <div className="pt-4 border-t mt-6 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setAttestingNode(null)}
                                    className="btn-secondary flex-1"
                                    disabled={isSubmittingAttest}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="btn-primary flex-1"
                                    disabled={isSubmittingAttest || !attestForm.machinery_type || !attestForm.production_capacity || attestForm.energy_sources.length === 0}
                                >
                                    {isSubmittingAttest ? 'Verifying...' : 'Seal to Blockchain & Verify'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

        </div>
    );
}
