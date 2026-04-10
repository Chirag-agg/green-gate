import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import { confirmProductSupplyChain, discoverProductSupplyChain } from '../utils/api';
import { ArrowLeft, ArrowRight, CheckCircle2, PackageSearch } from 'lucide-react';

const PIPELINE_STEPS = [
    'Analyzing manufacturer networks',
    'Extracting production stages',
];

function roleLabel(role) {
    return role.replaceAll('_', ' ');
}

function ensureRole(role) {
    const normalized = String(role || '').trim().toLowerCase().replaceAll(' ', '_');
    const allowed = new Set(['raw_material', 'processing', 'manufacturing', 'assembly', 'logistics']);
    return allowed.has(normalized) ? normalized : 'manufacturing';
}

export default function ProductNew() {
    const navigate = useNavigate();
    
    // MSME Guided Interview State
    const [step, setStep] = useState(1);
    const [answers, setAnswers] = useState({
        rawMaterial: '',
        supplierName: '',
        locationGrid: '',
        fuelMachinery: '',
        productionVolume: '',
    });

    const [loading, setLoading] = useState(false);
    const [confirming, setConfirming] = useState(false);
    const [loadingStep, setLoadingStep] = useState(0);
    const [discovery, setDiscovery] = useState(null);

    const handleAnswerChange = (field, value) => {
        setAnswers(prev => ({ ...prev, [field]: value }));
    };

    const nextStep = () => setStep(prev => prev + 1);
    const prevStep = () => setStep(prev => prev - 1);

    const isStepValid = () => {
        switch (step) {
            case 1: return answers.rawMaterial.trim().length > 0;
            case 2: return answers.supplierName.trim().length > 0;
            case 3: return answers.locationGrid.trim().length > 0;
            case 4: return answers.fuelMachinery.trim().length > 0;
            case 5: return answers.productionVolume.trim().length > 0;
            default: return true;
        }
    };

    const graphNodes = useMemo(
        () => (discovery?.nodes || []).map((node, index) => ({
            id: node.id || `idx-${index}`,
            position: { x: 70 + (index * 240), y: 80 },
            data: {
                label: (
                    <div className="text-left w-full h-full flex flex-col justify-center">
                        <p className="text-sm font-bold text-gray-900 leading-tight">{node.company_name}</p>
                        <p className="text-xs font-semibold text-primary-700 mt-1 uppercase tracking-wide">{roleLabel(node.role)}</p>
                        <p className="text-xs text-gray-600 mt-2">{node.location}</p>
                    </div>
                ),
            },
            style: {
                width: 200,
                height: 100,
                borderRadius: 16,
                border: '1px solid rgba(255, 255, 255, 0.4)',
                background: 'rgba(255, 255, 255, 0.6)',
                backdropFilter: 'blur(12px)',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
                padding: 16,
                fontSize: 14,
            },
        })),
        [discovery?.nodes]
    );

    const graphEdges = useMemo(() => {
        if (discovery?.edges?.length) {
            return discovery.edges.map((edge) => ({
                id: edge.id,
                source: edge.from_node_id,
                target: edge.to_node_id,
                animated: false,
                label: edge.relation,
                style: { stroke: '#94a3b8', strokeWidth: 2 },
            }));
        }

        const nodes = discovery?.nodes || [];
        return nodes.slice(0, -1).map((node, index) => ({
            id: `chain-${index}`,
            source: nodes[index].id || `idx-${index}`,
            target: nodes[index + 1].id || `idx-${index + 1}`,
            label: 'supplies to',
            style: { stroke: '#94a3b8', strokeWidth: 2 },
        }));
    }, [discovery?.edges, discovery?.nodes]);

    const runDiscovery = async () => {
        setLoading(true);
        setLoadingStep(0);

        const interval = setInterval(() => {
            setLoadingStep((prev) => (prev + 1) % PIPELINE_STEPS.length);
        }, 900);

        try {
            // Synthesize the guided answers into the required backend payload
            const syntheticPayload = {
                company_name: 'My Manufacturing Company',
                potential_supplier: answers.supplierName,
                product_name: answers.rawMaterial,
                sector: 'manufacturing', // Broad sector, backend uses LLM to deduce specifics
            };

            const res = await discoverProductSupplyChain(syntheticPayload);
            setDiscovery(res.data);
            setStep(6); // Move to results view
            toast.success('Supply chain mapped successfully');
        } catch (err) {
            const msg = err.response?.data?.detail || 'Discovery failed';
            toast.error(msg);
        } finally {
            clearInterval(interval);
            setLoading(false);
        }
    };

    const confirmSupplyChain = async () => {
        if (!discovery?.product_id) {
            return;
        }

        const cleanedNodes = (discovery?.nodes || [])
            .map((node, index) => ({
                id: node.id || `idx-${index}`,
                company_name: String(node.company_name || '').trim(),
                role: ensureRole(node.role),
                location: String(node.location || 'Unknown').trim() || 'Unknown',
                discovered_source: String(node.discovered_source || '').trim(),
                confidence_score: Number(node.confidence_score ?? 0.75),
            }))
            .filter((node) => node.company_name.length > 0);

        if (cleanedNodes.length === 0) {
            toast.error('Add at least one supplier before confirming');
            return;
        }

        setConfirming(true);
        try {
            const res = await confirmProductSupplyChain(discovery.product_id, {
                nodes: cleanedNodes,
                edges: [],
            });
            setDiscovery(res.data);
            toast.success('Supply chain finalized');
            navigate(`/product/${res.data.product_id}`);
        } catch (err) {
            const msg = err.response?.data?.detail || 'Failed to finalize supply chain';
            toast.error(msg);
        } finally {
            setConfirming(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 animate-fade-in">
            {step < 6 ? (
                // WIZARD VIEW
                <div className="card-glass p-8 md:p-12 mb-6">
                    <div className="flex items-center gap-3 mb-8">
                        <PackageSearch className="w-8 h-8 text-primary-600" />
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Map Your Supply Chain</h1>
                            <p className="text-sm text-gray-500 font-medium">Step {step} of 5</p>
                        </div>
                    </div>

                    <div className="h-2 w-full bg-gray-100 rounded-full mb-10 overflow-hidden">
                        <div 
                            className="h-full bg-primary-600 transition-all duration-500 ease-out"
                            style={{ width: `${(step / 5) * 100}%` }}
                        />
                    </div>

                    <div className="min-h-[200px] flex flex-col justify-center">
                        {step === 1 && (
                            <div className="animate-fade-in">
                                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-6">What main raw material do you purchase for production?</h2>
                                <input
                                    className="input-field text-lg py-4 px-6"
                                    placeholder="e.g., MS Billets, Raw Aluminium, Iron Ore"
                                    value={answers.rawMaterial}
                                    onChange={(e) => handleAnswerChange('rawMaterial', e.target.value)}
                                    autoFocus
                                />
                            </div>
                        )}

                        {step === 2 && (
                            <div className="animate-fade-in">
                                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-6">Who is your primary supplier for this material?</h2>
                                <input
                                    className="input-field text-lg py-4 px-6"
                                    placeholder="e.g., Tata Steel, Hindalco, Harpreet Steel"
                                    value={answers.supplierName}
                                    onChange={(e) => handleAnswerChange('supplierName', e.target.value)}
                                    autoFocus
                                />
                                <p className="text-sm text-gray-500 mt-3 flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4 text-primary-500" />
                                    GreenGate instantly verifies top Indian suppliers.
                                </p>
                            </div>
                        )}

                        {step === 3 && (
                            <div className="animate-fade-in">
                                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-6">In which state is your factory located?</h2>
                                <input
                                    className="input-field text-lg py-4 px-6"
                                    placeholder="e.g., Punjab, Odisha, Maharashtra"
                                    value={answers.locationGrid}
                                    onChange={(e) => handleAnswerChange('locationGrid', e.target.value)}
                                    autoFocus
                                />
                            </div>
                        )}

                        {step === 4 && (
                            <div className="animate-fade-in">
                                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-6">What fuel runs your main furnaces or machinery?</h2>
                                <input
                                    className="input-field text-lg py-4 px-6"
                                    placeholder="e.g., Grid Electricity, Coal, Diesel Generator"
                                    value={answers.fuelMachinery}
                                    onChange={(e) => handleAnswerChange('fuelMachinery', e.target.value)}
                                    autoFocus
                                />
                            </div>
                        )}

                        {step === 5 && (
                            <div className="animate-fade-in">
                                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-6">What is your rough monthly production volume (in tonnes)?</h2>
                                <input
                                    className="input-field text-lg py-4 px-6"
                                    placeholder="e.g., 40"
                                    type="number"
                                    value={answers.productionVolume}
                                    onChange={(e) => handleAnswerChange('productionVolume', e.target.value)}
                                    autoFocus
                                />
                            </div>
                        )}
                    </div>

                    <div className="mt-12 flex justify-between items-center">
                        <button
                            onClick={prevStep}
                            disabled={step === 1 || loading}
                            className={`flex items-center gap-2 px-6 py-3 font-semibold rounded-xl transition-colors ${
                                step === 1 ? 'opacity-0 pointer-events-none' : 'text-gray-600 hover:bg-gray-100'
                            }`}
                        >
                            <ArrowLeft className="w-5 h-5" /> Back
                        </button>

                        {step < 5 ? (
                            <button
                                onClick={nextStep}
                                disabled={!isStepValid()}
                                className="btn-primary group flex items-center gap-2 px-8 py-3 text-lg"
                            >
                                Continue <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                            </button>
                        ) : (
                            <button
                                onClick={runDiscovery}
                                disabled={!isStepValid() || loading}
                                className="btn-primary flex items-center gap-2 px-8 py-3 text-lg"
                            >
                                {loading ? 'Mapping...' : 'Generate Compliance Graph'}
                            </button>
                        )}
                    </div>

                    {loading && (
                        <div className="mt-6 rounded-2xl border border-primary-200 bg-primary-50/50 p-6 animate-fade-in">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
                                <p className="font-semibold text-gray-900">Building supply chain structure...</p>
                            </div>
                            <div className="space-y-2 mt-4 ml-8">
                                {PIPELINE_STEPS.map((stepName, index) => (
                                    <p key={stepName} className={`text-sm transition-opacity duration-300 ${index === loadingStep ? 'text-primary-700 font-bold opacity-100' : 'text-gray-500 opacity-50'}`}>
                                        {index === loadingStep ? '▶' : '·'} {stepName}
                                    </p>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                // RESULTS VIEW
                <div className="max-w-7xl mx-auto animate-fade-in">
                    <div className="mb-8">
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">Your Supply Chain map</h1>
                        <p className="text-gray-500 text-lg">This map is locked from AI-discovered supplier intelligence.</p>
                    </div>

                    <div className="card-glass p-6 mb-8">
                        {graphNodes.length > 0 ? (
                            <div className="rounded-2xl overflow-hidden bg-slate-50/50" style={{ height: 400 }}>
                                <ReactFlow
                                    nodes={graphNodes}
                                    edges={graphEdges}
                                    fitView
                                    nodesDraggable={false}
                                    nodesConnectable={false}
                                    elementsSelectable={false}
                                >
                                    <Background gap={24} size={2} color="#cbd5e1" />
                                </ReactFlow>
                            </div>
                        ) : (
                            <div className="h-[400px] flex items-center justify-center bg-slate-50/50 rounded-2xl">
                                <p className="text-gray-500">No nodes discovered.</p>
                            </div>
                        )}
                    </div>

                    <div className="card-glass p-6 md:p-8">
                        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-between items-center bg-primary-50 rounded-2xl p-6">
                            <div className="text-primary-900">
                                <p className="font-bold">Ready to calculate emissions?</p>
                                <p className="text-sm text-primary-700 mt-1">Supplier details are auto-locked to prevent manual tampering and model drift.</p>
                            </div>
                            <button 
                                onClick={confirmSupplyChain} 
                                disabled={confirming} 
                                className="btn-primary px-8 py-3 text-lg shadow-lg w-full sm:w-auto"
                            >
                                {confirming ? 'Saving Map...' : 'Proceed to Calculation'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
