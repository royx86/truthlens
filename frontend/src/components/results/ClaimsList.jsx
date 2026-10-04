import React from 'react';
import { ClaimCard } from './ClaimCard';
import { EmptyState } from '../common/EmptyState';
import { FileQuestion } from 'lucide-react';

export function ClaimsList({ claims = [] }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900 tracking-tight">
          Detected claims
        </h2>
        <span className="text-xs font-semibold text-slate-500">
          {claims.length} {claims.length === 1 ? 'claim' : 'claims'} evaluated
        </span>
      </div>

      {claims.length === 0 ? (
        <EmptyState
          icon={FileQuestion}
          title="No distinct claims identified"
          description="The analysis pipeline did not identify verifiable factual claims in this post."
        />
      ) : (
        <div className="space-y-4">
          {claims.map((claim) => (
            <ClaimCard key={claim.id} claim={claim} />
          ))}
        </div>
      )}
    </div>
  );
}
