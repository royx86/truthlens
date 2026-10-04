import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { AnalyzeInput } from '../components/analyze/AnalyzeInput';
import { AnalysisLoading } from '../components/analyze/AnalysisLoading';
import { AnalysisError } from '../components/analyze/AnalysisError';
import { PipelineSection } from '../components/results/PipelineSection';
import { analyzePost } from '../services/api';
import { normalizeAnalysisResponse } from '../utils/analysis';
import { saveAnalysisToHistory } from '../utils/history';
import { mockAnalysisData } from '../data/mockAnalysis';

export function Home() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [submittedUrl, setSubmittedUrl] = useState('');
  const navigate = useNavigate();

  const handleAnalyze = async (url, forceMock = false) => {
    setSubmittedUrl(url);
    setLoading(true);
    setError(null);

    try {
      const rawData = await analyzePost(url, forceMock);
      const normalized = normalizeAnalysisResponse(rawData);

      // Save to local storage history
      saveAnalysisToHistory(normalized, rawData);

      // Reset loading before navigating so returning users see a clean page
      setLoading(false);

      // Navigate to /results passing the normalized data and raw response
      navigate('/results', {
        state: {
          normalizedData: normalized,
          rawResponse: rawData,
        },
      });
    } catch (err) {
      console.error('Analysis request error:', err);
      setError(err);
      setLoading(false);
    }
  };

  const handleTryDemo = () => {
    handleAnalyze('https://www.instagram.com/p/C-exampleAIphoto/', true);
  };

  const handleRetry = () => {
    if (submittedUrl) {
      handleAnalyze(submittedUrl);
    } else {
      setError(null);
    }
  };

  const handleReset = () => {
    setError(null);
    setLoading(false);
    setSubmittedUrl('');
  };

  return (
    <PageContainer>
      {loading ? (
        <AnalysisLoading targetUrl={submittedUrl} />
      ) : error ? (
        <AnalysisError error={error} onRetry={handleRetry} onReset={handleReset} />
      ) : (
        <>
          <AnalyzeInput
            onSubmit={(url) => handleAnalyze(url, false)}
            isLoading={loading}
            onTryDemo={handleTryDemo}
          />
          <PipelineSection />
        </>
      )}
    </PageContainer>
  );
}
