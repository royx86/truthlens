import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { AnalysisHeader } from '../components/results/AnalysisHeader';
import { VerdictCard } from '../components/results/VerdictCard';
import { OriginalPostCard } from '../components/results/OriginalPostCard';
import { EvidenceSummary } from '../components/results/EvidenceSummary';
import { ClaimsList } from '../components/results/ClaimsList';
import { KeySources } from '../components/results/KeySources';
import { ContextNotice } from '../components/results/ContextNotice';
import { PipelineSection } from '../components/results/PipelineSection';
import { normalizeAnalysisResponse } from '../utils/analysis';
import { getHistory } from '../utils/history';
import { mockAnalysisData } from '../data/mockAnalysis';
import { Sparkles, ArrowLeft } from 'lucide-react';

export function Results() {
  const location = useLocation();
  const navigate = useNavigate();

  // Try retrieving data from router state
  let data = location.state?.normalizedData;

  // Fallback 1: check if rawResponse was passed in router state
  if (!data && location.state?.rawResponse) {
    data = normalizeAnalysisResponse(location.state.rawResponse);
  }

  // Fallback 2: check if there's a recent item in history with fullResponse
  if (!data) {
    const history = getHistory();
    if (history.length > 0 && history[0].fullResponse) {
      data = normalizeAnalysisResponse(history[0].fullResponse);
    }
  }

  // If still no data, show clean empty state prompting analysis
  if (!data) {
    return (
      <PageContainer>
        <div className="max-w-md mx-auto py-16 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-violet-50 text-violet-600 flex items-center justify-center mx-auto">
            <Sparkles className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">No active analysis found</h2>
          <p className="text-xs sm:text-sm text-slate-500">
            Submit a public post link from the home page or try our demo analysis report.
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Go to Home</span>
            </button>
            <button
              type="button"
              onClick={() => {
                const mockNormalized = normalizeAnalysisResponse(mockAnalysisData);
                navigate('/results', {
                  state: {
                    normalizedData: mockNormalized,
                    rawResponse: mockAnalysisData,
                  },
                });
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
            >
              <span>Load Demo Report</span>
            </button>
          </div>
        </div>
      </PageContainer>
    );
  }

  const { overall, source, author, content, context, claims, keySources } = data;

  const handleReset = () => {
    navigate('/');
  };

  return (
    <PageContainer>
      <div className="space-y-6">
        {/* Header: Eyebrow, Title, Subtitle, Analyze another button */}
        <AnalysisHeader onReset={handleReset} />

        {/* Large Summary Card: Overall Verdict, Confidence, 3 metrics */}
        <VerdictCard overall={overall} />

        {/* Two-Column Responsive Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Original Post Details (Desktop col-span-5) */}
          <div className="lg:col-span-5 space-y-6">
            <OriginalPostCard
              author={author}
              source={source}
              content={content}
              context={context}
            />
          </div>

          {/* Right Column: Summary, Claims, Key Sources, Context Notice (Desktop col-span-7) */}
          <div className="lg:col-span-7 space-y-6">
            <EvidenceSummary summary={overall?.overallSummary} />
            <ClaimsList claims={claims} />
            <KeySources sources={keySources} />
            <ContextNotice context={context} />
          </div>
        </div>

        {/* Transparent AI Pipeline Section */}
        <PipelineSection />
      </div>
    </PageContainer>
  );
}
