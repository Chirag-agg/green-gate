/**
 * Home page — Hero section, features, stats for GreenGate.
 */

import { Link } from 'react-router-dom';
import { ArrowRight, Cpu, ShieldCheck, FileCheck2, Globe, CheckCircle2 } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen selection:bg-primary-100">
      {/* Spacer to account for the new floating navbar */}
      <div className="h-28" />

      {/* Hero Section */}
      <section className="relative overflow-hidden mb-16">
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-surface-50 to-transparent" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <div className="text-center max-w-5xl mx-auto rounded-3xl border border-surface-200 bg-white p-8 sm:p-14 shadow-md">
            <div className="inline-flex items-center gap-2 bg-primary-50 border border-primary-200 rounded-full px-5 py-2 mb-8 animate-fade-in shadow-sm">
              <span className="text-sm font-bold text-primary-800 tracking-wide uppercase">Built for Exporters, Not Engineers</span>
            </div>

            <h1 className="text-5xl sm:text-7xl font-extrabold text-surface-900 leading-[1.1] mb-8 animate-slide-up tracking-tight">
              A Clear Path to{' '}
              <span className="text-primary-700">CBAM Compliance</span>
              <br className="hidden sm:block" /> for Everyone.
            </h1>

            <p className="text-xl sm:text-2xl text-surface-600 max-w-3xl mx-auto mb-12 leading-relaxed animate-slide-up font-medium" style={{ animationDelay: '100ms' }}>
              Exporting to the EU is hard. Don't let confusing carbon taxes stop you.
              GreenGate makes it simple to report and verify your data.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-6 animate-slide-up" style={{ animationDelay: '200ms' }}>
              <Link to="/register" className="btn-primary text-xl !px-10 !py-6 gap-3 group w-full sm:w-auto">
                <ShieldCheck className="w-7 h-7" />
                Start My Application
                <ArrowRight className="w-6 h-6 group-hover:translate-x-2 transition-transform" />
              </Link>
              <Link to="/verify" className="btn-secondary text-xl !px-10 !py-6 gap-3 w-full sm:w-auto">
                <FileCheck2 className="w-7 h-7" />
                Verify Document
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section - Replacing stats with highly visual cards for accessibility */}
      <section className="py-24 relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-extrabold text-surface-900 mb-6">
            How GreenGate Helps You
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
          {/* Feature 1 */}
          <div className="card p-10 group hover:-translate-y-1 transition-transform duration-300">
            <div className="w-20 h-20 rounded-2xl bg-surface-100 flex items-center justify-center mb-8 border border-surface-200 group-hover:bg-primary-50 transition-colors">
              <Cpu className="w-10 h-10 text-primary-700" />
            </div>
            <h3 className="text-2xl font-bold text-surface-900 mb-4 tracking-tight">Easy Calculations</h3>
            <p className="text-lg text-surface-600 leading-relaxed mb-6">
              Our automated system uses simple questions to figure out exactly how much carbon is in your process. No PhD required.
            </p>
            <ul className="space-y-3">
              <li className="flex items-center gap-3 text-surface-700 font-medium">
                <CheckCircle2 className="w-6 h-6 text-primary-600 flex-shrink-0" /> Fast process
              </li>
              <li className="flex items-center gap-3 text-surface-700 font-medium">
                <CheckCircle2 className="w-6 h-6 text-primary-600 flex-shrink-0" /> Smart recommendations
              </li>
            </ul>
          </div>

          {/* Feature 2 */}
          <div className="card p-10 group hover:-translate-y-1 transition-transform duration-300">
            <div className="w-20 h-20 rounded-2xl bg-surface-100 flex items-center justify-center mb-8 border border-surface-200 group-hover:bg-primary-50 transition-colors">
              <ShieldCheck className="w-10 h-10 text-primary-700" />
            </div>
            <h3 className="text-2xl font-bold text-surface-900 mb-4 tracking-tight">Trust & Proof</h3>
            <p className="text-lg text-surface-600 leading-relaxed mb-6">
              Your results are locked securely. European buyers can scan and verify your report instantly, building massive trust.
            </p>
            <ul className="space-y-3">
              <li className="flex items-center gap-3 text-surface-700 font-medium">
                <CheckCircle2 className="w-6 h-6 text-primary-600 flex-shrink-0" /> Unbreakable records
              </li>
              <li className="flex items-center gap-3 text-surface-700 font-medium">
                <CheckCircle2 className="w-6 h-6 text-primary-600 flex-shrink-0" /> High credibility
              </li>
            </ul>
          </div>

          {/* Feature 3 */}
          <div className="card p-10 group hover:-translate-y-1 transition-transform duration-300">
            <div className="w-20 h-20 rounded-2xl bg-surface-100 flex items-center justify-center mb-8 border border-surface-200 group-hover:bg-primary-50 transition-colors">
              <FileCheck2 className="w-10 h-10 text-primary-700" />
            </div>
            <h3 className="text-2xl font-bold text-surface-900 mb-4 tracking-tight">Ready Documents</h3>
            <p className="text-lg text-surface-600 leading-relaxed mb-6">
              We generate the exact forms needed by the EU. Just click print or download. We handle the complex math behind the scenes.
            </p>
            <ul className="space-y-3">
              <li className="flex items-center gap-3 text-surface-700 font-medium">
                <CheckCircle2 className="w-6 h-6 text-primary-600 flex-shrink-0" /> One-click downloads
              </li>
              <li className="flex items-center gap-3 text-surface-700 font-medium">
                <CheckCircle2 className="w-6 h-6 text-primary-600 flex-shrink-0" /> Correct format
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 mx-4 sm:mx-8 mb-12">
        <div className="max-w-6xl mx-auto rounded-3xl overflow-hidden relative shadow-xl border border-surface-300">
          <div className="absolute inset-0 bg-surface-900" />
          <div className="absolute inset-0 bg-[linear-gradient(115deg,rgba(102,109,60,0.16),rgba(47,42,36,0.3))]" />
          <div className="relative px-6 py-20 text-center flex flex-col items-center">
            <div className="w-16 h-16 bg-white/10 border border-white/20 rounded-2xl flex items-center justify-center mb-8">
              <Globe className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-4xl sm:text-5xl font-extrabold text-white mb-6 tracking-tight max-w-3xl">
              Keep Trading with Europe. Let Us Handle the Paperwork.
            </h2>
            <Link to="/register" className="btn-primary bg-white text-surface-900 hover:bg-surface-100 text-xl !px-12 !py-6 gap-3 group mt-4">
              Get Started Now
              <ArrowRight className="w-6 h-6 group-hover:translate-x-2 transition-transform text-primary-700" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-surface-100 py-12 border-t border-surface-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <p className="text-xl font-bold text-surface-900">GreenGate</p>
            <p className="text-base font-medium text-surface-500">
              © {new Date().getFullYear()} GreenGate Technologies
            </p>
            <div className="flex items-center gap-8 text-base font-semibold text-surface-600">
              <Link to="/verify" className="hover:text-primary-700 transition-colors">Verify Paperwork</Link>
              <a href="mailto:info@greengate.io" className="hover:text-primary-700 transition-colors">Help / Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
