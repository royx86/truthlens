import React from 'react';
import { Info, AlertCircle } from 'lucide-react';

export function ContextNotice({ context }) {
  if (!context) return null;

  const { isSatire, flags = [], limitations } = context;

  // If no contextual flags or limitations exist, don't show
  if (!isSatire && flags.length === 0 && !limitations) return null;

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 text-xs text-slate-600 space-y-2">
      <div className="flex items-center gap-2 font-bold text-slate-800">
        <Info className="w-4 h-4 text-violet-600 shrink-0" />
        <span>Context & Limitations</span>
      </div>

      {isSatire && (
        <p className="leading-relaxed">
          <span className="font-semibold text-slate-700">Satire context detected:</span>{' '}
          This post exhibits markers of parody or satire. This context is provided to clarify editorial intent, but does not by itself establish whether individual factual claims are true or false.
        </p>
      )}

      {limitations && (
        <p className="leading-relaxed">
          <span className="font-semibold text-slate-700">Analysis boundary:</span> {limitations}
        </p>
      )}

      {flags.length > 0 && !isSatire && (
        <div className="flex items-center gap-1.5 flex-wrap pt-1">
          <span className="text-slate-500 font-medium">Context tags:</span>
          {flags.map((flag) => (
            <span
              key={flag}
              className="px-2 py-0.5 rounded bg-white border border-slate-200 text-[11px] font-mono text-slate-600"
            >
              {flag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
