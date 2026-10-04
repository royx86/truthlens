import React, { useState, useEffect, useRef } from 'react';
import { ShieldCheck, CheckCircle2, Loader2, Clock, Zap } from 'lucide-react';

const STAGES = [
  {
    id: 1,
    label: 'Detecting platform',
    desc: 'Validating host and post schema',
    emoji: '🔍',
    approxSec: 2,
  },
  {
    id: 2,
    label: 'Retrieving post',
    desc: 'Fetching public caption and media metadata',
    emoji: '📥',
    approxSec: 4,
  },
  {
    id: 3,
    label: 'Analyzing media',
    desc: 'Running vision models on images and video frames',
    emoji: '🖼️',
    approxSec: 8,
  },
  {
    id: 4,
    label: 'Extracting claims',
    desc: 'Isolating verifiable factual assertions from the post',
    emoji: '✂️',
    approxSec: 5,
  },
  {
    id: 5,
    label: 'Searching for evidence',
    desc: 'Querying journalistic archives and fact-check databases',
    emoji: '🗄️',
    approxSec: 5,
  },
  {
    id: 6,
    label: 'Building report',
    desc: 'Synthesizing evidence-backed confidence scores and context',
    emoji: '📋',
    approxSec: 9,
  },
];

const TOTAL_APPROX_SEC = STAGES.reduce((s, st) => s + st.approxSec, 0);

// Fun facts/tips that cycle to keep user engaged
const TIPS = [
  'AI cross-references claims against thousands of journalistic archives.',
  'Misinformation often travels 6x faster than corrections on social media.',
  'Our evidence engine queries live fact-check databases in real time.',
  'Media analysis detects digitally altered images using vision models.',
  'Each claim is scored independently before an overall verdict is formed.',
  'Context matters — satire, parody and opinion are handled separately.',
];

export function AnalysisLoading({ targetUrl }) {
  const [activeStage, setActiveStage] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [tipIndex, setTipIndex] = useState(0);
  const stageRef = useRef(0);

  // Tick elapsed seconds
  useEffect(() => {
    const tick = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    return () => clearInterval(tick);
  }, []);

  // Rotate tips every 6 seconds
  useEffect(() => {
    const rotate = setInterval(() => {
      setTipIndex((i) => (i + 1) % TIPS.length);
    }, 6000);
    return () => clearInterval(rotate);
  }, []);

  // Progress through stages using each stage's own timing
  useEffect(() => {
    let current = 0;

    const advance = () => {
      current += 1;
      if (current < STAGES.length) {
        stageRef.current = current;
        setActiveStage(current);
        // Schedule next advance based on this stage's duration
        setTimeout(advance, (STAGES[current]?.approxSec || 5) * 1000);
      }
    };

    // Start first stage immediately, advance after its duration
    const firstTimer = setTimeout(advance, STAGES[0].approxSec * 1000);
    return () => clearTimeout(firstTimer);
  }, []);

  // Visual progress percentage (driven by elapsed time vs total estimate)
  const visualPct = Math.min(Math.round((elapsedSec / TOTAL_APPROX_SEC) * 100), 92);

  const formatTime = (sec) => {
    if (sec < 60) return `${sec}s`;
    return `${Math.floor(sec / 60)}m ${sec % 60}s`;
  };

  return (
    <div className="max-w-2xl mx-auto py-12 px-4">
      {/* ── Top section: orb + title ── */}
      <div className="flex flex-col items-center text-center mb-10">
        {/* Animated orb */}
        <div className="relative flex items-center justify-center mb-6 select-none">
          {/* Outer glow ring */}
          <div className="absolute w-28 h-28 rounded-full bg-gradient-to-br from-violet-200 to-indigo-200 opacity-50 animate-pulse-subtle blur-xl" />
          {/* Mid ring */}
          <div className="absolute w-24 h-24 rounded-full border-2 border-dashed border-violet-300/60 animate-spin-slow" />
          {/* Core icon */}
          <div className="relative w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-700 flex items-center justify-center text-white shadow-lg shadow-violet-500/30 animate-float">
            <ShieldCheck className="w-10 h-10 stroke-[2]" />
          </div>
          {/* Orbiting dot */}
          <div className="absolute w-3 h-3 rounded-full bg-amber-400 shadow-sm orbit-dot" />
        </div>

        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Analyzing this post…
        </h2>
        <p className="mt-1.5 text-sm text-slate-500 max-w-md font-mono text-[12px] truncate px-4">
          {targetUrl || 'Examining submitted post…'}
        </p>

        {/* Elapsed + estimate */}
        <div className="mt-4 flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 bg-slate-100 rounded-full px-3 py-1">
            <Clock className="w-3.5 h-3.5 text-violet-500" />
            Elapsed: <strong className="text-slate-700">{formatTime(elapsedSec)}</strong>
          </span>
          <span className="text-xs text-slate-400">·</span>
          <span className="text-xs text-slate-500 bg-amber-50 border border-amber-200 rounded-full px-3 py-1 font-medium text-amber-700">
            ⏳ Usually 20–40 seconds
          </span>
        </div>
      </div>

      {/* ── Progress bar ── */}
      <div className="mb-8">
        <div className="flex justify-between text-[11px] text-slate-400 font-medium mb-1.5">
          <span className="uppercase tracking-wider">Overall progress</span>
          <span>{visualPct}%</span>
        </div>
        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000 ease-out shimmer-bg"
            style={{ width: `${visualPct}%` }}
          />
        </div>
      </div>

      {/* ── Pipeline stages ── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between text-xs text-slate-400 font-semibold uppercase tracking-wider px-5 py-3 border-b border-slate-100 bg-slate-50/60">
          <span className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-violet-500" />
            Verification pipeline
          </span>
          <span>
            Stage {Math.min(activeStage + 1, STAGES.length)} / {STAGES.length}
          </span>
        </div>

        <div className="divide-y divide-slate-50">
          {STAGES.map((stage, idx) => {
            const isCompleted = idx < activeStage;
            const isCurrent = idx === activeStage;
            const isPending = idx > activeStage;

            return (
              <div
                key={stage.id}
                className={`flex items-start gap-3.5 px-5 py-3.5 transition-all duration-300 ${isCurrent
                  ? 'bg-violet-50/70'
                  : isCompleted
                    ? 'bg-white'
                    : 'bg-white opacity-40'
                  }`}
              >
                {/* Status icon */}
                <div className="mt-0.5 shrink-0 w-5 flex items-center justify-center">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4.5 h-4.5 text-emerald-500 stroke-[2.5]" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-violet-600 animate-spin stroke-[2.5]" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-slate-200" />
                  )}
                </div>

                {/* Emoji */}
                <span className="text-base leading-none mt-0.5 shrink-0">{stage.emoji}</span>

                {/* Text */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p
                      className={`text-xs font-bold leading-snug ${isCurrent ? 'text-violet-900' : isCompleted ? 'text-slate-700' : 'text-slate-400'
                        }`}
                    >
                      {stage.label}
                    </p>
                    {isCurrent && (
                      <span className="text-[10px] font-bold text-violet-600 uppercase tracking-wide animate-pulse shrink-0">
                        In progress
                      </span>
                    )}
                    {isCompleted && (
                      <span className="text-[10px] font-semibold text-emerald-600 shrink-0">Done ✓</span>
                    )}
                  </div>
                  <p
                    className={`text-[11px] mt-0.5 leading-relaxed ${isCurrent ? 'text-violet-700' : 'text-slate-400'
                      }`}
                  >
                    {stage.desc}
                  </p>
                </div>

                {/* Approx time badge for pending stages */}
                {isPending && (
                  <span className="text-[10px] text-slate-300 shrink-0 mt-0.5">~{stage.approxSec}s</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Rotating tip ── */}
      <div className="mt-6 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 flex items-start gap-2.5">
        <span className="text-base leading-none mt-0.5">💡</span>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600 mb-0.5">Did you know?</p>
          <p
            key={tipIndex}
            className="text-xs text-amber-800 leading-relaxed animate-in fade-in duration-500"
          >
            {TIPS[tipIndex]}
          </p>
        </div>
      </div>

      <p className="mt-5 text-xs text-center text-slate-400">
        Hang tight — we're consulting multiple sources to give you accurate results.
      </p>
    </div>
  );
}
