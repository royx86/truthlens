import React from 'react';
import { ArrowLeft } from 'lucide-react';

export function AnalysisHeader({ onReset }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6">
      <div>
        <span className="text-xs font-bold uppercase tracking-wider text-violet-600 block mb-1">
          ANALYSIS RESULTS
        </span>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Here's what we found.
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Evidence-backed context for the public post you submitted.
        </p>
      </div>

      <button
        type="button"
        id="analyze-another-post-button"
        onClick={onReset}
        className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl border border-violet-300 text-violet-700 hover:bg-violet-50 font-semibold text-xs transition-colors shadow-sm self-start sm:self-auto cursor-pointer"
      >
        <ArrowLeft className="w-3.5 h-3.5 stroke-[2.5]" />
        <span>Analyze another post</span>
      </button>
    </div>
  );
}
