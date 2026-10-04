import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white mt-auto py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left */}
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <ShieldCheck className="w-4 h-4 text-violet-600" />
          <span className="font-semibold text-slate-700">TruthLens</span>
          <span>© 2026</span>
          <span>•</span>
          <span>AI-Assisted Evidence Verification Platform</span>
        </div>

        {/* Right */}
        <div className="flex items-center gap-6 text-xs text-slate-500">
          <Link to="/about" className="hover:text-slate-800 transition-colors">
            About
          </Link>
          <Link to="/how-it-works" className="hover:text-slate-800 transition-colors">
            Methodology
          </Link>
          <span className="hover:text-slate-800 transition-colors cursor-pointer">
            Privacy
          </span>
          <span className="hover:text-slate-800 transition-colors cursor-pointer">
            Terms
          </span>
          <span className="hover:text-slate-800 transition-colors cursor-pointer">
            Contact
          </span>
        </div>
      </div>
    </footer>
  );
}
