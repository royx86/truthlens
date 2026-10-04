import React from 'react';
import { AlertTriangle, CheckCircle2, XCircle, HelpCircle, ShieldAlert } from 'lucide-react';
import { cn } from '../../lib/utils';

export function VerdictCard({ overall }) {
  const verdict = overall?.verdict || {
    label: 'Not analyzed',
    badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
    barColor: '#94a3b8',
    progressPct: 0,
  };

  const rawKey = overall?.rawVerdict || '';
  const progressPct = verdict.progressPct ?? 50;
  const barColor = verdict.barColor || '#3b82f6';

  // Select suitable icon
  const renderIcon = () => {
    switch (rawKey) {
      case 'SUPPORTED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />;
      case 'REFUTED':
        return <XCircle className="w-4 h-4 text-rose-600 shrink-0" />;
      case 'PARTIALLY_SUPPORTED':
      case 'MISLEADING':
        return <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />;
      case 'INSUFFICIENT_EVIDENCE':
        return <ShieldAlert className="w-4 h-4 text-slate-500 shrink-0" />;
      default:
        return <HelpCircle className="w-4 h-4 text-violet-600 shrink-0" />;
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-sm space-y-6">
      {/* Top Header Row */}
      <div className="space-y-3">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
          Analyzed post
        </span>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Verdict Badge */}
          <div
            className={cn(
              'inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs sm:text-sm font-semibold tracking-wide self-start',
              verdict.badgeClass
            )}
          >
            {renderIcon()}
            <span>{verdict.label}</span>
          </div>

          {/* Confidence Score */}
          <span className="text-xs sm:text-sm font-medium text-slate-700">
            {overall?.confidence || 'Confidence: Not available'}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden mt-2">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${Math.max(progressPct, 8)}%`,
              backgroundColor: barColor,
            }}
          />
        </div>
      </div>

      {/* Metadata 3-column Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100">
        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Source credibility
          </p>
          <p className="text-sm font-bold text-slate-800 mt-1">
            {overall?.sourceCredibility || 'Not available'}
          </p>
        </div>

        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Claims detected
          </p>
          <p className="text-sm font-bold text-slate-800 mt-1">
            {overall?.claimsDetected ?? 0}
          </p>
        </div>

        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Last checked
          </p>
          <p className="text-sm font-bold text-slate-800 mt-1">
            {overall?.lastChecked || 'Just now'}
          </p>
        </div>
      </div>
    </div>
  );
}
