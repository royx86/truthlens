import React from 'react';
import { AlertTriangle, RefreshCw, ArrowLeft, ShieldAlert } from 'lucide-react';

export function AnalysisError({ error, onRetry, onReset }) {
  const errorMessage =
    error?.message ||
    (typeof error === 'string' ? error : 'TruthLens was unable to complete the analysis for this link.');

  const errorStatus = error?.status;
  const platform = error?.data?.platform;

  return (
    <div className="max-w-lg mx-auto py-12 px-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-rose-50 border border-rose-200 text-rose-600 flex items-center justify-center mx-auto mb-5 shadow-sm">
        <ShieldAlert className="w-8 h-8 stroke-[2]" />
      </div>

      <span className="text-[11px] font-bold text-rose-600 uppercase tracking-widest">
        Analysis Interrupted
      </span>
      <h2 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
        Something went wrong
      </h2>
      <p className="mt-2 text-sm text-slate-600 leading-relaxed">
        TruthLens couldn't complete this analysis.
      </p>

      {/* Safe error message card */}
      <div className="mt-6 bg-white rounded-xl border border-rose-100 p-4 shadow-sm text-left">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-semibold text-slate-800">
              {errorStatus ? `Error (${errorStatus})` : 'Analysis Notice'}
            </p>
            <p className="text-slate-600 leading-relaxed">{errorMessage}</p>
            {platform && (
              <p className="text-[11px] text-slate-400 font-mono">Platform: {platform}</p>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Try again</span>
          </button>
        )}
        <button
          type="button"
          onClick={onReset}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Analyze another post</span>
        </button>
      </div>
    </div>
  );
}
