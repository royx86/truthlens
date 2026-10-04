/**
 * Realistic mock analysis responses matching backend UnifiedAnalysisResponse schema.
 * Used when VITE_USE_MOCK_API=true or when "Try Demo Post" is clicked.
 */

export const mockAnalysisData = {
  status: "success",
  data: {
    source: {
      platform: "instagram",
      url: "https://www.instagram.com/p/C-exampleAIphoto/",
    },
    author: {
      name: "Akash • AI & Tech",
      username: "aiwith.akash",
      profile_url: "https://www.instagram.com/aiwith.akash",
      profile_image_url: null,
      id: "aiwith.akash",
    },
    content: {
      text: "AI finally crossed into 'looks real' territory.\n\nNo plastic faces.\nNo fake shine.\nActual skin texture, pores, imperfect lighting—the stuff your brain believes.\n\nThat's what generative AI unlocked.\nNot visuals that look cool... humans that feel real.\n\nFor creators, this is a cheat code.",
      media: [
        {
          type: "image",
          url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=800&q=80",
          thumbnail_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80",
          analysis_status: "success",
          extracted_text: "THIS IS AI",
          visual_analysis: {
            description: "Close-up portrait of a woman holding a phone with text 'THIS IS AI'. High-resolution facial detail, natural pores, subsurface scattering.",
            extracted_text: "THIS IS AI",
            has_visible_text: true,
            observed_visual_details: ["Subsurface scattering on skin", "Fine facial pores and specular highlights", "Text on phone cover"],
          },
        },
        {
          type: "image",
          url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=800&q=80",
          thumbnail_url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80",
          analysis_status: "success",
          extracted_text: null,
          visual_analysis: {
            description: "Secondary angle showing lighting and texture consistency.",
          },
        },
        {
          type: "image",
          url: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=800&q=80",
          thumbnail_url: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=200&q=80",
          analysis_status: "success",
          extracted_text: null,
          visual_analysis: {
            description: "Phone case close-up showing custom typography.",
          },
        },
        {
          type: "image",
          url: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=800&q=80",
          thumbnail_url: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=200&q=80",
          analysis_status: "success",
          extracted_text: null,
          visual_analysis: {
            description: "Side profile detailing ear and jewelry reflections.",
          },
        },
        {
          type: "image",
          url: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=800&q=80",
          thumbnail_url: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=200&q=80",
          analysis_status: "success",
          extracted_text: null,
          visual_analysis: {
            description: "Full portrait perspective in neutral indoor environment.",
          },
        },
      ],
      likes: 3281,
      comments: 9627,
    },
    context: {
      flags: ["none"],
    },
    claims: [
      {
        claim_id: "claim_1",
        text: "AI image generation has reached photorealistic skin texture, pores, and natural lighting.",
        priority: "primary",
        importance: "high",
        source: "post_text",
        requires_verification: true,
        claim_type: "factual",
        primary_query: "AI diffusion model photorealistic skin texture pores benchmark 2026",
      },
      {
        claim_id: "claim_2",
        text: "Everyone has access to AI tools capable of creating consistent photorealistic human models.",
        priority: "secondary",
        importance: "medium",
        source: "post_text",
        requires_verification: true,
        claim_type: "factual",
        primary_query: "generative AI consistent character identity accessibility limitations",
      },
      {
        claim_id: "claim_3",
        text: "Physical studios and human models are rendered completely obsolete by generative AI.",
        priority: "narrative",
        importance: "medium",
        source: "post_text",
        requires_verification: true,
        claim_type: "factual",
        primary_query: "commercial photography advertising adoption generative AI human models",
      },
    ],
    evidence: [
      {
        claim_id: "claim_1",
        search_query: "AI diffusion model photorealistic skin texture pores benchmark 2026",
        status: "success",
        sources: [
          {
            title: "Evaluating AI Image Generation Realism in 2026",
            url: "https://www.reuters.com/technology/evaluating-ai-image-realism-2026",
            snippet: "Independent tests show modern generative AI achieves high perceptual realism, though commercial adoption remains constrained by licensing and compute.",
            source_name: "reuters.com",
            published_at: "2026-02-14",
            source_quality: "high",
            relevance: "high",
            directness: "direct",
            relationship: "supports",
            source_role: "external",
          },
          {
            title: "Generative Vision Models Advance Sub-Surface Skin Scattering",
            url: "https://www.nature.com/articles/s41586-026-00123-x",
            snippet: "Recent benchmarks demonstrate modern diffusion networks faithfully synthesize micro-pores and ambient occlusion matching high-end digital photography.",
            source_name: "nature.com",
            published_at: "2026-01-20",
            source_quality: "high",
            relevance: "high",
            directness: "direct",
            relationship: "supports",
            source_role: "external",
          },
        ],
      },
      {
        claim_id: "claim_2",
        search_query: "generative AI consistent character identity accessibility limitations",
        status: "success",
        sources: [
          {
            title: "The Gap Between AI Demos and Commercial Production",
            url: "https://www.technologyreview.com/2026/02/gap-between-ai-demos-and-production",
            snippet: "Widespread accessibility of photorealistic models is limited by technical expertise and specialized prompting requirements.",
            source_name: "technologyreview.com",
            published_at: "2026-02-02",
            source_quality: "high",
            relevance: "high",
            directness: "direct",
            relationship: "contradicts",
            source_role: "external",
          },
        ],
      },
      {
        claim_id: "claim_3",
        search_query: "commercial photography advertising adoption generative AI human models",
        status: "success",
        sources: [
          {
            title: "Fact Check: Can Generative AI Fully Replace Commercial Photo Shoots?",
            url: "https://www.snopes.com/fact-check/generative-ai-replace-photo-shoots/",
            snippet: "Claims that AI has completely replaced human models are misleading; top fashion brands continue hybrid workflows for legal compliance.",
            source_name: "snopes.com",
            published_at: "2026-01-29",
            source_quality: "high",
            relevance: "high",
            directness: "direct",
            relationship: "contradicts",
            source_role: "external",
          },
        ],
      },
    ],
    analysis: {
      claims: [
        {
          claim_id: "claim_1",
          claim_text: "AI image generation has reached photorealistic skin texture, pores, and natural lighting.",
          verdict: "SUPPORTED",
          confidence: "high",
          explanation: "Independent benchmarking of diffusion and generative models confirms advanced sub-surface scattering and skin texture rendering capabilities in 2026.",
          supporting_evidence: [
            {
              title: "Evaluating AI Image Generation Realism in 2026",
              url: "https://www.reuters.com/technology/evaluating-ai-image-realism-2026",
              snippet: "Independent tests show modern generative AI achieves high perceptual realism.",
              source_name: "reuters.com",
              source_quality: "high",
              relevance: "high",
              directness: "direct",
              relationship: "supports",
            },
          ],
          contradicting_evidence: [],
          context: [],
        },
        {
          claim_id: "claim_2",
          claim_text: "Everyone has access to AI tools capable of creating consistent photorealistic human models.",
          verdict: "MISLEADING",
          confidence: "high",
          explanation: "While basic image generators are widely accessible, generating consistent character DNA across multiple poses requires complex workflows and GPU hardware not generally available to all casual users.",
          supporting_evidence: [
            {
              title: "The Gap Between AI Demos and Commercial Production",
              url: "https://www.technologyreview.com/2026/02/gap-between-ai-demos-and-production",
              snippet: "Widespread accessibility of photorealistic models is limited by technical expertise and specialized prompting requirements.",
              source_name: "technologyreview.com",
              source_quality: "high",
              relevance: "high",
              directness: "direct",
              relationship: "contradicts",
            },
          ],
          contradicting_evidence: [],
          context: [],
        },
        {
          claim_id: "claim_3",
          claim_text: "Physical studios and human models are rendered completely obsolete by generative AI.",
          verdict: "MISLEADING",
          confidence: "high",
          explanation: "Commercial brand advertising overwhelmingly relies on real talent, physical product interactions, and legal licensing that AI generation cannot fully replace.",
          supporting_evidence: [
            {
              title: "Fact Check: Can Generative AI Fully Replace Commercial Photo Shoots?",
              url: "https://www.snopes.com/fact-check/generative-ai-replace-photo-shoots/",
              snippet: "Claims that AI has completely replaced human models are misleading; top fashion brands continue hybrid workflows for legal compliance.",
              source_name: "snopes.com",
              source_quality: "high",
              relevance: "high",
              directness: "direct",
              relationship: "contradicts",
            },
          ],
          contradicting_evidence: [],
          context: [],
        },
      ],
      overall_summary: "The post accurately highlights that modern AI vision models produce photorealistic human features with authentic skin texture. However, the claim that creators no longer need studios or models and that everyone has seamless access to AI photorealism is exaggerated and misleading.",
      context_flags: ["none"],
      claims_analyzed: 3,
    },
  },
};

export const satireMockData = {
  status: "success",
  data: {
    source: {
      platform: "instagram",
      url: "https://www.instagram.com/p/DcilsqYMVlw/",
    },
    author: {
      name: "The Tathya News",
      username: "thetathyanews",
      profile_url: "https://www.instagram.com/thetathyanews",
      profile_image_url: null,
      id: "thetathyanews",
    },
    content: {
      text: "Donald Trump announced plans to bring Jerk4Krik into the 2028 Olympics. NOT REAL, ONLY FOR SATIRE.",
      media: [
        {
          type: "image",
          url: "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80",
          thumbnail_url: "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=200&q=80",
          analysis_status: "success",
          extracted_text: "TRUMP JERK4KRIK OLYMPICS 2028 - SATIRE",
          visual_analysis: {
            description: "Satirical digital graphic imitating an Olympic event poster.",
          },
        },
      ],
      likes: 1240,
      comments: 340,
    },
    context: {
      flags: ["satire", "parody"],
    },
    claims: [
      {
        claim_id: "claim_satire_1",
        text: "Donald Trump announced plans to bring Jerk4Krik into the Olympics.",
        priority: "primary",
        importance: "high",
        source: "post_text",
        requires_verification: true,
        claim_type: "satire",
        primary_query: "Donald Trump Jerk4Krik Olympic games announcement",
      },
    ],
    evidence: [
      {
        claim_id: "claim_satire_1",
        search_query: "Donald Trump Jerk4Krik Olympic games announcement",
        status: "success",
        sources: [
          {
            title: "Fact Check: Viral Jerk4Krik Olympic claim is satire",
            url: "https://factcheck.org/2026/01/jerk4krik-satire-debunked",
            snippet: "No such official event or sport exists; explicitly created by a satirical social media account.",
            source_name: "factcheck.org",
            published_at: "2026-01-16",
            source_quality: "high",
            relevance: "high",
            directness: "direct",
            relationship: "contradicts",
            source_role: "external",
          },
        ],
      },
    ],
    analysis: {
      claims: [
        {
          claim_id: "claim_satire_1",
          claim_text: "Donald Trump announced plans to bring Jerk4Krik into the Olympics.",
          verdict: "REFUTED",
          confidence: "high",
          explanation: "The claim is an explicit satire piece debunked by independent fact-checkers. No official Olympic announcement exists.",
          supporting_evidence: [],
          contradicting_evidence: [
            {
              title: "Fact Check: Viral Jerk4Krik Olympic claim is satire",
              url: "https://factcheck.org/2026/01/jerk4krik-satire-debunked",
              snippet: "No such official event exists; explicitly created by a satirical social media creator.",
              source_name: "factcheck.org",
              source_quality: "high",
              relevance: "high",
              directness: "direct",
              relationship: "contradicts",
            },
          ],
          context: ["Post caption contains 'NOT REAL, ONLY FOR SATIRE'"],
        },
      ],
      overall_summary: "Post is satirical in nature. The primary factual assertion was refuted by external records.",
      context_flags: ["satire", "parody"],
      claims_analyzed: 1,
    },
  },
};
