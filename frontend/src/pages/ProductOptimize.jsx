/**
 * Supply chain optimization dashboard (Phase 4).
 */

import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getProductDetail, optimizeProductSupplyChain } from '../utils/api';
import { AlertTriangle, Zap, Sun, Settings2, Leaf, Box, ArrowRightCircle } from 'lucide-react';

function roleLabel(role) {
  return String(role || '').replaceAll('_', ' ');
}

function buildGraphNodes(nodes, targetFactory, replacementCompany, mode = 'before') {
  return (nodes || []).map((node, index) => {
    const isTarget = String(node.company_name || '').toLowerCase() === String(targetFactory || '').toLowerCase();
    const shownName = mode === 'after' && isTarget && replacementCompany
      ? replacementCompany
      : node.company_name;

    return {
      id: `${mode}-${node.id}`,
      position: { x: 70 + index * 220, y: 80 },
      data: {
        label: (
          <div className="text-left">
            <p className="text-xs font-semibold text-gray-900">{shownName}</p>
            <p className="text-[11px] text-gray-600">{node.location}</p>
            <p className="text-[11px] text-gray-700">{roleLabel(node.role)}</p>
            {mode === 'after' && isTarget && replacementCompany && (
              <p className="text-[10px] font-semibold text-green-700">Replaced</p>
            )}
          </div>
        ),
      },
      style: {
        width: 180,
        borderRadius: 12,
        border: isTarget
          ? mode === 'after' && replacementCompany
            ? '1px solid #10b981'
            : '1px solid #f59e0b'
          : '1px solid #cbd5e1',
        background: isTarget
          ? mode === 'after' && replacementCompany
            ? '#ecfdf5'
            : '#fffbeb'
          : '#f8fafc',
        padding: 8,
        fontSize: 12,
      },
    };
  });
}

function buildGraphEdges(edges, mode = 'before') {
  return (edges || []).map((edge) => ({
    id: `${mode}-${edge.id}`,
    source: `${mode}-${edge.from_node_id}`,
    target: `${mode}-${edge.to_node_id}`,
    label: edge.relation,
    style: { stroke: '#94a3b8' },
  }));
}

export default function ProductOptimize() {
  const { productId } = useParams();
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [product, setProduct] = useState(null);
  const [result, setResult] = useState(null);
  const [targetFactory, setTargetFactory] = useState('');
  const [selectedSupplier, setSelectedSupplier] = useState(null);

  const loadData = async () => {
    if (!productId) return;
    setLoading(true);
    try {
      const detail = await getProductDetail(productId);
      setProduct(detail.data);

      const optimize = await optimizeProductSupplyChain(productId, {
        target_factory: null,
        product_quantity: 1000,
      });
      setResult(optimize.data);
      setTargetFactory(optimize.data.target_factory || '');
      setSelectedSupplier(optimize.data.suggested_suppliers?.[0] || null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load optimization data');
    } finally {
      setLoading(false);
    }
  };

  const runOptimization = async (factoryName) => {
    if (!productId) return;
    setOptimizing(true);
    try {
      const optimize = await optimizeProductSupplyChain(productId, {
        target_factory: factoryName || null,
        product_quantity: 1000,
      });
      setResult(optimize.data);
      setTargetFactory(optimize.data.target_factory || '');
      setSelectedSupplier(optimize.data.suggested_suppliers?.[0] || null);
      toast.success('Optimization simulation updated');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Optimization failed');
    } finally {
      setOptimizing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [productId]);

  const highestFactory = useMemo(() => result?.current_factories?.[0] || null, [result]);

  const comparisonData = useMemo(() => {
    if (!result) return [];
    return [
      { name: 'Current Emissions', value: Number(result.current_emissions || 0) },
      { name: 'Optimized Emissions', value: Number(selectedSupplier?.optimized_total_emissions || result.optimized_emissions || 0) },
      { name: 'Current CBAM Tax', value: Number(result.current_cbam_tax || 0) },
      { name: 'Optimized CBAM Tax', value: Number(selectedSupplier?.optimized_cbam_tax_total || result.optimized_cbam_tax || 0) },
    ];
  }, [result, selectedSupplier]);

  const beforeNodes = useMemo(() => buildGraphNodes(product?.nodes, targetFactory, null, 'before'), [product?.nodes, targetFactory]);
  const beforeEdges = useMemo(() => buildGraphEdges(product?.edges, 'before'), [product?.edges]);
  const afterNodes = useMemo(
    () => buildGraphNodes(product?.nodes, targetFactory, selectedSupplier?.company || '', 'after'),
    [product?.nodes, targetFactory, selectedSupplier?.company]
  );
  const afterEdges = useMemo(() => buildGraphEdges(product?.edges, 'after'), [product?.edges]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">
      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Supply Chain Optimization</h1>
          <p className="text-gray-500 text-sm mt-1">
            {product?.product_name || 'Loading product...'}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/product/${productId}`} className="btn-secondary">
            Back to Product
          </Link>
          <button
            onClick={() => runOptimization(targetFactory)}
            disabled={optimizing || loading}
            className="btn-primary disabled:opacity-50"
          >
            {optimizing ? 'Simulating...' : 'Re-run Optimization'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="card p-6">
          <p className="text-sm text-gray-600">Loading optimization analysis...</p>
        </div>
      ) : (
        <>
          {result && (
            <div className="card p-6 mb-8 border-l-4 border-l-primary-600 shadow-md">
              <h2 className="text-xl font-bold text-gray-900 mb-2 tracking-tight">Optimization Impact Summary</h2>
              <p className="text-sm text-gray-600 mb-4 leading-relaxed">
                By executing the tiered strategy below, you can bypass the EU's punitive <span className="font-semibold text-red-600">4.32 tCO₂/t default penalty</span>, drop your verified intensity to <span className="font-semibold text-green-700">{Number(selectedSupplier?.optimized_intensity || result.optimized_intensity || 0).toFixed(2)} tCO₂/t</span>, and secure <span className="font-bold text-green-700 underline decoration-green-300 decoration-2">€{Number(selectedSupplier?.cbam_savings || result.cbam_savings || 0).toFixed(0)}</span> in CBAM tax savings this year.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-gray-50 rounded-xl border border-gray-200 p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide font-semibold">Current Emissions</p>
                  <p className="text-xl font-bold text-gray-900">{Number(result.current_emissions || 0).toFixed(1)} tCO₂</p>
                </div>
                <div className="bg-green-50 rounded-xl border border-green-200 p-4">
                  <p className="text-xs text-green-800 uppercase tracking-wide font-semibold">Target Emissions</p>
                  <p className="text-xl font-bold text-green-700">{Number(selectedSupplier?.optimized_total_emissions || result.optimized_emissions || 0).toFixed(1)} tCO₂</p>
                </div>
                <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
                  <p className="text-xs text-blue-800 uppercase tracking-wide font-semibold">Verified Intensity</p>
                  <p className="text-xl font-bold text-blue-700">{Number(selectedSupplier?.optimized_intensity || result.optimized_intensity || 0).toFixed(2)} tCO₂/t</p>
                </div>
                <div className="bg-emerald-50 shadow-inner rounded-xl border border-emerald-300 p-4">
                  <p className="text-xs text-emerald-800 uppercase tracking-wide font-semibold">Annual CBAM Savings</p>
                  <p className="text-xl font-bold text-emerald-700">€{Number(selectedSupplier?.cbam_savings || result.cbam_savings || 0).toFixed(0)}</p>
                </div>
              </div>
            </div>
          )}

          {/* ── TIER 1 ──────────────────────────────────────────────────────── */}
          <div className="mb-8">
            <h3 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
              <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm font-black">Tier 1</span>
              Immediate Actions <span className="text-gray-400 font-medium ml-1 text-lg">(Zero Cost, High ROI)</span>
            </h3>
            <p className="text-sm text-gray-600 mb-4">Execute these operational changes this week to instantly lower your Scope 2 footprint before the next verification cycle.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="card p-5 hover:border-blue-300 transition-colors">
                    <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-3">
                        <Zap className="w-5 h-5 text-blue-600" />
                    </div>
                    <h4 className="font-bold text-gray-900 mb-1">Open Access Green Tariff</h4>
                    <p className="text-sm text-gray-600 leading-relaxed mb-3">Sign a short-term PPA with the state grid to source 40% of electricity from solar/wind.</p>
                    <div className="bg-gray-50 p-2 rounded border border-gray-100 text-xs text-gray-700">
                        <span className="font-semibold text-green-700">Expected ROI:</span> -12% Scope 2
                    </div>
                </div>

                <div className="card p-5 hover:border-amber-300 transition-colors">
                    <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center mb-3">
                        <Sun className="w-5 h-5 text-amber-600" />
                    </div>
                    <h4 className="font-bold text-gray-900 mb-1">Shift Timing Alignment</h4>
                    <p className="text-sm text-gray-600 leading-relaxed mb-3">Move high-load induction furnace operations entirely to daytime solar-peak hours (10 AM - 4 PM).</p>
                    <div className="bg-gray-50 p-2 rounded border border-gray-100 text-xs text-gray-700">
                        <span className="font-semibold text-green-700">Expected ROI:</span> Reduces grid-stress penalty
                    </div>
                </div>

                <div className="card p-5 hover:border-purple-300 transition-colors">
                    <div className="w-10 h-10 bg-purple-50 rounded-lg flex items-center justify-center mb-3">
                        <Settings2 className="w-5 h-5 text-purple-600" />
                    </div>
                    <h4 className="font-bold text-gray-900 mb-1">Compressor Optimization</h4>
                    <p className="text-sm text-gray-600 leading-relaxed mb-3">Fix pneumatic leaks and reduce baseline compressor pressure by 1 bar on the main assembly line.</p>
                    <div className="bg-gray-50 p-2 rounded border border-gray-100 text-xs text-gray-700">
                        <span className="font-semibold text-green-700">Expected ROI:</span> -4% total energy draw
                    </div>
                </div>
            </div>
          </div>

          {/* ── TIER 2 ──────────────────────────────────────────────────────── */}
          <div className="mb-10">
            <h3 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
              <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm font-black">Tier 2</span>
              Quarterly Upgrades <span className="text-gray-400 font-medium ml-1 text-lg">(Low Capex, 1-Year Payback)</span>
            </h3>
            <p className="text-sm text-gray-600 mb-4">Invest in established efficiency technologies that directly lower your Scope 1 & 2 baseline, easily paying for themselves in avoided CBAM taxes.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="card p-5 hover:border-green-300 transition-colors flex gap-4">
                    <div className="w-12 h-12 shrink-0 bg-green-50 rounded-xl flex items-center justify-center border border-green-100">
                        <Leaf className="w-6 h-6 text-green-600" />
                    </div>
                    <div>
                        <h4 className="font-bold text-gray-900 mb-1">Waste Heat Recovery (WHRS)</h4>
                        <p className="text-sm text-gray-600 leading-relaxed max-w-sm mb-3">Capture exhaust heat from curing ovens to pre-heat boiler feedwater. Reduces coal/gas consumption directly.</p>
                        <span className="inline-block bg-green-50 text-green-800 text-xs font-semibold px-2.5 py-1 rounded border border-green-200">
                            -15% Scope 1 Impact
                        </span>
                    </div>
                </div>

                <div className="card p-5 hover:border-green-300 transition-colors flex gap-4">
                    <div className="w-12 h-12 shrink-0 bg-green-50 rounded-xl flex items-center justify-center border border-green-100">
                        <Zap className="w-6 h-6 text-green-600" />
                    </div>
                    <div>
                        <h4 className="font-bold text-gray-900 mb-1">Variable Frequency Drives (VFD)</h4>
                        <p className="text-sm text-gray-600 leading-relaxed max-w-sm mb-3">Install VFDs on heavy blowers and exhaust fans to match motor speed to dynamic production load.</p>
                        <span className="inline-block bg-green-50 text-green-800 text-xs font-semibold px-2.5 py-1 rounded border border-green-200">
                            -8% Scope 2 Impact
                        </span>
                    </div>
                </div>
            </div>
          </div>

          <hr className="my-10 border-gray-200" />

          {/* ── TIER 3: Strategic Replacement ─────────────────────────────── */}
          <div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
              <span className="bg-gray-800 text-white px-3 py-1 rounded-full text-sm font-black">Tier 3</span>
              Strategic Re-Sourcing <span className="text-gray-400 font-medium ml-1 text-lg">(Long-Term Supply Chain Pivot)</span>
            </h3>
            <p className="text-sm text-gray-600 mb-6 max-w-3xl">Replacing your suppliers is difficult, but substituting exactly one high-emission Tier 2 node with an Electric Arc Furnace (EAF) or Hydrogen-reduction alternate fundamentally drops the embedded footprint of your exported products.</p>
            
            {highestFactory && (
                <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 mb-6 shadow-sm">
                <p className="text-sm font-semibold text-amber-800 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 flex-shrink-0" /> <span className="font-bold">{highestFactory.company}</span> contributes {(Number(highestFactory.share || 0) * 100).toFixed(1)}% of your total emissions. Targeting this node yields the highest ROI.
                </p>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <div className="card p-6 bg-gray-50 border-gray-200">
                <h2 className="text-sm tracking-wide uppercase font-bold text-gray-500 mb-4">Suggested Alternative Suppliers</h2>
                {!result?.suggested_suppliers?.length ? (
                    <p className="text-sm text-gray-500">No alternatives found.</p>
                ) : (
                    <div className="space-y-3">
                    {result.suggested_suppliers.map((supplier, index) => {
                        const isSelected = selectedSupplier?.company === supplier.company;
                        return (
                        <div key={`${supplier.company}-${index}`} className={`rounded-xl border p-4 transition-all ${isSelected ? 'border-primary-500 bg-white shadow-md ring-1 ring-primary-500' : 'border-gray-200 bg-white hover:border-gray-300'}`}>
                            <div className="flex items-start justify-between gap-3">
                            <div>
                                <p className="text-base font-bold text-gray-900 mb-0.5">{supplier.company}</p>
                                <p className="text-xs text-gray-500 mb-2">{supplier.location} • {supplier.machinery.replace(/_/g, ' ')}</p>
                                <p className="text-xs font-medium text-green-700 bg-green-50 inline-block px-2 py-0.5 rounded border border-green-100">
                                    Est. {Number(supplier.estimated_emissions || 0).toFixed(1)} tCO₂
                                </p>
                            </div>
                            <button
                                onClick={() => setSelectedSupplier(supplier)}
                                className={`shrink-0 flex items-center gap-2 text-sm font-semibold px-3 py-1.5 rounded-lg border transition-colors ${isSelected ? 'bg-primary-50 text-primary-700 border-primary-200' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
                            >
                                {isSelected ? 'Simulating' : 'Simulate'}
                                <ArrowRightCircle className="w-4 h-4" />
                            </button>
                            </div>
                        </div>
                        );
                    })}
                    </div>
                )}
                </div>

                <div className="card p-6 bg-gray-50 border-gray-200">
                <h2 className="text-sm tracking-wide uppercase font-bold text-gray-500 mb-4">Emissions & Tax Delta</h2>
                <div style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData} margin={{ top: 10, right: 20, bottom: 40, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="name" angle={-15} textAnchor="end" interval={0} height={70} tick={{fontSize: 11, fill: '#64748b'}} />
                        <YAxis tick={{fontSize: 11, fill: '#64748b'}} axisLine={false} tickLine={false} />
                        <Tooltip 
                            formatter={(value) => Number(value).toFixed(2)}
                            cursor={{fill: '#f1f5f9'}}
                            contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}} 
                        />
                        <Bar dataKey="value" fill="#1A6B3A" radius={[4, 4, 0, 0]} maxBarSize={50} />
                    </BarChart>
                    </ResponsiveContainer>
                </div>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="card p-6">
                <h2 className="text-sm uppercase tracking-wide font-bold text-gray-500 mb-3">Supply Chain Vector — Current</h2>
                <div className="rounded-xl border border-gray-200 overflow-hidden bg-gray-50" style={{ height: 320 }}>
                    <ReactFlow
                    nodes={beforeNodes}
                    edges={beforeEdges}
                    fitView
                    nodesDraggable={false}
                    nodesConnectable={false}
                    elementsSelectable={false}
                    >
                    <MiniMap zoomable pannable nodeColor="#cbd5e1" maskColor="rgba(248, 250, 252, 0.7)" />
                    <Controls showInteractive={false} />
                    <Background gap={20} size={1} color="#cbd5e1" />
                    </ReactFlow>
                </div>
                </div>

                <div className="card p-6 border-primary-200 shadow-sm ring-1 ring-primary-50">
                <h2 className="text-sm uppercase tracking-wide font-bold text-primary-700 mb-3">Supply Chain Vector — Target</h2>
                <div className="rounded-xl border border-gray-200 overflow-hidden bg-white" style={{ height: 320 }}>
                    <ReactFlow
                    nodes={afterNodes}
                    edges={afterEdges}
                    fitView
                    nodesDraggable={false}
                    nodesConnectable={false}
                    elementsSelectable={false}
                    >
                    <MiniMap zoomable pannable nodeColor="#bbf7d0" maskColor="rgba(255, 255, 255, 0.7)" />
                    <Controls showInteractive={false} />
                    <Background gap={20} size={1} color="#e2e8f0" />
                    </ReactFlow>
                </div>
                </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
