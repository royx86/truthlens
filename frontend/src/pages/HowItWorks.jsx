import React from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { Link } from 'react-router-dom';
import { Share2, FileSearch, Sparkles, Database, CheckSquare, Award, ArrowRight, ShieldCheck } from 'lucide-react';

const DETAILED_STEPS = [
  {
    num: '01',
    title: 'Submit a Public Post',
    desc: 'You submit a public social media link (such as an Instagram reel, photo, or post). TruthLens identifies the origin host and prepares a scoped retrieval pipeline.',
    icon: Share2,
  },
  {
    num: '02',
    title: 'Retrieve Available Content',
    desc: 'The system accesses public post captions, author metadata, and high-resolution media streams without modifying or transforming original source assets.',
    icon: FileSearch,
  },
  {
    num: '03',
    title: 'Extract Atomic Claims',
    desc: 'Language models break post captions, overlaid image text, and spoken audio into atomic, verifiable factual assertions, isolating claims from pure opinion or emotion.',
    icon: Sparkles,
  },
  {
    num: '04',
    title: 'Search External Sources',
    desc: 'Independent search providers query authoritative journalistic archives, verified public fact-checking organizations, and primary documentation databases.',
    icon: Database,
  },
  {
    num: '05',
    title: 'Compare & Rank Evidence',
    desc: 'Evidence is categorized by relevance, directness, and source credibility. Independent corroboration is strictly distinguished from self-referential social claims.',
    icon: CheckSquare,
  },
  {
    num: '06',
    title: 'Generate an Evidence-Backed Report',
    desc: 'TruthLens synthesizes the findings into an accessible, claim-by-claim breakdown with direct source links, confidence indicators, and contextual disclaimers.',
    icon: Award,
  },
];

export function HowItWorks() {
  return (
    <PageContainer>
      <div className="max-w-4xl mx-auto space-y-12">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-violet-50 border border-violet-200 text-violet-700 text-xs font-semibold uppercase tracking-wider">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>VERIFICATION METHODOLOGY</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            How TruthLens Works
          </h1>
          <p className="text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            TruthLens helps organize evidence and context around claims. Rather than making unilateral declarations of truth, our system connects assertions with independent corroboration.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {DETAILED_STEPS.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.num}
                className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center font-bold text-sm">
                    <Icon className="w-5 h-5 stroke-[2]" />
                  </div>
                  <span className="text-xs font-mono font-bold text-slate-400">
                    Step {step.num}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900">
                  {step.title}
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
                  {step.desc}
                </p>
              </div>
            );
          })}
        </div>

        {/* Philosophy Note */}
        <div className="bg-violet-50/70 border border-violet-100 rounded-2xl p-6 sm:p-8 text-center space-y-3">
          <h2 className="text-lg font-bold text-slate-900">
            Transparent, Open-Ended Evidence
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 max-w-2xl mx-auto leading-relaxed">
            No automated system can detect truth with 100% certainty. TruthLens provides readers with direct, unedited source citations and confidence metrics to empower critical thinking and informed evaluation.
          </p>
          <div className="pt-2">
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              <span>Analyze a post now</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
