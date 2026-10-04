import React, { useState } from 'react';
import { Sparkles, ArrowRight, ShieldCheck, CheckCircle2, AlertCircle, PlayCircle } from 'lucide-react';

export function AnalyzeInput({ onSubmit, isLoading, onTryDemo }) {
  const [url, setUrl] = useState('');
  const [validationError, setValidationError] = useState('');

  const EXAMPLE_URL = 'https://www.instagram.com/p/C-exampleAIphoto/';

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = url.trim();

    if (!trimmed) {
      setValidationError('Please enter a valid public post URL.');
      return;
    }

    try {
      const parsed = new URL(trimmed.startsWith('http') ? trimmed : `https://${trimmed}`);
      if (!parsed.hostname || !parsed.hostname.includes('.')) {
        throw new Error('Invalid host');
      }
    } catch {
      setValidationError('Please enter a valid public post URL (e.g., https://www.instagram.com/p/...)');
      return;
    }

    setValidationError('');
    onSubmit(trimmed);
  };

  const handleFillExample = (exampleLink) => {
    setUrl(exampleLink);
    setValidationError('');
  };

  return (
    <div className="space-y-12">
      {/* Hero Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
        {/* Left: Headline & Input Card */}
        <div className="lg:col-span-7 space-y-6">
          {/* Eyebrow */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-violet-50 border border-violet-200 text-violet-700 text-xs font-semibold tracking-wider uppercase">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-POWERED VERIFICATION</span>
          </div>

          {/* Heading */}
          <div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-[1.15]">
              See what's really{' '}
              <span className="gradient-text">behind the post.</span>
            </h1>
            <p className="mt-4 text-base sm:text-lg text-slate-600 leading-relaxed max-w-xl">
              Analyze public social media posts and get claim-by-claim context backed by external evidence from verified journalistic archives.
            </p>
          </div>

          {/* Main Input Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm hover:shadow-md hover:shadow-violet-100/60 transition-shadow">
            <form onSubmit={handleSubmit} noValidate>
              <label
                htmlFor="social-post-url-input"
                className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2"
              >
                Paste a public post URL
              </label>

              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="relative flex-1">
                  <input
                    id="social-post-url-input"
                    type="url"
                    value={url}
                    onChange={(e) => {
                      setUrl(e.target.value);
                      if (validationError) setValidationError('');
                    }}
                    placeholder="Instagram, Facebook, Reddit, X, Threads or YouTube URL"
                    disabled={isLoading}
                    className={`w-full px-4 py-3 text-sm rounded-xl border transition-all placeholder:text-slate-400 focus:outline-none focus:ring-2 ${
                      validationError
                        ? 'border-rose-400 focus:ring-rose-300 bg-rose-50/20'
                        : 'border-slate-300 focus:border-violet-600 focus:ring-violet-100'
                    }`}
                  />
                </div>

                <button
                  type="submit"
                  id="analyze-post-button"
                  disabled={isLoading}
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-700 hover:from-violet-700 hover:to-indigo-800 active:from-violet-800 text-white font-semibold text-sm transition-all shadow-sm hover:shadow-md shadow-violet-600/20 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer shrink-0"
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Analyzing...</span>
                    </>
                  ) : (
                    <>
                      <span>Analyze Post</span>
                      <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                    </>
                  )}
                </button>
              </div>

              {/* Inline Validation Error */}
              {validationError && (
                <div className="mt-2.5 flex items-center gap-1.5 text-xs font-medium text-rose-600 animate-in fade-in duration-150">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{validationError}</span>
                </div>
              )}

              {/* Platform Support Info & Example */}
              <div className="mt-4 pt-4 border-t border-slate-100 space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                  <p className="font-medium text-slate-600">
                    Currently supports public posts from supported platforms:
                  </p>
                  <button
                    type="button"
                    onClick={onTryDemo}
                    disabled={isLoading}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-violet-600 hover:text-violet-800 transition-colors cursor-pointer"
                  >
                    <PlayCircle className="w-3.5 h-3.5" />
                    <span>Try Demo Post</span>
                  </button>
                </div>

                {/* Platform Badges */}
                <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    Instagram (Active)
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    Facebook (Active)
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 border border-slate-200">
                    X / Twitter (Coming soon)
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 border border-slate-200">
                    Reddit (Coming soon)
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 border border-slate-200">
                    Threads (Coming soon)
                  </span>
                </div>

                {/* Example Link */}
                <div className="text-xs text-slate-500 flex items-center gap-1.5 flex-wrap">
                  <span>Example:</span>
                  <button
                    type="button"
                    onClick={() => handleFillExample(EXAMPLE_URL)}
                    className="text-violet-600 hover:underline font-mono text-[11px] truncate max-w-xs text-left"
                    title="Click to fill example URL"
                  >
                    {EXAMPLE_URL}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        {/* Right: Live Preview Mock Card */}
        <div className="lg:col-span-5">
          <div className="bg-white rounded-2xl border border-violet-100/80 p-5 shadow-sm shadow-violet-100/50 space-y-4 relative overflow-hidden">
            {/* subtle gradient top-right corner */}
            <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full bg-gradient-to-br from-violet-100 to-indigo-100 opacity-60 blur-2xl pointer-events-none" />

            <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-slate-100">
              <span className="font-semibold text-slate-700 uppercase tracking-wider text-[11px]">
                Analysis preview
              </span>
              <span className="font-mono text-[11px] text-slate-400">instagram.com/p/C-example</span>
            </div>

            {/* Verdict Sample */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Likely accurate</span>
                </span>
                <span className="text-xs font-medium text-slate-500">92% confidence</span>
              </div>
              <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                <div className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full w-[92%]" />
              </div>
            </div>

            {/* Mini Grid */}
            <div className="grid grid-cols-3 gap-2 py-2 border-t border-b border-slate-100 text-center">
              <div>
                <p className="text-[10px] uppercase font-semibold text-slate-400">Credibility</p>
                <p className="text-xs font-bold text-slate-800 mt-0.5">High</p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-semibold text-slate-400">Claims</p>
                <p className="text-xs font-bold text-slate-800 mt-0.5">3 analyzed</p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-semibold text-slate-400">Last checked</p>
                <p className="text-xs font-bold text-slate-800 mt-0.5">Just now</p>
              </div>
            </div>

            {/* Sample claim snippet */}
            <div className="bg-violet-50/50 rounded-xl p-3 border border-violet-100 text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 text-[11px]">Claim 1</span>
                <span className="text-[10px] font-bold text-emerald-600 uppercase">Supported</span>
              </div>
              <p className="text-slate-600 italic text-[11px] line-clamp-2">
                "AI vision models accurately reproduce photorealistic micro-textures in 2026..."
              </p>
            </div>

            <div className="text-[11px] text-slate-400 flex items-center justify-center gap-1.5 pt-1">
              <ShieldCheck className="w-3.5 h-3.5 text-violet-600" />
              <span>Evidence cross-referenced across 4 trusted archives</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
