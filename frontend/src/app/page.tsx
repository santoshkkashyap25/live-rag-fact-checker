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
  ExternalLink
} from "lucide-react";
import styles from "./page.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  performance: PerformanceDetails;
}

export default function VerifyPage() {
  const [inputText, setInputText] = useState("");
  const [examples, setExamples] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<number | null>(null);

  // Fetch examples on mount
  useEffect(() => {
    async function fetchExamples() {
      try {
        const res = await fetch(`${API_BASE}/api/examples`);
        if (res.ok) {
          const data = await res.json();
          setExamples(data.examples);
        } else {
          throw new Error("Failed to load");
        }
      } catch (err) {
        // Fallback examples
        setExamples([
          "India has 28 states and 8 union territories.",
          "The Great Wall of China is visible from the Moon.",
          "Bananas are naturally radioactive due to potassium-40.",
          "Lightning never strikes the same place twice.",
          "The Digital India initiative was launched in 2015."
        ]);
      }
    }
    fetchExamples();
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

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);
    setExpandedEvidence(null);

    try {
      const res = await fetch(`${API_BASE}/api/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: inputText }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Verification failed. Please try again.");
      }

      const data: VerifyResponse = await res.json();
      setResult(data);
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
          </form>
        </section>

        {/* Loading State Animation */}
        {loading && (
          <section className={styles.loadingCard}>
            <div className={styles.loaderSpinner}>
              <RefreshCw className={styles.spinIcon} />
            </div>
            <h3 className={styles.loadingTitle}>Processing Live Fact-Check</h3>
            <div className={styles.stepsTimeline}>
              <div className={`${styles.step} ${loadingStep >= 0 ? styles.stepActive : ""}`}>
                <div className={styles.stepDot}>1</div>
                <div className={styles.stepLabel}>Extracting verifiable claim</div>
              </div>
              <div className={`${styles.step} ${loadingStep >= 1 ? styles.stepActive : ""}`}>
                <div className={styles.stepDot}>2</div>
                <div className={styles.stepLabel}>Searching the web in real-time</div>
              </div>
              <div className={`${styles.step} ${loadingStep >= 2 ? styles.stepActive : ""}`}>
                <div className={styles.stepDot}>3</div>
                <div className={styles.stepLabel}>Evaluating verdict & reasoning</div>
              </div>
            </div>
          </section>
        )}

        {/* Error State */}
        {error && (
          <section className={styles.errorCard}>
            <AlertCircle className={styles.errorIcon} />
            <div className={styles.errorContent}>
              <h4>Verification Failed</h4>
              <p>{error}</p>
            </div>
          </section>
        )}

        {/* Results Visualizer */}
        {result && (
          <section className={styles.resultContainer}>
            <div className={styles.resultGrid}>
              
              {/* Left Column: Verdict Card */}
              <div className={`${styles.resultCard} ${getVerdictClass(result.verdict)}`}>
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
                    <span className={styles.metricLabel}>Total Latency</span>
                    <span className={styles.metricValue}>
                      {result.performance.total_time}
                    </span>
                  </div>
                </div>

                <div className={styles.claimBox}>
                  <span className={styles.claimBoxLabel}>Extracted Claim:</span>
                  <p className={styles.claimBoxText}>"{result.extracted_claim}"</p>
                </div>
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
                Key evidence retrieved dynamically from DuckDuckGo & Wikipedia and prioritized via Cross-Encoder re-ranking.
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
                            Relevance: {Math.round(score * 100)}%
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
    </div>
  );
}
