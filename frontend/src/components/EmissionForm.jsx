/**
 * EmissionForm — Multi-step data input form for carbon calculation.
 */

import { useEffect, useState } from 'react';
import { Building2, Zap, ClipboardCheck, ChevronRight, ChevronLeft, Loader2, CheckCircle2, Circle, Calculator } from 'lucide-react';
import toast from 'react-hot-toast';
import { runCompanyIntelligence } from '../utils/api';

const SECTORS = [
  { value: 'steel_bfbof', label: 'Steel (BF-BOF — Blast Furnace)' },
  { value: 'steel_eaf', label: 'Steel (EAF — Electric Arc Furnace)' },
  { value: 'cement', label: 'Cement' },
  { value: 'aluminium_primary', label: 'Aluminium (Primary)' },
  { value: 'aluminium_secondary', label: 'Aluminium (Secondary)' },
  { value: 'fertilizer_urea', label: 'Fertilizer (Urea)' },
  { value: 'hydrogen_grey', label: 'Hydrogen (Grey)' },
  { value: 'hydrogen_blue', label: 'Hydrogen (Blue)' },
  { value: 'hydrogen_green', label: 'Hydrogen (Green)' },
];

const STATES = [
  'Maharashtra', 'Gujarat', 'Punjab', 'Rajasthan', 'Odisha',
  'Tamil Nadu', 'Karnataka', 'West Bengal', 'Uttar Pradesh', 'Haryana',
  'Andhra Pradesh', 'Bihar', 'Chhattisgarh', 'Delhi', 'Goa',
  'Jharkhand', 'Kerala', 'Madhya Pradesh', 'Telangana', 'Assam',
];

const STEPS = [
  { title: 'Company Details', icon: Building2, desc: 'Your business context' },
  { title: 'Verification', icon: ClipboardCheck, desc: 'Confirm facility data' },
  { title: 'Energy Numbers', icon: Zap, desc: 'Monthly consumption' },
  { title: 'Review', icon: ClipboardCheck, desc: 'Final check' },
];

const MACHINERY_OPTIONS = [
  { value: 'blast_furnace', label: 'Blast Furnace' },
  { value: 'electric_arc_furnace', label: 'Electric Arc Furnace' },
  { value: 'rotary_kiln', label: 'Rotary Kiln' },
  { value: 'smelter', label: 'Smelter' },
];

const MACHINERY_PROFILES = {
  electric_arc_furnace: { min_kwh_per_ton: 350, max_kwh_per_ton: 450 },
  blast_furnace: { min_kwh_per_ton: 500, max_kwh_per_ton: 700 },
  rotary_kiln: { min_kwh_per_ton: 90, max_kwh_per_ton: 140 },
  smelter: { min_kwh_per_ton: 1200, max_kwh_per_ton: 1700 },
};

const SECTOR_DEFAULTS = {
  steel_eaf: { machinery: 'electric_arc_furnace', product_type: 'steel' },
  steel_bfbof: { machinery: 'blast_furnace', product_type: 'steel' },
  cement: { machinery: 'rotary_kiln', product_type: 'cement' },
  aluminium_primary: { machinery: 'smelter', product_type: 'aluminum' },
  aluminium_secondary: { machinery: 'smelter', product_type: 'aluminum' },
  fertilizer_urea: { machinery: 'rotary_kiln', product_type: 'fertilizer' },
  hydrogen_grey: { machinery: 'smelter', product_type: 'hydrogen' },
  hydrogen_blue: { machinery: 'smelter', product_type: 'hydrogen' },
  hydrogen_green: { machinery: 'smelter', product_type: 'hydrogen' },
};

const INTELLIGENCE_STEPS = [
  'Searching public records...',
  'Analyzing corporate structures...',
  'Detecting heavy facilities...',
  'Synthesizing data...',
];

const initialFormData = {
  company_name: '',
  sector: 'steel_bfbof',
  machinery: 'blast_furnace',
  product_type: 'steel',
  state: 'Maharashtra',
  annual_production_tonnes: '',
  eu_export_tonnes: '',
  eu_importer_name: '',
  factory_location: '',
  estimated_production: '',
  export_markets: [],
  likely_machinery: [],
  primary_furnace_type: '',
  machine_manufacturer: '',
  machine_model: '',
  year_installed: '',
  energy_efficiency_rating: '',
  electricity_kwh_per_month: '',
  solar_kwh_per_month: '0',
  coal_kg_per_month: '',
  natural_gas_m3_per_month: '0',
  diesel_litres_per_month: '',
  lpg_litres_per_month: '0',
  furnace_oil_litres_per_month: '0',
  biomass_kg_per_month: '0',
};

export default function EmissionForm({ onSubmit, loading }) {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState(initialFormData);
  const [intelligenceLoading, setIntelligenceLoading] = useState(false);
  const [intelligenceStep, setIntelligenceStep] = useState(0);
  const [detectedProfile, setDetectedProfile] = useState(null);

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const updateSector = (sector) => {
    const defaults = SECTOR_DEFAULTS[sector] || { machinery: 'electric_arc_furnace', product_type: 'steel' };
    setFormData((prev) => ({
      ...prev,
      sector,
      machinery: defaults.machinery,
      product_type: defaults.product_type,
      primary_furnace_type: defaults.machinery,
    }));
  };

  const production = parseFloat(formData.annual_production_tonnes) || 0;
  const profile = MACHINERY_PROFILES[formData.machinery] || null;
  const expectedMin = profile ? production * profile.min_kwh_per_ton : 0;
  const expectedMax = profile ? production * profile.max_kwh_per_ton : 0;
  const expectedMidpoint = expectedMin > 0 && expectedMax > 0 ? (expectedMin + expectedMax) / 2 : 0;
  const inputEnergyAnnual = (parseFloat(formData.electricity_kwh_per_month) || 0) * 12;
  const outOfRange = expectedMax > 0 && (inputEnergyAnnual < expectedMin || inputEnergyAnnual > expectedMax);
  const deviation = expectedMidpoint > 0 ? inputEnergyAnnual / expectedMidpoint : 1;

  let credibilityStatus = 'High';
  let credibilityBadgeClass = 'bg-green-100 text-green-800 border-green-200';
  if (deviation < 0.5 || deviation > 1.5) {
    credibilityStatus = 'Low';
    credibilityBadgeClass = 'bg-red-100 text-red-800 border-red-200';
  } else if ((deviation >= 0.5 && deviation < 0.8) || (deviation > 1.2 && deviation <= 1.5)) {
    credibilityStatus = 'Moderate';
    credibilityBadgeClass = 'bg-amber-100 text-amber-800 border-amber-200';
  }

  const canAdvance = () => {
    if (step === 0) {
      return formData.company_name && formData.sector && formData.state && formData.annual_production_tonnes && formData.eu_export_tonnes;
    }
    if (step === 1) {
      return formData.primary_furnace_type && formData.machine_manufacturer && formData.machine_model && formData.year_installed && formData.energy_efficiency_rating;
    }
    if (step === 2) {
      return formData.electricity_kwh_per_month;
    }
    return true;
  };

  useEffect(() => {
    if (!intelligenceLoading) return undefined;
    const timer = setInterval(() => {
      setIntelligenceStep((prev) => (prev + 1) % INTELLIGENCE_STEPS.length);
    }, 900);
    return () => clearInterval(timer);
  }, [intelligenceLoading]);

  const handleNext = async () => {
    if (step === 0) {
      setIntelligenceLoading(true);
      setIntelligenceStep(0);

      try {
        const res = await runCompanyIntelligence({
          company_name: formData.company_name,
          state: formData.state,
          sector: formData.sector,
        });

        const profileData = res.data?.discovered_company_profile || {};
        const suggestedMachinery = Array.isArray(res.data?.suggested_machinery)
          ? res.data.suggested_machinery
          : [];
        const machinerySuggestion = suggestedMachinery[0] || formData.machinery;

        setDetectedProfile(profileData);
        setFormData((prev) => ({
          ...prev,
          factory_location: profileData.factory_location || prev.state,
          estimated_production: profileData.estimated_production || res.data?.suggested_production_range || prev.estimated_production,
          export_markets: Array.isArray(profileData.export_markets) ? profileData.export_markets : prev.export_markets,
          likely_machinery: Array.isArray(profileData.likely_machinery) ? profileData.likely_machinery : suggestedMachinery,
          machinery: machinerySuggestion,
          primary_furnace_type: machinerySuggestion,
        }));
      } catch (err) {
        toast.error('Automated verification lookup failed. Proceeding manually.');
        setDetectedProfile({
          company_name: formData.company_name,
          factory_location: formData.state,
          estimated_production: 'Unknown',
          export_markets: [],
          likely_machinery: [formData.machinery],
        });
      } finally {
        setIntelligenceLoading(false);
        setStep(1);
      }
      return;
    }

    if (step < 3) {
      setStep((prev) => prev + 1);
    }
  };

  const handleSubmit = () => {
    const payload = {
      ...formData,
      annual_production_tonnes: parseFloat(formData.annual_production_tonnes) || 0,
      eu_export_tonnes: parseFloat(formData.eu_export_tonnes) || 0,
      export_markets: Array.isArray(formData.export_markets) ? formData.export_markets : [],
      likely_machinery: Array.isArray(formData.likely_machinery) ? formData.likely_machinery : [],
      year_installed: parseInt(formData.year_installed, 10) || null,
      electricity_kwh_per_month: parseFloat(formData.electricity_kwh_per_month) || 0,
      solar_kwh_per_month: parseFloat(formData.solar_kwh_per_month) || 0,
      coal_kg_per_month: parseFloat(formData.coal_kg_per_month) || 0,
      natural_gas_m3_per_month: parseFloat(formData.natural_gas_m3_per_month) || 0,
      diesel_litres_per_month: parseFloat(formData.diesel_litres_per_month) || 0,
      lpg_litres_per_month: parseFloat(formData.lpg_litres_per_month) || 0,
      furnace_oil_litres_per_month: parseFloat(formData.furnace_oil_litres_per_month) || 0,
      biomass_kg_per_month: parseFloat(formData.biomass_kg_per_month) || 0,
    };
    onSubmit(payload);
  };

  return (
    <div className="max-w-4xl mx-auto w-full">
      {/* Loading Overlay State for Intelligence */}
      {intelligenceLoading && (
        <div className="card-glass p-10 animate-fade-in mb-8 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-12 h-12 text-primary-600 animate-spin mb-6" />
          <h3 className="text-2xl font-bold text-surface-900 mb-6 tracking-tight">Accessing Corporate Records...</h3>
          <div className="space-y-4 max-w-sm w-full mx-auto text-left">
            {INTELLIGENCE_STEPS.map((item, index) => (
              <div key={item} className={`flex items-center gap-3 text-lg transition-all duration-300 ${index === intelligenceStep ? 'text-primary-700 font-bold scale-105' : 'text-surface-400 font-medium'}`}>
                {index === intelligenceStep ? <CheckCircle2 className="w-6 h-6 text-primary-600" /> : <Circle className="w-5 h-5 opacity-50" />}
                {item}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Progress Steps */}
      <div className="mb-12 overflow-x-auto pb-4 custom-scrollbar">
        <div className="flex items-center justify-between min-w-[600px] px-2">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center flex-1 last:flex-none">
              <div className={`flex flex-col sm:flex-row items-center gap-4 ${i <= step ? 'text-primary-800' : 'text-surface-400'}`}>
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-xl font-extrabold transition-all duration-300 ${i < step ? 'bg-primary-700 text-white shadow-lg shadow-primary-700/30' : i === step ? 'bg-white text-primary-700 border-4 border-primary-600 shadow-md' : 'bg-surface-200 text-surface-400'
                  }`}>
                  {i < step ? <CheckCircle2 className="w-8 h-8" /> : <s.icon className="w-7 h-7" />}
                </div>
                <div className="text-center sm:text-left">
                  <p className="text-lg font-bold tracking-tight">{s.title}</p>
                  <p className="hidden sm:block text-sm font-medium opacity-80">{s.desc}</p>
                </div>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`h-1.5 flex-1 mx-6 rounded-full transition-colors ${i < step ? 'bg-primary-600' : 'bg-surface-200'}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="card-glass p-8 sm:p-12 animate-fade-in shadow-2xl">
        {step === 0 && (
          <div className="space-y-8">
            <div>
              <h3 className="text-3xl font-extrabold text-surface-900 mb-2 tracking-tight">About Your Company</h3>
              <p className="text-lg text-surface-600 font-medium">Please verify the primary details of the exporting entity.</p>
            </div>
            
            <div className="space-y-6">
              <div>
                <label className="block text-lg font-bold text-surface-800 mb-2">Company Name *</label>
                <input className="input-field text-lg !py-5 shadow-inner" placeholder="e.g., Apex Manufacturing Ltd." value={formData.company_name} onChange={(e) => updateField('company_name', e.target.value)} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-bold text-surface-800 mb-2">Primary Sector *</label>
                  <select className="input-field text-lg !py-5 shadow-inner cursor-pointer" value={formData.sector} onChange={(e) => updateSector(e.target.value)}>
                    {SECTORS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-lg font-bold text-surface-800 mb-2">Factory State *</label>
                  <select className="input-field text-lg !py-5 shadow-inner cursor-pointer" value={formData.state} onChange={(e) => updateField('state', e.target.value)}>
                    {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-bold text-surface-800 mb-2">Total Production (Tonnes/Year) *</label>
                  <input className="input-field text-lg !py-5 shadow-inner" type="number" placeholder="100000" value={formData.annual_production_tonnes} onChange={(e) => updateField('annual_production_tonnes', e.target.value)} />
                </div>
                <div>
                  <label className="block text-lg font-bold text-surface-800 mb-2">EU Export Target (Tonnes/Year) *</label>
                  <input className="input-field text-lg !py-5 shadow-inner" type="number" placeholder="50000" value={formData.eu_export_tonnes} onChange={(e) => updateField('eu_export_tonnes', e.target.value)} />
                </div>
              </div>
              <div>
                <label className="block text-lg font-bold text-surface-800 mb-2">EU Importer Name (Optional)</label>
                <input className="input-field text-lg !py-5 shadow-inner" placeholder="e.g., EuroSteel GmbH" value={formData.eu_importer_name} onChange={(e) => updateField('eu_importer_name', e.target.value)} />
              </div>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-8">
            <div>
              <h3 className="text-3xl font-extrabold text-surface-900 mb-2 tracking-tight">Verification Data</h3>
              <p className="text-lg text-surface-600 font-medium">Review the detected hardware profile. EU auditors will verify this.</p>
            </div>

            <div className="rounded-2xl border-2 border-primary-200 bg-primary-50 p-6 shadow-sm">
              <h4 className="text-xl font-bold text-primary-900 mb-4 border-b border-primary-200 pb-2">Automated Discovery Profile</h4>
              <div className="space-y-3">
                <p className="text-lg text-surface-800"><span className="font-extrabold text-primary-800 w-48 inline-block">Registered Name:</span> {detectedProfile?.company_name || formData.company_name}</p>
                <p className="text-lg text-surface-800"><span className="font-extrabold text-primary-800 w-48 inline-block">Registered Location:</span> {detectedProfile?.factory_location || formData.state}</p>
                <p className="text-lg text-surface-800"><span className="font-extrabold text-primary-800 w-48 inline-block">Estimated Output:</span> {detectedProfile?.estimated_production || 'Data unavailable'}</p>
                <p className="text-lg text-surface-800"><span className="font-extrabold text-primary-800 w-48 inline-block">Key Markets:</span> {(detectedProfile?.export_markets || []).join(', ') || 'Data unavailable'}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
              <div>
                <label className="block text-lg font-bold text-surface-800 mb-2">Correction: Location</label>
                <input className="input-field text-lg !py-5 shadow-inner" value={formData.factory_location} onChange={(e) => updateField('factory_location', e.target.value)} />
              </div>
              <div>
                <label className="block text-lg font-bold text-surface-800 mb-2">Correction: Output Estimate</label>
                <input className="input-field text-lg !py-5 shadow-inner" value={formData.estimated_production} onChange={(e) => updateField('estimated_production', e.target.value)} placeholder="e.g., 40k–60k tons annually" />
              </div>
            </div>

            <div className="mt-8 border-t border-surface-200 pt-8">
              <h4 className="text-2xl font-extrabold text-surface-900 mb-6 tracking-tight">Machinery & Hardware Specifications</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-lg font-bold text-surface-800 mb-2">Primary Heavy Machine *</label>
                  <select className="input-field text-lg !py-5 shadow-inner cursor-pointer" value={formData.primary_furnace_type} onChange={(e) => updateField('primary_furnace_type', e.target.value)}>
                    <option value="">Select machinery type</option>
                    {MACHINERY_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-lg font-bold text-surface-800 mb-2">Machine Manufacturer *</label>
                  <input className="input-field text-lg !py-5 shadow-inner" value={formData.machine_manufacturer} onChange={(e) => updateField('machine_manufacturer', e.target.value)} placeholder="e.g. SMS Group" />
                </div>
                <div>
                  <label className="block text-lg font-bold text-surface-800 mb-2">Hardware Model *</label>
                  <input className="input-field text-lg !py-5 shadow-inner" value={formData.machine_model} onChange={(e) => updateField('machine_model', e.target.value)} placeholder="e.g. Arc-1200X" />
                </div>
                <div>
                  <label className="block text-lg font-bold text-surface-800 mb-2">Year Installed *</label>
                  <input className="input-field text-lg !py-5 shadow-inner" type="number" value={formData.year_installed} onChange={(e) => updateField('year_installed', e.target.value)} placeholder="e.g. 2018" />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-lg font-bold text-surface-800 mb-2">Hardware Efficiency Rating *</label>
                  <input className="input-field text-lg !py-5 shadow-inner" value={formData.energy_efficiency_rating} onChange={(e) => updateField('energy_efficiency_rating', e.target.value)} placeholder="e.g. Tier 1 / Class A" />
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-8">
            <div>
              <h3 className="text-3xl font-extrabold text-surface-900 mb-2 tracking-tight">Energy Consumption Data</h3>
              <p className="text-lg text-surface-600 font-medium pb-4 border-b border-surface-200">Provide accurate monthly averages. Enter 0 if a source is unused.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="md:col-span-2 bg-primary-50 rounded-2xl p-6 border border-primary-200">
                <label className="block text-xl font-extrabold text-primary-900 mb-3">National Grid Electricity (kWh/month) *</label>
                <input className="input-field text-2xl font-bold !py-6 shadow-inner border-primary-300 focus:border-primary-600 focus:ring-primary-600/30 text-surface-900" type="number" placeholder="450000" value={formData.electricity_kwh_per_month} onChange={(e) => updateField('electricity_kwh_per_month', e.target.value)} />
                {profile && production > 0 && (
                  <div className="mt-4 flex flex-col gap-2">
                    <p className="text-base font-bold text-primary-800 flex items-center gap-2">
                      <Zap className="w-5 h-5" />
                      Expected baseline for your output: {expectedMin.toLocaleString()} – {expectedMax.toLocaleString()} kWh
                    </p>
                    {outOfRange && <p className="text-base font-bold text-red-700 bg-red-100 px-4 py-2 rounded-lg inline-block self-start border border-red-200">
                      Warning: Value far outside industry limits. May trigger audit.
                    </p>}
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-lg font-bold text-surface-800 mb-2">Solar / Renewable (kWh/month)</label>
                <input className="input-field text-lg !py-5 shadow-inner" type="number" placeholder="0" value={formData.solar_kwh_per_month} onChange={(e) => updateField('solar_kwh_per_month', e.target.value)} />
              </div>
              <div>
                <label className="block text-lg font-bold text-surface-800 mb-2">Raw Coal (kg/month)</label>
                <input className="input-field text-lg !py-5 shadow-inner" type="number" placeholder="0" value={formData.coal_kg_per_month} onChange={(e) => updateField('coal_kg_per_month', e.target.value)} />
              </div>
              <div>
                <label className="block text-lg font-bold text-surface-800 mb-2">Natural Gas (m³/month)</label>
                <input className="input-field text-lg !py-5 shadow-inner" type="number" placeholder="0" value={formData.natural_gas_m3_per_month} onChange={(e) => updateField('natural_gas_m3_per_month', e.target.value)} />
              </div>
              <div>
                <label className="block text-lg font-bold text-surface-800 mb-2">Diesel Fuel (litres/month)</label>
                <input className="input-field text-lg !py-5 shadow-inner" type="number" placeholder="0" value={formData.diesel_litres_per_month} onChange={(e) => updateField('diesel_litres_per_month', e.target.value)} />
              </div>
            </div>

            {profile && production > 0 && (
              <div className="mt-8 rounded-2xl border-2 border-surface-200 bg-surface-50 p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <p className="text-xl font-extrabold text-surface-900 mb-1">Data Credibility Standard</p>
                  <p className="text-sm font-medium text-surface-600">Based on hardware and output ratios</p>
                </div>
                <span className={`px-6 py-3 rounded-xl border-2 text-base font-bold uppercase tracking-wider ${credibilityBadgeClass}`}>
                  {credibilityStatus} Confidence
                </span>
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-8">
            <div className="text-center mb-8">
              <h3 className="text-4xl font-extrabold text-surface-900 mb-3 tracking-tight">Final Document Review</h3>
              <p className="text-xl text-surface-600 font-medium max-w-lg mx-auto">Please confirm your final numbers. This report forms the basis of your EU declarations.</p>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-white border-2 border-surface-200 rounded-3xl p-8 shadow-sm">
                <h4 className="text-2xl font-extrabold text-surface-900 mb-6 border-b border-surface-100 pb-4">Business Identity</h4>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-bold text-surface-400 uppercase tracking-widest">Entity Name</p>
                    <p className="text-xl font-bold text-surface-900">{formData.company_name}</p>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-surface-400 uppercase tracking-widest">Scope & Location</p>
                    <p className="text-lg font-medium text-surface-700">{SECTORS.find((s) => s.value === formData.sector)?.label} • <span className="text-primary-700">{formData.state}</span></p>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-surface-400 uppercase tracking-widest">Volume Data</p>
                    <p className="text-lg font-medium text-surface-700">{parseInt(formData.annual_production_tonnes || 0).toLocaleString()} tonnes/yr total</p>
                    <p className="text-lg font-medium text-surface-700 bg-amber-50 inline-block px-3 py-1 rounded-lg mt-1 border border-amber-200">{parseInt(formData.eu_export_tonnes || 0).toLocaleString()} tonnes to EU</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white border-2 border-surface-200 rounded-3xl p-8 shadow-sm">
                <h4 className="text-2xl font-extrabold text-surface-900 mb-6 border-b border-surface-100 pb-4">Consumption & Hardware</h4>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-bold text-surface-400 uppercase tracking-widest">Core Electricity Input</p>
                    <p className="text-2xl font-extrabold text-primary-700">{parseInt(formData.electricity_kwh_per_month || 0).toLocaleString()} kWh <span className="text-base font-medium text-surface-500">monthly average</span></p>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-surface-400 uppercase tracking-widest">Heavy Hardware Target</p>
                    <p className="text-lg font-medium text-surface-800">{formData.primary_furnace_type || 'Unknown Type'}</p>
                    <p className="text-base font-medium text-surface-500">{formData.machine_manufacturer || 'Unknown Make'} • {formData.year_installed || 'Unknown Year'}</p>
                  </div>
                  <div className="pt-2">
                    <span className={`px-4 py-2 border-2 text-sm font-bold rounded-xl inline-block ${credibilityBadgeClass}`}>
                      System Check: {credibilityStatus} Reliability
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 mt-12 pt-8 border-t-2 border-surface-100">
          {step > 0 ? (
            <button onClick={() => setStep(step - 1)} className="btn-secondary text-lg !px-8 !py-4 gap-2 w-full sm:w-auto text-center justify-center">
              <ChevronLeft className="w-5 h-5" /> Go Back
            </button>
          ) : <div className="hidden sm:block" />}

          {step < 3 ? (
            <button onClick={handleNext} disabled={!canAdvance() || intelligenceLoading} className="btn-primary text-lg !px-10 !py-4 gap-3 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary-700/20 w-full sm:w-auto text-center justify-center">
              {step === 1 ? 'Approve & Continue' : 'Continue'} <ChevronRight className="w-6 h-6" />
            </button>
          ) : (
            <button onClick={handleSubmit} disabled={loading} className="btn-primary text-xl !px-12 !py-5 gap-4 shadow-xl shadow-primary-700/30 w-full sm:w-auto text-center justify-center">
              {loading ? (
                <>
                  <Loader2 className="w-6 h-6 animate-spin" />
                  Generating Compliance Document...
                </>
              ) : (
                <>
                   <Calculator className="w-6 h-6" />
                  Calculate & Verify Report
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
