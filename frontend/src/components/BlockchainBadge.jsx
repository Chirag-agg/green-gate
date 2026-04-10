/**
 * BlockchainBadge — Displays blockchain certification status.
 */

import { ShieldCheck, ShieldX, ExternalLink, Copy, Check } from 'lucide-react';
import { useState } from 'react';

export default function BlockchainBadge({ certified, txHash, blockNumber, polygonscanUrl, reportHash, verifiedAt, hashVerified = true }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!certified) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-50 border border-gray-200">
        <ShieldX className="w-5 h-5 text-gray-400" />
        <span className="text-sm text-gray-500 font-medium">Not yet certified on blockchain</span>
      </div>
    );
  }

  return (
    <div className="card p-5 bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center shadow-lg shadow-green-500/30">
          <ShieldCheck className="w-5 h-5 text-white" />
        </div>
        <h4 className="text-lg font-bold text-green-800">✓ Blockchain Certified</h4>
      </div>

      <div className="space-y-3">
        {txHash && (
          <div className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-surface-200">
            <div>
              <p className="text-xs text-gray-500 font-medium">Transaction Hash</p>
              <p className="text-xs font-mono text-gray-700 truncate max-w-[250px]">{txHash}</p>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => handleCopy(txHash)}
                className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                title="Copy TX Hash"
              >
                {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-gray-400" />}
              </button>
            </div>
          </div>
        )}

        {blockNumber && (
          <div className="bg-white rounded-lg px-3 py-2 border border-surface-200">
            <p className="text-xs text-gray-500 font-medium">Block Number</p>
            <p className="text-sm font-semibold text-gray-700">{blockNumber.toLocaleString()}</p>
          </div>
        )}

        {reportHash && (
          <div className="bg-white rounded-lg px-3 py-2 border border-surface-200">
            <p className="text-xs text-gray-500 font-medium">Report Hash</p>
            <p className="text-xs font-mono text-gray-700 truncate">{reportHash}</p>
            <p className={`text-xs mt-1 font-semibold ${hashVerified ? 'text-green-700' : 'text-red-600'}`}>
              {hashVerified ? 'Integrity verified' : 'Report integrity compromised'}
            </p>
          </div>
        )}

        {verifiedAt && (
          <div className="bg-white rounded-lg px-3 py-2 border border-surface-200">
            <p className="text-xs text-gray-500 font-medium">Verification Timestamp</p>
            <p className="text-xs text-gray-700">{new Date(verifiedAt).toLocaleString()}</p>
          </div>
        )}

        <div className="flex gap-2 mt-4">
          {polygonscanUrl && (
            <a
              href={polygonscanUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-xs !py-2 !px-4 gap-1"
            >
              <ExternalLink className="w-3 h-3" /> View on Polygonscan
            </a>
          )}
          <button
            onClick={() => handleCopy(`${window.location.origin}/verify?hash=${reportHash}`)}
            className="btn-primary text-xs !py-2 !px-4"
          >
            Share Verification Link
          </button>
        </div>
      </div>
    </div>
  );
}
