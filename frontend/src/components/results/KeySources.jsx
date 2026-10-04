import React from 'react';
import { ExternalLink, Globe, BookOpen } from 'lucide-react';
import { EmptyState } from '../common/EmptyState';

export function KeySources({ sources = [] }) {
  if (!sources || sources.length === 0) {
    return (
      <div className="space-y-4 pt-4">
        <h2 className="text-lg font-bold text-slate-900 tracking-tight">
          Key Evidence Sources
        </h2>
        <EmptyState
          icon={Globe}
          title="No external sources available"
          description="External source links were not found or not returned for this post."
        />
      </div>
    );
  }

  // Helper to format quality tag
  const getQualityBadge = (sourceQuality) => {
    switch (sourceQuality?.toLowerCase()) {
      case 'high':
        return (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-violet-50 text-violet-700 border border-violet-200">
            HIGH CREDIBILITY
          </span>
        );
      case 'trusted':
        return (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-violet-50 text-violet-700 border border-violet-200">
            TRUSTED CREDIBILITY
          </span>
        );
      case 'medium':
        return (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
            STANDARD SOURCE
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
            EXTERNAL SOURCE
          </span>
        );
    }
  };

  return (
    <div className="space-y-4 pt-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900 tracking-tight">
          Key Evidence Sources
        </h2>
        <span className="text-xs font-semibold text-slate-500">
          {sources.length} {sources.length === 1 ? 'source' : 'sources'} cited
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((item, idx) => (
          <div
            key={item.url || idx}
            className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between space-y-3"
          >
            <div className="space-y-2">
              {/* Domain & Credibility Tag */}
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-bold text-slate-800 font-mono">
                  {item.sourceName || 'external source'}
                </span>
                {getQualityBadge(item.sourceQuality)}
              </div>

              {/* Title */}
              <h3 className="text-sm font-bold text-slate-900 leading-snug line-clamp-2">
                {item.title}
              </h3>

              {/* Snippet */}
              {item.snippet && (
                <p className="text-xs text-slate-600 italic leading-relaxed line-clamp-3">
                  "{item.snippet}"
                </p>
              )}
            </div>

            {/* External Link */}
            {item.url && (
              <div className="pt-2 border-t border-slate-100">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-600 hover:text-violet-800 transition-colors"
                >
                  <span>View Source</span>
                  <ExternalLink className="w-3.5 h-3.5 stroke-[2.2]" />
                </a>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
