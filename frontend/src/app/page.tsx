"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Search, 
  Trash2, 
  Clock, 
  Cpu, 
  Globe, 
  ChevronDown, 
  ChevronUp, 
  Sparkles,
  RefreshCw,
  ExternalLink,
  Database,
  Zap,
  Settings,
  Layers,
  ShieldCheck,
  Terminal,
  Activity
} from "lucide-react";
import LLMSettingsModal, { LLMConfig } from "./components/LLMSettingsModal";
import styles from "./page.module.css";

const API_BASE = "";

interface PerformanceDetails {
  extraction_time: string;
  retrieval_time: string;
  llm_time: string;
  total_time: string;
}

interface VerifyResponse {
  input_text: string;
  extracted_claim: string;
  verdict: string;
  confidence: string;
  reasoning: string;
  evidence: string[];
  evidence_scores: string[];
  evidence_sources?: string[];
  evidence_urls?: string[];
  engine?: {
    provider: string;
    model: string;
  };
  is_cache_hit?: boolean;
  performance: PerformanceDetails;
}

const DEFAULT_LLM_CONFIG: LLMConfig = {
  provider: "groq",
  apiKey: "",
  model: "groq/compound-mini",
  isCustomKey: false
};

export default function VerifyPage() {
  const [inputText, setInputText] = useState("");
  const [examples, setExamples] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<number | null>(null);
  const [clearingCache, setClearingCache] = useState(false);
  const [cacheSuccessMsg, setCacheSuccessMsg] = useState<string | null>(null);
  const [userId, setUserId] = useState<string>("");
  const [isCacheHit, setIsCacheHit] = useState(false);
  const [llmConfig, setLlmConfig] = useState<LLMConfig>(DEFAULT_LLM_CONFIG);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [tickIndex, setTickIndex] = useState(0);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const pipelineTicks = [
    "Parsing linguistic dependencies and isolating claim propositions...",
    "Querying DuckDuckGo live index and Wikipedia encyclopedia...",
    "Re-ranking evidence passages via BM25Okapi & phrase relevance...",
    `Prompting ${llmConfig.provider.toUpperCase()} (${llmConfig.model}) for strict verification...`,
    "Synthesizing factual verdict, confidence score, and citations..."
  ];

  // Rotate dynamic telemetry ticker smoothly during verification
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (loading) {
      setTickIndex(0);
      timer = setInterval(() => {
        setTickIndex((prev) => (prev + 1) % pipelineTicks.length);
      }, 1100);
    }
    return () => clearInterval(timer);
  }, [loading, pipelineTicks.length]);

  // Auto-retry countdown for initial backend warming up
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (countdown > 0) {
      timer = setTimeout(() => {
        setCountdown((prev) => prev - 1);
      }, 1000);
    } else if (countdown === 0 && isWarmingUp && !loading && inputText.trim()) {
      setIsWarmingUp(false);
      handleVerify();
    }
    return () => clearTimeout(timer);
  }, [countdown, isWarmingUp, loading, inputText]);

  // Initialize unique client user identifier and saved LLM config
  useEffect(() => {
    if (typeof window !== "undefined") {
      let storedId = localStorage.getItem("factguard_user_id");
      if (!storedId) {
        storedId = "usr_" + Math.random().toString(36).substring(2, 9) + Date.now().toString(36);
        localStorage.setItem("factguard_user_id", storedId);
      }
      setUserId(storedId);

      try {
        const savedLlm = localStorage.getItem("factguard_llm_config");
        if (savedLlm) {
          const parsed = JSON.parse(savedLlm);
          // Migrate obsolete default model name
          if (!parsed.isCustomKey && parsed.provider === "groq" && (parsed.model === "llama-3.3-70b-versatile" || !parsed.model)) {
            parsed.model = "groq/compound-mini";
            localStorage.setItem("factguard_llm_config", JSON.stringify(parsed));
          }
          setLlmConfig(parsed);
        }
      } catch (err) {
        console.error("Failed to load saved LLM config", err);
      }
    }
  }, []);

  const handleSaveConfig = (newConfig: LLMConfig) => {
    setLlmConfig(newConfig);
    if (typeof window !== "undefined") {
      localStorage.setItem("factguard_llm_config", JSON.stringify(newConfig));
    }
  };

  // Fetch examples on mount with subtle retry if backend is still booting
  useEffect(() => {
    let cancelled = false;
    let attempts = 0;

    async function fetchExamples() {
      try {
        const res = await fetch(`${API_BASE}/api/examples`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setExamples(data.examples);
          return;
        }
      } catch (err) {
        // Backend might still be starting
      }

      if (!cancelled) {
        setExamples([
          "India has 28 states and 8 union territories.",
          "The Great Wall of China is visible from the Moon.",
          "Bananas are naturally radioactive due to potassium-40.",
          "Lightning never strikes the same place twice.",
          "The Digital India initiative was launched in 2015."
        ]);

        if (attempts < 5) {
          attempts++;
          setTimeout(fetchExamples, 2500);
        }
      }
    }

    fetchExamples();
    return () => {
      cancelled = true;
    };
  }, []);

  // Simulate loading steps during verify
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (loading) {
      interval = setInterval(() => {
        setLoadingStep((prev) => {
          if (prev < 2) return prev + 1;
          return prev;
        });
      }, 1000);
    } else {
      setLoadingStep(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleVerify = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);
    setIsWarmingUp(false);
    setExpandedEvidence(null);
    setIsCacheHit(false);

    try {
      const res = await fetch(`${API_BASE}/api/verify`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "X-User-ID": userId || "default_user",
          "X-LLM-Provider": llmConfig.provider,
          "X-LLM-API-Key": llmConfig.apiKey || "",
          "X-LLM-Model": llmConfig.model || "",
        },
        body: JSON.stringify({ 
          text: inputText, 
          user_id: userId || "default_user",
          llm_provider: llmConfig.provider,
          llm_api_key: llmConfig.apiKey || undefined,
          llm_model: llmConfig.model || undefined
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const detailMsg = errData.detail || "Verification failed. Please try again.";
        const isWarm = 
          res.status === 503 || 
          res.status === 502 ||
          errData.code === "BACKEND_WARMING_UP" ||
          detailMsg.includes("initializing") || 
          detailMsg.includes("warming up") || 
          detailMsg.includes("fetch failed") ||
          detailMsg.includes("Proxy error");

        if (isWarm) {
          setIsWarmingUp(true);
          setCountdown(4);
        }
        throw new Error(detailMsg);
      }

      const data: VerifyResponse = await res.json();
      setResult(data);
      setIsCacheHit(!!data.is_cache_hit);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setInputText("");
    setResult(null);
    setError(null);
    setExpandedEvidence(null);
    setIsCacheHit(false);
  };

  const handleClearCache = async () => {
    if (!confirm("Are you sure you want to clear your query cache?")) return;
    setClearingCache(true);
    setCacheSuccessMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/cache/clear`, {
        method: "POST",
        headers: {
          "X-User-ID": userId || "default_user",
        },
      });
      if (!res.ok) throw new Error("Failed to clear query cache");
      
      // Reset cache hit signal immediately on cache clear
      setIsCacheHit(false);
      setCacheSuccessMsg("Your cache cleared!");
      setTimeout(() => setCacheSuccessMsg(null), 3000);
    } catch (err: any) {
      alert(err.message || "Error clearing query cache.");
    } finally {
      setClearingCache(false);
    }
  };

  const handleExampleClick = (ex: string) => {
    setInputText(ex);
  };

  const getVerdictIcon = (verdict: string) => {
    switch (verdict) {
      case "True":
        return <CheckCircle2 className={`${styles.verdictIcon} ${styles.trueIcon}`} />;
      case "False":
        return <XCircle className={`${styles.verdictIcon} ${styles.falseIcon}`} />;
      default:
        return <AlertCircle className={`${styles.verdictIcon} ${styles.unverifiableIcon}`} />;
    }
  };

  const getVerdictClass = (verdict: string) => {
    switch (verdict) {
      case "True":
        return styles.verdictTrue;
      case "False":
        return styles.verdictFalse;
      default:
        return styles.verdictUnverifiable;
    }
  };

  const formatRelevance = (score: number) => {
    if (score >= 0 && score <= 1) {
      return `${Math.round(score * 100)}%`;
    }
    // Cross-encoder logit conversion via sigmoid
    const sigmoid = 1 / (1 + Math.exp(-score));
    return `${Math.min(100, Math.max(1, Math.round(sigmoid * 100)))}%`;
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <Link href="/" className={styles.logoArea}>
          <Sparkles className={styles.logoIcon} />
          <span className={styles.logoText}>FactGuard AI</span>
        </Link>
        <nav className={styles.nav}>
          <Link href="/" className={`${styles.navLink} ${styles.activeLink}`}>
            Verify Claim
          </Link>
          <Link href="/analytics" className={styles.navLink}>
            Analytics
          </Link>
          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            className={styles.settingsNavBtn}
            title="Configure LLM Provider & Custom API Keys"
          >
            <Settings size={15} />
            <span>LLM Settings</span>
            <span className={`${styles.providerPill} ${llmConfig.isCustomKey ? styles.providerPillCustom : ""}`}>
              {llmConfig.provider.toUpperCase()} {llmConfig.isCustomKey ? "(BYOK)" : "(Default)"}
            </span>
          </button>
        </nav>
      </header>

      {/* Main Content */}
      <main className={styles.main}>
        <div className={styles.heroSection}>
          <h1 className={styles.title}>Real-Time Web Intelligence & Fact Verification</h1>
          <p className={styles.subtitle}>
            Enter any news headline, viral claim, or factual statement to verify its accuracy against real-time internet intelligence (DuckDuckGo + Wikipedia).
          </p>
        </div>

        {/* Active Engine Bar */}
        <div className={styles.engineBar}>
          <div className={styles.engineInfo}>
            <Cpu size={15} className={styles.engineIcon} />
            <span className={styles.engineLabel}>Verification Engine:</span>
            <strong className={styles.engineName}>
              {llmConfig.provider.toUpperCase()} • {llmConfig.model}
            </strong>
            <span className={`${styles.engineBadge} ${llmConfig.isCustomKey ? styles.engineBadgeCustom : ""}`}>
              {llmConfig.isCustomKey ? "Custom API Key Active" : "Server Default"}
            </span>
          </div>
          <button 
            type="button" 
            onClick={() => setIsSettingsOpen(true)}
            className={styles.engineChangeBtn}
          >
            Switch Provider / Add Key →
          </button>
        </div>

        {/* Input Area Card */}
        <section className={styles.inputCard}>
          {examples.length > 0 && (
            <div className={styles.examplesContainer}>
              <span className={styles.examplesLabel}>Try an example:</span>
              <div className={styles.examplePills}>
                {examples.map((ex, i) => (
                  <button
                    key={i}
                    onClick={() => handleExampleClick(ex)}
                    className={styles.examplePill}
                    type="button"
                  >
                    {ex.length > 50 ? `${ex.substring(0, 50)}...` : ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          <form onSubmit={handleVerify} className={styles.form}>
            <div className={styles.textareaWrapper}>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Enter any claim or statement to verify against live internet evidence..."
                maxLength={1000}
                className={styles.textarea}
                rows={4}
                disabled={loading}
              />
              <span className={styles.charCounter}>
                {inputText.length}/1000
              </span>
            </div>

            <div className={styles.actionRow}>
              <div className={styles.actionButtons}>
                <button
                  type="submit"
                  disabled={loading || !inputText.trim()}
                  className={`${styles.btn} ${styles.btnPrimary}`}
                >
                  <Search size={18} />
                  <span>Verify Statement</span>
                </button>
                
                <button
                  type="button"
                  onClick={handleClear}
                  disabled={loading || !inputText}
                  className={`${styles.btn} ${styles.btnSecondary}`}
                >
                  <Trash2 size={18} />
                  <span>Clear</span>
                </button>
              </div>

              {/* Query Cache Manager & Live Signal */}
              <div className={`${styles.cacheManager} ${isCacheHit ? styles.cacheManagerHit : ""}`}>
                <span className={styles.cacheManagerLabel}>
                  <Database size={14} style={{ color: "#ec4899" }} />
                  Query Cache
                </span>

                {/* Live Cache Status Signal */}
                <div 
                  className={`${styles.cacheSignal} ${isCacheHit ? styles.cacheSignalHit : styles.cacheSignalIdle}`}
                  title={isCacheHit ? "Cache Hit Active: Instant response served from memory" : "Cache Standby: Ready for queries"}
                >
                  <span className={`${styles.signalDot} ${isCacheHit ? styles.signalDotHit : ""}`} />
                  <span>{isCacheHit ? "Cache Hit Active" : "Cache Standby"}</span>
                </div>

                <button
                  type="button"
                  onClick={handleClearCache}
                  disabled={clearingCache || loading}
                  className={styles.clearCacheBtn}
                  title="Clear cached verification results to force fresh live web search"
                >
                  <Trash2 size={14} />
                  <span>{clearingCache ? "Clearing..." : "Clear Cache"}</span>
                </button>
                {cacheSuccessMsg && (
                  <span className={styles.cacheSuccessMsg}>
                    <CheckCircle2 size={13} />
                    {cacheSuccessMsg}
                  </span>
                )}
              </div>
            </div>
          </form>
        </section>

        {/* Loading State Animation */}
        {loading && (
          <section className={styles.loadingCard}>
            <div className={styles.loadingAura} />

            {/* Futuristic Orbital Gyroscope / Radar Spinner */}
            <div className={styles.orbitalWrapper}>
              <div className={styles.orbitalRingOuter} />
              <div className={styles.orbitalRingInner} />
              <div className={styles.orbitalPulseGlow} />
              <div className={styles.orbitalCore}>
                {loadingStep === 0 && <Layers className={`${styles.orbitalIcon} ${styles.iconStep0}`} />}
                {loadingStep === 1 && <Globe className={`${styles.orbitalIcon} ${styles.iconStep1}`} />}
                {loadingStep >= 2 && <ShieldCheck className={`${styles.orbitalIcon} ${styles.iconStep2}`} />}
              </div>
            </div>

            <div className={styles.loadingHeaderArea}>
              <h3 className={styles.loadingTitle}>Processing Live Fact-Check</h3>
              <p className={styles.loadingSubtitle}>
                Verifying claim against real-time web intelligence and neural re-ranking
              </p>
            </div>

            {/* Stepper with Connected Dynamic Flow Line */}
            <div className={styles.stepsTimeline}>
              <div className={styles.timelineTrack}>
                <div 
                  className={styles.timelineProgress} 
                  style={{ width: loadingStep === 0 ? "20%" : loadingStep === 1 ? "60%" : "100%" }}
                />
              </div>

              <div className={`${styles.step} ${loadingStep === 0 ? styles.stepCurrent : loadingStep > 0 ? styles.stepDone : ""}`}>
                <div className={styles.stepNode}>
                  {loadingStep > 0 ? (
                    <CheckCircle2 size={16} className={styles.stepCheckIcon} />
                  ) : (
                    <span>1</span>
                  )}
                  {loadingStep === 0 && <div className={styles.stepSonar} />}
                </div>
                <div className={styles.stepContent}>
                  <span className={styles.stepTitle}>Claim Parsing</span>
                  <span className={styles.stepDesc}>NLP proposition isolation</span>
                </div>
              </div>

              <div className={`${styles.step} ${loadingStep === 1 ? styles.stepCurrent : loadingStep > 1 ? styles.stepDone : ""}`}>
                <div className={styles.stepNode}>
                  {loadingStep > 1 ? (
                    <CheckCircle2 size={16} className={styles.stepCheckIcon} />
                  ) : (
                    <span>2</span>
                  )}
                  {loadingStep === 1 && <div className={styles.stepSonar} />}
                </div>
                <div className={styles.stepContent}>
                  <span className={styles.stepTitle}>Live Web Search</span>
                  <span className={styles.stepDesc}>DuckDuckGo & Wikipedia</span>
                </div>
              </div>

              <div className={`${styles.step} ${loadingStep >= 2 ? styles.stepCurrent : ""}`}>
                <div className={styles.stepNode}>
                  <span>3</span>
                  {loadingStep >= 2 && <div className={styles.stepSonar} />}
                </div>
                <div className={styles.stepContent}>
                  <span className={styles.stepTitle}>LLM Verification</span>
                  <span className={styles.stepDesc}>{llmConfig.provider.toUpperCase()} Reasoning</span>
                </div>
              </div>
            </div>

            {/* Rolling Telemetry & Equalizer Soundwave Bar */}
            <div className={styles.telemetryBar}>
              <div className={styles.telemetryPulse}>
                <span className={styles.liveDot} />
                <span className={styles.telemetryTag}>PIPELINE ACTIVE</span>
              </div>

              <div className={styles.equalizerWave}>
                <span className={styles.eqBar} />
                <span className={styles.eqBar} />
                <span className={styles.eqBar} />
                <span className={styles.eqBar} />
                <span className={styles.eqBar} />
              </div>

              <div className={styles.rollingLogArea}>
                <Terminal size={13} className={styles.terminalIcon} />
                <span key={tickIndex} className={styles.rollingLogText}>
                  {pipelineTicks[tickIndex % pipelineTicks.length]}
                </span>
              </div>
            </div>
          </section>
        )}

        {/* Error / Warming Up State */}
        {error && isWarmingUp ? (
          <section className={styles.warmupCard}>
            <div className={styles.warmupIconWrapper}>
              <Activity className={styles.warmupIcon} />
            </div>
            <div className={styles.warmupContent}>
              <h4>Backend Engine Initializing</h4>
              <p>
                The Python AI backend is currently warming up (loading linguistic and search indexes). Initial cold-start takes ~1–3 seconds after launching containers.
              </p>
              <div className={styles.warmupActions}>
                <button
                  type="button"
                  onClick={() => {
                    setIsWarmingUp(false);
                    setCountdown(0);
                    handleVerify();
                  }}
                  className={styles.warmupRetryBtn}
                  disabled={loading}
                >
                  <RefreshCw size={14} className={loading ? styles.spinIcon : ""} />
                  <span>
                    {countdown > 0 ? `Auto-retrying in ${countdown}s...` : "Retry Verification Now"}
                  </span>
                </button>
              </div>
            </div>
          </section>
        ) : error ? (
          <section className={styles.errorCard}>
            <AlertCircle className={styles.errorIcon} />
            <div className={styles.errorContent}>
              <h4>Verification Failed</h4>
              <p>{error}</p>
            </div>
          </section>
        ) : null}

        {/* Results Visualizer */}
        {result && (
          <section className={styles.resultContainer}>
            <div className={styles.resultGrid}>
              
              {/* Left Column: Verdict Card */}
              <div className={`${styles.resultCard} ${getVerdictClass(result.verdict)}`}>
                {isCacheHit && (
                  <div className={styles.cacheHitBanner}>
                    <Zap size={14} className={styles.zapIcon} />
                    <span>CACHE HIT • Instant Response</span>
                  </div>
                )}

                <div className={styles.verdictHeader}>
                  {getVerdictIcon(result.verdict)}
                  <div>
                    <span className={styles.verdictLabel}>Verdict</span>
                    <h2 className={styles.verdictTitle}>{result.verdict}</h2>
                  </div>
                </div>

                <div className={styles.metricsRow}>
                  <div className={styles.metricItem}>
                    <span className={styles.metricLabel}>Confidence</span>
                    <span className={styles.metricValue}>
                      {Math.round(parseFloat(result.confidence) * 100)}%
                    </span>
                    <div className={styles.progressBarBg}>
                      <div 
                        className={styles.progressBarFill} 
                        style={{ width: `${parseFloat(result.confidence) * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className={styles.metricItem}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span className={styles.metricLabel}>Total Latency</span>
                      {isCacheHit && <span className={styles.cachePill}>Cached</span>}
                    </div>
                    <span className={styles.metricValue}>
                      {result.performance.total_time}
                    </span>
                  </div>
                </div>

                <div className={styles.claimBox}>
                  <span className={styles.claimBoxLabel}>Extracted Claim:</span>
                  <p className={styles.claimBoxText}>"{result.extracted_claim}"</p>
                </div>

                {result.engine && (
                  <div className={styles.engineVerdictTag}>
                    <Cpu size={13} />
                    <span>Verified via {result.engine.provider.toUpperCase()} ({result.engine.model})</span>
                  </div>
                )}
              </div>

              {/* Right Column: Reasoning & Timeline */}
              <div className={styles.resultCard}>
                <h3 className={styles.sectionTitle}>Verification Reasoning</h3>
                <div className={styles.reasoningContent}>
                  <p>{result.reasoning}</p>
                </div>

                <div className={styles.performanceBreakdown}>
                  <h4 className={styles.performanceTitle}>Pipeline Breakdown</h4>
                  <div className={styles.perfGrid}>
                    <div className={styles.perfItem}>
                      <Search size={16} className={styles.perfIcon} />
                      <div>
                        <span>Claim Parsing</span>
                        <strong>{result.performance.extraction_time}</strong>
                      </div>
                    </div>
                    <div className={styles.perfItem}>
                      <Globe size={16} className={styles.perfIcon} />
                      <div>
                        <span>Live Search</span>
                        <strong>{result.performance.retrieval_time}</strong>
                      </div>
                    </div>
                    <div className={styles.perfItem}>
                      <Cpu size={16} className={styles.perfIcon} />
                      <div>
                        <span>LLM Verdict</span>
                        <strong>{result.performance.llm_time}</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

            </div>

            {/* Evidence List Card */}
            <div className={`${styles.resultCard} ${styles.evidenceCard}`}>
              <h3 className={styles.sectionTitle}>Live Web Evidence</h3>
              <p className={styles.evidenceSubtitle}>
                Key evidence retrieved dynamically from DuckDuckGo & Wikipedia and prioritized via BM25Okapi relevance re-ranking.
              </p>

              <div className={styles.evidenceList}>
                {result.evidence.map((ev, index) => {
                  const isExpanded = expandedEvidence === index;
                  const score = parseFloat(result.evidence_scores[index] || "0");
                  const source = result.evidence_sources?.[index] || "Web";
                  const url = result.evidence_urls?.[index];
                  
                  return (
                    <div 
                      key={index} 
                      className={`${styles.evidenceItem} ${isExpanded ? styles.evidenceExpanded : ""}`}
                    >
                      <button
                        onClick={() => setExpandedEvidence(isExpanded ? null : index)}
                        className={styles.evidenceHeader}
                        type="button"
                      >
                        <div className={styles.evidenceTitleArea}>
                          <span className={styles.evidenceIndex}>#{index + 1}</span>
                          <span className={styles.sourceBadge}>
                            <Globe size={11} /> {source}
                          </span>
                          <span className={styles.evidencePreview}>
                            {ev.length > 80 ? `${ev.substring(0, 80)}...` : ev}
                          </span>
                        </div>
                        <div className={styles.evidenceHeaderRight}>
                          <span className={styles.evidenceScore}>
                            Relevance: {formatRelevance(score)}
                          </span>
                          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </div>
                      </button>
                      
                      {isExpanded && (
                        <div className={styles.evidenceBody}>
                          <p className={styles.evidenceFullText}>{ev}</p>
                          {url && (
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={styles.evidenceSourceLink}
                            >
                              <Globe size={13} />
                              <span>Read Source Article</span>
                              <ExternalLink size={12} />
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

          </section>
        )}
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <p>© 2026 FactGuard AI.</p>
      </footer>

      {/* LLM Settings Modal */}
      <LLMSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentConfig={llmConfig}
        onSave={handleSaveConfig}
      />
    </div>
  );
}
