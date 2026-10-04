import React from 'react';
import { cn } from '../../lib/utils';

export function StatusBadge({ children, className, variant = 'neutral', size = 'md' }) {
  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1 font-medium',
    lg: 'text-sm px-3 py-1 font-medium',
  };

  const variantStyles = {
    neutral: 'bg-slate-100 text-slate-700 border-slate-200',
    supported: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    misleading: 'bg-amber-50 text-amber-700 border-amber-200',
    refuted: 'bg-rose-50 text-rose-700 border-rose-200',
    unverified: 'bg-violet-50 text-violet-700 border-violet-200',
    primary: 'bg-violet-600 text-white border-transparent',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border tracking-wide uppercase',
        sizeStyles[size] || sizeStyles.md,
        variantStyles[variant] || variantStyles.neutral,
        className
      )}
    >
      {children}
    </span>
  );
}
