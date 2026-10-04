import React from 'react';
import { ExternalLink, CheckCircle2, AlertTriangle, XCircle, HelpCircle, ShieldAlert } from 'lucide-react';
import { cn } from '../../lib/utils';

export function ClaimCard({ claim }) {
  const {
    id,
    index,
    text,
    verdict,
    rawVerdict,
    confidence,
    explanation,
    supportingEvidence = [],
    contradictingEvidence = [],
    evidenceStatus,
    evidenceStatusMessage,
    sources = [],
    hasAnalysis,
  } = claim;

  // Primary source link to highlight
  const firstSupporting = supportingEvidence[0] || sources.find((s) => s.relationship === 'supports') || sources[0];
  const firstContradicting = contradictingEvidence[0] || sources.find((s) => s.relationship === 'contradicts');

  const primarySource = firstSupporting || firstContradicting;

  // Text excerpt for supporting evidence
  const evidenceExcerpt =
    firstSupporting?.snippet ||
    firstContradicting?.snippet ||
    explanation ||
    evidenceStatusMessage;

  // Custom verdict label for claim badge (e.g. REAL / MISLEADING / REFUTED / UNVERIFIED)
  const getBadgeLabel = () => {
    if (!rawVerdict) return 'NOT ANALYZED';
    switch (rawVerdict) {
      case 'SUPPORTED':
        return 'REAL';
      case 'MISLEADING':
        return 'MISLEADING';
      case 'PARTIALLY_SUPPORTED':
        return 'PARTIALLY SUPPORTED';
      case 'REFUTED':
        return 'REFUTED';
      case 'UNVERIFIED':
        return 'UNVERIFIED';
      case 'INSUFFICIENT_EVIDENCE':
        return 'INSUFFICIENT EVIDENCE';
      default:
        return verdict.label?.toUpperCase() || rawVerdict;
    }
  };

  const badgeClass = verdict?.badgeClass || 'bg-slate-100 text-slate-700 border-slate-200';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4 transition-shadow hover:shadow-md">
      {/* Top Header: Claim Index & Verdict Badge */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-slate-900">
            Claim {index}
          </span>
          {claim.importance && claim.importance !== 'medium' && (
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-500">
              {claim.importance} priority
            </span>
          )}
        </div>

        <span
          className={cn(
            'px-2.5 py-0.5 rounded-md text-[11px] font-bold tracking-wider uppercase border',
            badgeClass
          )}
        >
          {getBadgeLabel()}
        </span>
      </div>

      {/* Claim Quotation */}
      <blockquote className="text-sm sm:text-base font-semibold text-slate-800 leading-snug">
        "{text}"
      </blockquote>

      {/* Explanation / Supporting Evidence Excerpt */}
      {evidenceExcerpt ? (
        <div className="text-xs sm:text-sm text-slate-600 space-y-1.5 leading-relaxed pt-1">
          <p>
            <span className="font-semibold text-slate-800">
              {firstContradicting && !firstSupporting ? 'Contradicting evidence: ' : 'Supporting evidence: '}
            </span>
            {evidenceExcerpt}
          </p>
        </div>
      ) : evidenceStatusMessage ? (
        <p className="text-xs text-slate-500 italic bg-slate-50 p-2.5 rounded-lg border border-slate-100">
          {evidenceStatusMessage}
        </p>
      ) : null}

      {/* Specific Evidence Status Notices */}
      {evidenceStatusMessage && evidenceExcerpt && (
        <p className="text-[11px] text-slate-500 italic">
          Note: {evidenceStatusMessage}
        </p>
      )}

      {/* Source Links */}
      {primarySource?.url ? (
        <div className="pt-2 border-t border-slate-100">
          <a
            href={primarySource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-600 hover:text-violet-800 transition-colors"
          >
            <span>View supporting source</span>
            <ExternalLink className="w-3.5 h-3.5 stroke-[2.2]" />
          </a>
        </div>
      ) : (
        <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400">
          No external source link available for this claim.
        </div>
      )}
    </div>
  );
}
