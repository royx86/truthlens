/**
 * TruthLens Analysis Response Normalization Adapter
 * Provides clean, safe, and normalized data objects for UI components without scattering
 * optional chaining and lookups throughout component trees.
 */

export const VERDICT_CONFIG = {
  SUPPORTED: {
    key: 'SUPPORTED',
    label: 'Supported',
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    barColor: '#10b981',
    progressPct: 100,
  },
  PARTIALLY_SUPPORTED: {
    key: 'PARTIALLY_SUPPORTED',
    label: 'Partially supported',
    badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
    barColor: '#f59e0b',
    progressPct: 60,
  },
  MISLEADING: {
    key: 'MISLEADING',
    label: 'Misleading',
    badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
    barColor: '#f59e0b',
    progressPct: 40,
  },
  REFUTED: {
    key: 'REFUTED',
    label: 'Refuted',
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
    barColor: '#f43f5e',
    progressPct: 15,
  },
  UNVERIFIED: {
    key: 'UNVERIFIED',
    label: 'Unverified',
    badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
    barColor: '#3b82f6',
    progressPct: 50,
  },
  INSUFFICIENT_EVIDENCE: {
    key: 'INSUFFICIENT_EVIDENCE',
    label: 'Insufficient evidence',
    badgeClass: 'bg-slate-100 text-slate-700 border-slate-300',
    barColor: '#94a3b8',
    progressPct: 30,
  },
};

export const EVIDENCE_STATUS_MESSAGES = {
  no_results: 'No external sources were returned for this claim.',
  no_relevant_results: 'Search results were found, but no sufficiently relevant evidence was identified.',
  rate_limited: 'Evidence search was temporarily rate-limited. This claim could not be fully checked.',
  search_failed: 'Evidence search could not be completed.',
};

/**
 * Maps raw backend verdict string to safe UI config
 */
export function getVerdictConfig(rawVerdict) {
  if (!rawVerdict) {
    return {
      key: 'UNKNOWN',
      label: 'Not analyzed',
      badgeClass: 'bg-slate-100 text-slate-600 border-slate-200',
      barColor: '#94a3b8',
      progressPct: 0,
    };
  }
  const normalized = String(rawVerdict).trim().toUpperCase();
  return (
    VERDICT_CONFIG[normalized] || {
      key: normalized,
      label: normalized.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()),
      badgeClass: 'bg-slate-100 text-slate-700 border-slate-300',
      barColor: '#94a3b8',
      progressPct: 50,
    }
  );
}

/**
 * Derives overall verdict from analysis object or claim assessments
 */
function deriveOverallVerdict(analysisData) {
  if (!analysisData) return null;

  // If explicit overall verdict was placed on analysis
  if (analysisData.analysis?.verdict) {
    return analysisData.analysis.verdict;
  }

  // Derive from claim assessments if available
  const claims = analysisData.analysis?.claims || [];
  if (claims.length === 0) return null;

  const verdicts = claims.map((c) => c.verdict).filter(Boolean);
  if (verdicts.length === 0) return null;

  if (verdicts.includes('REFUTED')) {
    if (verdicts.includes('SUPPORTED')) return 'PARTIALLY_SUPPORTED';
    return 'REFUTED';
  }
  if (verdicts.includes('MISLEADING')) {
    return 'MISLEADING';
  }
  if (verdicts.includes('PARTIALLY_SUPPORTED')) {
    return 'PARTIALLY_SUPPORTED';
  }
  if (verdicts.every((v) => v === 'SUPPORTED')) {
    return 'SUPPORTED';
  }
  if (verdicts.includes('UNVERIFIED')) {
    return 'UNVERIFIED';
  }
  if (verdicts.includes('INSUFFICIENT_EVIDENCE')) {
    return 'INSUFFICIENT_EVIDENCE';
  }
  return verdicts[0];
}

/**
 * Derives overall confidence string
 */
function deriveOverallConfidence(analysisData) {
  const analysis = analysisData?.analysis;
  if (analysis?.confidence) {
    return typeof analysis.confidence === 'number'
      ? `${Math.round(analysis.confidence <= 1 ? analysis.confidence * 100 : analysis.confidence)}% confidence`
      : `${analysis.confidence} confidence`;
  }

  // Check claims confidence
  const claimConfs = (analysis?.claims || []).map((c) => c.confidence).filter(Boolean);
  if (claimConfs.length > 0) {
    // If high / medium / low
    const hasHigh = claimConfs.some((c) => String(c).toLowerCase() === 'high');
    const hasMed = claimConfs.some((c) => String(c).toLowerCase() === 'medium');
    if (hasHigh && !claimConfs.some((c) => String(c).toLowerCase() === 'low')) {
      return 'High confidence';
    }
    if (hasMed) return 'Medium confidence';
    return `${claimConfs[0]} confidence`;
  }

  return 'Confidence: Not available';
}

/**
 * Extracts and deduplicates key evidence sources
 */
function extractKeySources(evidenceList, analysisClaims) {
  const seenUrls = new Set();
  const sources = [];

  // Helper to add ranked source
  const addSource = (s) => {
    if (!s || !s.url || seenUrls.has(s.url)) return;
    seenUrls.add(s.url);
    sources.push({
      title: s.title || s.source_name || s.url,
      url: s.url,
      snippet: s.snippet || '',
      sourceName: s.source_name || extractDomain(s.url),
      publishedAt: s.published_at || null,
      sourceQuality: s.source_quality || 'unknown',
      relevance: s.relevance || 'medium',
      directness: s.directness || 'contextual',
      relationship: s.relationship || 'unclear',
    });
  };

  // Add from claim supporting/contradicting evidence first (highest relevance)
  if (Array.isArray(analysisClaims)) {
    for (const claim of analysisClaims) {
      if (Array.isArray(claim.supporting_evidence)) {
        claim.supporting_evidence.forEach(addSource);
      }
      if (Array.isArray(claim.contradicting_evidence)) {
        claim.contradicting_evidence.forEach(addSource);
      }
    }
  }

  // Next add from evidence sources array
  if (Array.isArray(evidenceList)) {
    for (const group of evidenceList) {
      if (Array.isArray(group.sources)) {
        group.sources.forEach(addSource);
      }
    }
  }

  return sources;
}

export function extractDomain(url) {
  try {
    const parsed = new URL(url.startsWith('http') ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

/**
 * Primary normalization function
 */
export function normalizeAnalysisResponse(raw) {
  if (!raw) return null;

  // Envelope unpack
  const root = raw.data || raw;
  const source = root.source || {};
  const author = root.author || {};
  const content = root.content || {};
  const context = root.context || {};
  const claims = Array.isArray(root.claims) ? root.claims : [];
  const evidenceList = Array.isArray(root.evidence) ? root.evidence : [];
  const analysis = root.analysis || {};
  const analysisClaims = Array.isArray(analysis.claims) ? analysis.claims : [];

  // Build claim assessment lookup map by claim_id (Section 16 requirement)
  const analysisClaimMap = new Map();
  for (const ac of analysisClaims) {
    if (ac && ac.claim_id) {
      analysisClaimMap.set(ac.claim_id, ac);
    }
  }

  // Build evidence lookup map by claim_id
  const evidenceMap = new Map();
  for (const ev of evidenceList) {
    if (ev && ev.claim_id) {
      evidenceMap.set(ev.claim_id, ev);
    }
  }

  // Normalized claims array with merged assessments
  const normalizedClaims = claims.map((claim, index) => {
    const claimId = claim.claim_id || `claim_${index + 1}`;
    const assessment = analysisClaimMap.get(claimId);
    const evItem = evidenceMap.get(claimId);

    const rawVerdict = assessment?.verdict || null;
    const verdictInfo = getVerdictConfig(rawVerdict);

    return {
      id: claimId,
      index: index + 1,
      text: claim.text || assessment?.claim_text || 'Claim text unavailable',
      priority: claim.priority || 'primary',
      importance: claim.importance || 'medium',
      claimType: claim.claim_type || 'factual',
      source: claim.source || 'post_text',
      verdict: verdictInfo,
      rawVerdict,
      confidence: assessment?.confidence || null,
      explanation: assessment?.explanation || '',
      supportingEvidence: assessment?.supporting_evidence || [],
      contradictingEvidence: assessment?.contradicting_evidence || [],
      context: assessment?.context || [],
      evidenceStatus: evItem?.status || 'success',
      evidenceStatusMessage: evItem?.status && EVIDENCE_STATUS_MESSAGES[evItem.status]
        ? EVIDENCE_STATUS_MESSAGES[evItem.status]
        : null,
      sources: evItem?.sources || [],
      hasAnalysis: Boolean(assessment),
    };
  });

  // Extract media items
  let mediaItems = [];
  if (Array.isArray(content.media)) {
    mediaItems = content.media;
  } else if (Array.isArray(root.media)) {
    mediaItems = root.media;
  }

  // Context flags
  const rawFlags = Array.isArray(context.flags)
    ? context.flags
    : Array.isArray(analysis.context_flags)
    ? analysis.context_flags
    : [];
  const flags = rawFlags.filter((f) => f && f !== 'none');
  const isSatire = flags.some((f) => ['satire', 'parody'].includes(f.toLowerCase()));

  // Overall verdict & confidence
  const overallVerdictKey = deriveOverallVerdict(root);
  const overallVerdict = getVerdictConfig(overallVerdictKey);
  const overallConfidence = deriveOverallConfidence(root);

  // Source credibility calculation or fallback
  let sourceCredibility = 'Not available';
  const keySources = extractKeySources(evidenceList, analysisClaims);
  if (keySources.length > 0) {
    const hasHighQuality = keySources.some((s) => s.sourceQuality === 'high');
    const hasMedQuality = keySources.some((s) => s.sourceQuality === 'medium');
    if (hasHighQuality) sourceCredibility = 'High';
    else if (hasMedQuality) sourceCredibility = 'Medium';
    else sourceCredibility = 'Variable';
  }

  return {
    source: {
      platform: source.platform || 'unknown',
      url: source.url || '',
    },
    author: {
      name: author.name || author.username || 'Unknown Author',
      username: author.username ? (author.username.startsWith('@') ? author.username : `@${author.username}`) : null,
      profileUrl: author.profile_url || null,
      profileImageUrl: author.profile_image_url || null,
      initials: (author.name || author.username || 'U').slice(0, 1).toUpperCase(),
    },
    content: {
      text: content.text || root.post_text || '',
      media: mediaItems,
      likes: content.likes || content.metadata?.like_count || null,
      comments: content.comments || content.metadata?.comment_count || null,
    },
    context: {
      flags,
      isSatire,
      limitations: root.context?.limitations || analysis.context_limitations || null,
    },
    overall: {
      verdict: overallVerdict,
      rawVerdict: overallVerdictKey,
      confidence: overallConfidence,
      sourceCredibility,
      claimsDetected: analysis.claims_analyzed ?? normalizedClaims.length,
      lastChecked: 'Just now',
      overallSummary: analysis.overall_summary || 'No overall summary was provided.',
    },
    claims: normalizedClaims,
    keySources,
    rawResponse: raw,
  };
}
