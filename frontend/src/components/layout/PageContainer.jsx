import React from 'react';
import { Navbar } from './Navbar';
import { Footer } from './Footer';
import { cn } from '../../lib/utils';

export function PageContainer({ children, className = '', onClearHistoryNotification }) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <Navbar onClearHistoryNotification={onClearHistoryNotification} />
      <main className={cn('flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10', className)}>
        {children}
      </main>
      <Footer />
    </div>
  );
}
