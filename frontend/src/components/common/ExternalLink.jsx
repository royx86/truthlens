import React from 'react';
import { ExternalLink as ExternalLinkIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

export function ExternalLink({
  href,
  children,
  className = '',
  showIcon = true,
  iconSize = 13,
  'aria-label': ariaLabel,
}) {
  if (!href) return <span className={className}>{children}</span>;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={ariaLabel || (typeof children === 'string' ? `${children} (opens in new tab)` : 'Opens external link in new tab')}
      className={cn(
        'inline-flex items-center gap-1 text-violet-600 hover:text-violet-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 rounded-sm',
        className
      )}
    >
      <span>{children}</span>
      {showIcon && <ExternalLinkIcon size={iconSize} className="shrink-0 stroke-[2.2]" aria-hidden="true" />}
    </a>
  );
}
