import React from 'react';
import { Share2, FileSearch, Sparkles, Database, CheckSquare, Award } from 'lucide-react';

const PIPELINE_STEPS = [
  {
    step: 'Step 01',
    title: 'Post Ingestion',
    desc: 'Extract caption, images & metadata',
    icon: Share2,
  },
  {
    step: 'Step 02',
    title: 'Content Analysis',
    desc: 'Vision models inspect visual texture & text',
    icon: FileSearch,
  },
  {
    step: 'Step 03',
    title: 'Claim Extraction',
    desc: 'Isolate verifiable factual assertions',
    icon: Sparkles,
  },
  {
    step: 'Step 04',
    title: 'Evidence Search',
    desc: 'Query verified news archives & databases',
    icon: Database,
  },
  {
    step: 'Step 05',
    title: 'Cross-Reference',
    desc: 'Compare claims against trusted sources',
    icon: CheckSquare,
  },
  {
    step: 'Step 06',
    title: 'Verdict',
    desc: 'Assign confidence & output explanation',
    icon: Award,
  },
];

export function PipelineSection() {
  return (
    <section className="mt-16 bg-gradient-to-br from-violet-950 via-indigo-950 to-violet-900 text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-violet-800/50">
      <div className="text-center max-w-2xl mx-auto mb-8">
        <span className="text-[11px] font-bold uppercase tracking-widest text-violet-400">
          TRANSPARENT AI PIPELINE
        </span>
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white mt-1">
          How TruthLens investigates social media posts
        </h2>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {PIPELINE_STEPS.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.step}
              className="bg-violet-900/40 hover:bg-violet-800/60 border border-violet-700/40 rounded-xl p-4 flex flex-col items-center text-center transition-all hover:border-violet-500/60 group"
            >
              <div className="w-10 h-10 rounded-xl bg-violet-800/60 text-violet-300 flex items-center justify-center mb-3 group-hover:scale-105 group-hover:bg-violet-600 group-hover:text-white transition-all">
                <Icon className="w-5 h-5 stroke-[1.8]" />
              </div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                {item.step}
              </span>
              <h3 className="text-xs font-bold text-slate-100 mb-1.5 leading-snug">
                {item.title}
              </h3>
              <p className="text-[11px] text-slate-400 leading-normal">
                {item.desc}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
