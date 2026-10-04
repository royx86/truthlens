import React from 'react';

export function EvidenceSummary({ summary }) {
  const text = summary || 'No overall summary was provided.';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-2.5">
      <h2 className="text-base font-bold text-slate-900">
        Evidence-backed summary
      </h2>
      <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-normal">
        {text}
      </p>
    </div>
  );
}
