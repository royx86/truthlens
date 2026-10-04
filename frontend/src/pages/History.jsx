import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { getHistory, clearHistory } from '../utils/history';
import { normalizeAnalysisResponse } from '../utils/analysis';
import { History as HistoryIcon, Trash2, ArrowRight, ExternalLink, Calendar, CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';
import { EmptyState } from '../components/common/EmptyState';
import { cn } from '../lib/utils';

export function History() {
  const [historyItems, setHistoryItems] = useState([]);
  const navigate = useNavigate();

  const loadItems = () => {
    setHistoryItems(getHistory());
  };

  useEffect(() => {
    loadItems();
  }, []);

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear your local analysis history?')) {
      clearHistory();
      setHistoryItems([]);
    }
  };

  const handleOpenItem = (item) => {
    if (item.fullResponse) {
      const normalized = normalizeAnalysisResponse(item.fullResponse);
      navigate('/results', {
        state: {
          normalizedData: normalized,
          rawResponse: item.fullResponse,
        },
      });
    }
  };

  const formatDate = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Recent';
    }
  };

  const getVerdictIcon = (rawVerdict) => {
    switch (rawVerdict) {
      case 'SUPPORTED':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />;
      case 'REFUTED':
        return <XCircle className="w-3.5 h-3.5 text-rose-600" />;
      case 'PARTIALLY_SUPPORTED':
      case 'MISLEADING':
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />;
      default:
        return <HelpCircle className="w-3.5 h-3.5 text-violet-600" />;
    }
  };

  return (
    <PageContainer onClearHistoryNotification={loadItems}>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center">
                <HistoryIcon className="w-4 h-4" />
              </div>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                Analysis History
              </h1>
            </div>
            <p className="mt-1 text-xs sm:text-sm text-slate-500">
              Locally cached verifications performed on this device.
            </p>
          </div>

          {historyItems.length > 0 && (
            <button
              type="button"
              onClick={handleClearAll}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-rose-200 text-rose-600 hover:bg-rose-50 text-xs font-semibold transition-colors self-start sm:self-auto cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear history</span>
            </button>
          )}
        </div>

        {/* History List */}
        {historyItems.length === 0 ? (
          <EmptyState
            icon={HistoryIcon}
            title="No analysis history yet"
            description="Analyzed public posts will automatically appear here for quick offline reference."
          />
        ) : (
          <div className="space-y-3">
            {historyItems.map((item) => (
              <div
                key={item.id}
                onClick={() => handleOpenItem(item)}
                className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm hover:shadow-md transition-all hover:border-violet-400 cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
              >
                <div className="space-y-1.5 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700 capitalize">
                      {item.platform}
                    </span>

                    <span
                      className={cn(
                        'inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full border',
                        item.badgeClass || 'bg-slate-100 text-slate-700 border-slate-200'
                      )}
                    >
                      {getVerdictIcon(item.rawVerdict)}
                      <span>{item.verdict}</span>
                    </span>

                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      <span>{formatDate(item.timestamp)}</span>
                    </span>
                  </div>

                  <p className="text-xs font-bold text-slate-800 truncate">
                    {item.author} {item.authorUsername && <span className="font-normal text-slate-400">({item.authorUsername})</span>}
                  </p>

                  <p className="text-[11px] text-slate-400 font-mono truncate">
                    {item.url}
                  </p>
                </div>

                <div className="flex items-center gap-2 text-xs font-semibold text-violet-600 group-hover:translate-x-1 transition-transform shrink-0">
                  <span>View result</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  );
}
