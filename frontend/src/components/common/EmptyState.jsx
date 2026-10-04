import React from 'react';
import { HelpCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

export function EmptyState({
  icon: Icon = HelpCircle,
  title = 'No information available',
  description = null,
  className = '',
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-8 px-4 text-center text-slate-500 rounded-lg bg-slate-50/60 border border-dashed border-slate-200',
        className
      )}
    >
      <Icon className="w-8 h-8 text-slate-400 mb-2 stroke-[1.5]" aria-hidden="true" />
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {description && <p className="text-xs text-slate-500 mt-1 max-w-sm">{description}</p>}
    </div>
  );
}
