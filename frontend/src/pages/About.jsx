import React from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { ShieldCheck, CheckCircle2, Layers, Search, Eye } from 'lucide-react';
import { Link } from 'react-router-dom';

export function About() {
  return (
    <PageContainer>
      <div className="max-w-3xl mx-auto space-y-10">
        {/* Brand Hero */}
        <div className="text-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-violet-600 text-white flex items-center justify-center mx-auto shadow-md shadow-violet-500/20">
            <ShieldCheck className="w-8 h-8 stroke-[2.2]" />
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            About TruthLens
          </h1>
          <p className="text-base text-violet-600 font-semibold">
            AI-powered social media verification and evidence analysis.
          </p>
        </div>

        {/* Narrative Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-4 text-sm text-slate-700 leading-relaxed font-normal">
          <p>
            In modern social media ecosystems, assertions, altered media, and decontextualized snippets circulate at unprecedented velocity. Discerning factual reporting from misattribution often demands hours of manual cross-referencing.
          </p>
          <p>
            <strong className="text-slate-900">TruthLens</strong> was designed to bridge this gap. Rather than acting as an infallible arbiter of truth, TruthLens functions as an automated research assistant that decomposes viral posts into their core verifiable assertions, retrieves corresponding records from reputable global news archives, and structures that evidence clearly for the reader.
          </p>
          <p>
            Every claim is linked directly to primary reporting, ensuring that users can inspect sources themselves and reach independent conclusions with context.
          </p>
        </div>

        {/* Pillars */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
            <div className="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center">
              <Search className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-slate-900">Evidence First</h2>
            <p className="text-xs text-slate-500 leading-relaxed font-normal">
              Claims are evaluated strictly against retrieved journalistic citations and peer-reviewed records.
            </p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Eye className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-slate-900">Transparent AI</h2>
            <p className="text-xs text-slate-500 leading-relaxed font-normal">
              Every stage of ingestion, multimodal vision analysis, and reasoning is documented without hidden score manipulation.
            </p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2">
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-slate-900">Context Aware</h2>
            <p className="text-xs text-slate-500 leading-relaxed font-normal">
              Identifies satire, parody, and uncertainty, distinguishing intentional comedy from deceptive falsehoods.
            </p>
          </div>
        </div>

        {/* Call to action */}
        <div className="text-center pt-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold shadow-sm transition-colors"
          >
            <span>Start an analysis</span>
          </Link>
        </div>
      </div>
    </PageContainer>
  );
}
