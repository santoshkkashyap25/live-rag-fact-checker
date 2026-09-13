"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Sparkles,
  BarChart2,
  Clock,
  CheckCircle2,
  Globe,
  RefreshCw,
  TrendingUp,
  Award,
  AlertCircle
} from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  CartesianGrid
} from "recharts";
import styles from "./page.module.css";

const API_BASE = "";

interface VerdictDistribution {
  True: number;
  False: number;
  Unverifiable: number;
}

interface AnalyticsStats {
  summary: {
    total_queries: number;
    recent_queries: number;
    avg_total_time: number;
    avg_confidence: number;
    cache_hit_rate: number;
    verdict_distribution: VerdictDistribution;
    avg_evidence_count: number;
    message?: string;
  };
  cache: {
    size: number;
    max_size: number;
    ttl_seconds: number;
  };
  database: {
    status: string;
    total_facts?: number;
    embedding_dim?: number;
    index_type?: string;
    has_metadata?: boolean;
  };
  history: Array<{
    timestamp: string;
    total_time: number;
    confidence: number;
    verdict: string;
  }>;
}

const COLORS = ["#10b981", "#ef4444", "#f59e0b"]; // Green, Red, Orange

export default function AnalyticsPage() {
  const [stats, setStats] = useState<AnalyticsStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/analytics`);
      if (!res.ok) {
        throw new Error("Failed to fetch analytics statistics");
      }
      const data: AnalyticsStats = await res.json();
      setStats(data);
    } catch (err: any) {
      setError(err.message || "Could not load analytics. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading && !stats) {
    return (
      <div className={styles.loadingScreen}>
        <RefreshCw className={styles.spinIcon} />
        <p>Loading analytics dashboard...</p>
      </div>
    );
  }

  const summary = stats?.summary;
  const db = stats?.database;
  const cache = stats?.cache;
  const history = stats?.history || [];

  // Parse pie data
  const pieData = summary && summary.verdict_distribution ? [
    { name: "True", value: summary.verdict_distribution.True || 0 },
    { name: "False", value: summary.verdict_distribution.False || 0 },
    { name: "Unverifiable", value: summary.verdict_distribution.Unverifiable || 0 }
  ].filter(d => d.value > 0) : [];

  // Parse line data (response time history)
  const lineData = history.map((h, i) => ({
    name: i + 1,
    time: parseFloat(h.total_time.toFixed(2)),
    confidence: Math.round(h.confidence * 100),
    verdict: h.verdict
  }));

  // Parse bar data (confidence brackets)
  const confidenceData = (() => {
    if (history.length === 0) return [];
    const brackets = [
      { name: "0-20%", count: 0 },
      { name: "20-40%", count: 0 },
      { name: "40-60%", count: 0 },
      { name: "60-80%", count: 0 },
      { name: "80-100%", count: 0 }
    ];
    history.forEach(h => {
      const conf = h.confidence * 100;
      if (conf <= 20) brackets[0].count++;
      else if (conf <= 40) brackets[1].count++;
      else if (conf <= 60) brackets[2].count++;
      else if (conf <= 80) brackets[3].count++;
      else brackets[4].count++;
    });
    return brackets;
  })();

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <Link href="/" className={styles.logoArea}>
          <Sparkles className={styles.logoIcon} />
          <span className={styles.logoText}>FactGuard AI</span>
        </Link>
        <nav className={styles.nav}>
          <Link href="/" className={styles.navLink}>
            Verify Claim
          </Link>
          <Link href="/analytics" className={`${styles.navLink} ${styles.activeLink}`}>
            Analytics
          </Link>
        </nav>
      </header>

      {/* Main Content */}
      <main className={styles.main}>
        <div className={styles.topRow}>
          <div>
            <h1 className={styles.title}>System Analytics</h1>
            <p className={styles.subtitle}>
              Monitor real-time pipeline performance, accuracy ratios, and live web intelligence state.
            </p>
          </div>
          <button onClick={fetchStats} className={styles.refreshBtn} title="Refresh Statistics" disabled={loading}>
            <RefreshCw size={16} className={loading ? styles.spinIcon : ""} />
            <span>{loading ? "Refreshing..." : "Refresh"}</span>
          </button>
        </div>

        {error && (
          <div className={styles.errorBanner}>
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {summary && summary.total_queries === 0 ? (
          <div className={styles.emptyCard}>
            <BarChart2 className={styles.emptyIcon} />
            <h3>No Analytics Data Available</h3>
            <p>
              You haven't run any statement verifications yet. Please go to the 
              <Link href="/"> Verify Claim</Link> page and test some statements to generate performance metrics.
            </p>
          </div>
        ) : (
          stats && (
            <>
              {/* Overview Metrics Cards */}
              <section className={styles.statsGrid}>
                
                <div className={styles.statCard}>
                  <div className={styles.statIconArea}>
                    <TrendingUp className={styles.statIcon} />
                  </div>
                  <div className={styles.statInfo}>
                    <span className={styles.statLabel}>Total Queries</span>
                    <h2 className={styles.statValue}>{summary?.total_queries}</h2>
                    <span className={styles.statSub}>Cumulative pipeline executions</span>
                  </div>
                </div>

                <div className={styles.statCard}>
                  <div className={styles.statIconArea} style={{ backgroundColor: "rgba(139, 92, 246, 0.1)" }}>
                    <Clock className={styles.statIcon} style={{ color: "#8b5cf6" }} />
                  </div>
                  <div className={styles.statInfo}>
                    <span className={styles.statLabel}>Avg Latency</span>
                    <h2 className={styles.statValue}>
                      {summary?.avg_total_time?.toFixed(2)}s
                    </h2>
                    <span className={styles.statSub}>Average processing time</span>
                  </div>
                </div>

                <div className={styles.statCard}>
                  <div className={styles.statIconArea} style={{ backgroundColor: "rgba(16, 185, 129, 0.1)" }}>
                    <Award className={styles.statIcon} style={{ color: "#10b981" }} />
                  </div>
                  <div className={styles.statInfo}>
                    <span className={styles.statLabel}>Avg Confidence</span>
                    <h2 className={styles.statValue}>
                      {summary ? Math.round(summary.avg_confidence * 100) : 0}%
                    </h2>
                    <span className={styles.statSub}>System verification assurance</span>
                  </div>
                </div>

              </section>

              {/* Charts Grid */}
              <section className={styles.chartsGrid}>
                
                {/* Latency History */}
                <div className={styles.chartCard}>
                  <h3 className={styles.chartTitle}>Response Time Trend</h3>
                  <p className={styles.chartSubtitle}>Pipeline latency (seconds) for the last 100 queries</p>
                  <div className={styles.chartContainer}>
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={lineData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                        <XAxis dataKey="name" stroke="#6b7280" fontSize={12} />
                        <YAxis stroke="#6b7280" fontSize={12} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: "#0f172a", borderColor: "rgba(255,255,255,0.08)" }}
                          labelStyle={{ color: "#9ca3af" }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="time" 
                          stroke="#3b82f6" 
                          strokeWidth={2}
                          dot={{ r: 3, strokeWidth: 0, fill: "#3b82f6" }}
                          activeDot={{ r: 5 }} 
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Verdict Distribution */}
                <div className={styles.chartCard}>
                  <h3 className={styles.chartTitle}>Verdict Distribution</h3>
                  <p className={styles.chartSubtitle}>Breakdown of claim verification classifications</p>
                  <div className={styles.chartContainer} style={{ display: "flex", alignItems: "center" }}>
                    <div style={{ width: "60%", height: 260 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            {pieData.map((entry, index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={COLORS[entry.name === "True" ? 0 : entry.name === "False" ? 1 : 2]} 
                              />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{ backgroundColor: "#0f172a", borderColor: "rgba(255,255,255,0.08)" }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className={styles.pieLegend}>
                      {pieData.map((d, i) => (
                        <div key={i} className={styles.legendItem}>
                          <div 
                            className={styles.legendColor} 
                            style={{ backgroundColor: COLORS[d.name === "True" ? 0 : d.name === "False" ? 1 : 2] }}
                          />
                          <span className={styles.legendLabel}>{d.name} ({d.value})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Confidence Histograms */}
                <div className={styles.chartCard} style={{ gridColumn: "span 2" }}>
                  <h3 className={styles.chartTitle}>Confidence Level Distribution</h3>
                  <p className={styles.chartSubtitle}>Frequency count of verification confidence score ranges</p>
                  <div className={styles.chartContainer}>
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart data={confidenceData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                        <XAxis dataKey="name" stroke="#6b7280" fontSize={12} />
                        <YAxis stroke="#6b7280" fontSize={12} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#0f172a", borderColor: "rgba(255,255,255,0.08)" }}
                        />
                        <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

              </section>

              {/* Database & Cache Admins */}
              <section className={styles.systemSection}>
                
                {/* Real-Time Web Intelligence Info Card */}
                <div className={styles.systemCard}>
                  <div className={styles.systemHeader}>
                    <Globe size={20} className={styles.systemIcon} style={{ color: "#3b82f6" }} />
                    <h3>Web Intelligence Engine</h3>
                  </div>
                  <div className={styles.systemInfoGrid}>
                    <div className={styles.infoRow}>
                      <span>Status</span>
                      <strong className={styles.statusOnline}>Online / Active</strong>
                    </div>
                    <div className={styles.infoRow}>
                      <span>Search Providers</span>
                      <strong>DuckDuckGo & Wikipedia</strong>
                    </div>
                    <div className={styles.infoRow}>
                      <span>Coverage</span>
                      <strong>Live Internet (Real-Time)</strong>
                    </div>
                    <div className={styles.infoRow}>
                      <span>Re-ranker</span>
                      <strong>Cross-Encoder (MS-Marco)</strong>
                    </div>
                    <div className={styles.infoRow}>
                      <span>Citations & URLs</span>
                      <strong>Enabled</strong>
                    </div>
                  </div>
                </div>

              </section>
            </>
          )
        )}
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <p>© 2026 FactGuard AI.</p>
      </footer>
    </div>
  );
}
