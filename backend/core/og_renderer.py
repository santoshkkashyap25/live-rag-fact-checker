# core/og_renderer.py
import html
from typing import Dict, Any
from core.security import sanitize_secrets

def render_og_svg(item: Dict[str, Any]) -> str:
    """Generate dynamic OpenGraph SVG card badge"""
    verdict_raw = str(item.get("verdict", "Unverifiable"))
    verdict = html.escape(verdict_raw if verdict_raw in ["True", "False", "Unverifiable"] else "Unverifiable")
    raw_claim = sanitize_secrets(item.get("extracted_claim") or item.get("input_text") or "Verified Claim")
    claim = html.escape(raw_claim[:90])
    confidence_raw = item.get("confidence", 0.9)
    try:
        conf_val = float(confidence_raw)
        conf_pct = int(conf_val * 100) if conf_val <= 1.0 else int(conf_val)
    except Exception:
        conf_pct = 90

    # Color scheme based on verdict
    if verdict == "True":
        accent_color = "#22c55e"
        badge_bg = "rgba(34, 197, 94, 0.15)"
        badge_border = "#22c55e"
    elif verdict == "False":
        accent_color = "#ef4444"
        badge_bg = "rgba(239, 68, 68, 0.15)"
        badge_border = "#ef4444"
    else:
        accent_color = "#f59e0b"
        badge_bg = "rgba(245, 158, 11, 0.15)"
        badge_border = "#f59e0b"

    citations_count = len(item.get("evidence", []))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" fill="none">
    <defs>
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#090d16" />
            <stop offset="50%" stop-color="#0f172a" />
            <stop offset="100%" stop-color="#070a12" />
        </linearGradient>
        <linearGradient id="shield_grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#38bdf8" />
            <stop offset="100%" stop-color="#818cf8" />
        </linearGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="15" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
    </defs>

    <!-- Background -->
    <rect width="1200" height="630" fill="url(#bg)" />

    <!-- Ambient Glowing Orb -->
    <circle cx="950" cy="180" r="240" fill="{accent_color}" opacity="0.12" filter="url(#glow)" />
    <circle cx="200" cy="480" r="200" fill="#38bdf8" opacity="0.08" filter="url(#glow)" />

    <!-- Border -->
    <rect x="20" y="20" width="1160" height="590" rx="24" stroke="rgba(255,255,255,0.1)" stroke-width="2" fill="none" />

    <!-- Brand Header -->
    <g transform="translate(80, 70)">
        <!-- Shield Icon -->
        <path d="M28 4L6 14V30C6 44 15 56 28 60C41 56 50 44 50 30V14L28 4Z" fill="url(#shield_grad)" />
        <path d="M22 30L26 34L34 24" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
        <text x="68" y="42" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="34" font-weight="800" letter-spacing="-0.5">
            FactGuard<tspan fill="#38bdf8">.AI</tspan>
        </text>
        <text x="310" y="42" fill="#64748b" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="500">
            Real-Time Web Intelligence Verification
        </text>
    </g>

    <!-- Claim Box -->
    <g transform="translate(80, 160)">
        <text x="0" y="30" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="600" text-transform="uppercase" letter-spacing="1">
            VERIFIED CLAIM
        </text>
        <rect x="0" y="50" width="1040" height="150" rx="16" fill="rgba(255, 255, 255, 0.03)" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1.5" />
        <text x="40" y="130" fill="#f8fafc" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="36" font-weight="700">
            "{claim}"
        </text>
    </g>

    <!-- Verdict Card & Metrics -->
    <g transform="translate(80, 390)">
        <!-- Verdict Badge -->
        <rect x="0" y="0" width="320" height="120" rx="20" fill="{badge_bg}" stroke="{badge_border}" stroke-width="2.5" />
        <text x="36" y="52" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="16" font-weight="600">
            AI VERDICT
        </text>
        <text x="36" y="96" fill="{accent_color}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="44" font-weight="900" letter-spacing="1">
            {verdict.upper()}
        </text>

        <!-- Confidence Gauge -->
        <g transform="translate(360, 0)">
            <rect x="0" y="0" width="320" height="120" rx="20" fill="rgba(255, 255, 255, 0.03)" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1.5" />
            <text x="36" y="52" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="16" font-weight="600">
                CONFIDENCE SCORE
            </text>
            <text x="36" y="96" fill="#f8fafc" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="44" font-weight="900">
                {conf_pct}%
            </text>
        </g>

        <!-- Evidence Citations Count -->
        <g transform="translate(720, 0)">
            <rect x="0" y="0" width="320" height="120" rx="20" fill="rgba(255, 255, 255, 0.03)" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1.5" />
            <text x="36" y="52" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="16" font-weight="600">
                LIVE WEB CITATIONS
            </text>
            <text x="36" y="96" fill="#38bdf8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="44" font-weight="900">
                {citations_count} Sources
            </text>
        </g>
    </g>

    <!-- Footer URL -->
    <text x="80" y="570" fill="#475569" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="18" font-weight="500">
        Live Verification by FactGuard • Powered by DuckDuckGo, Wikipedia &amp; Multi-LLM RAG
    </text>
</svg>"""
    return svg


def render_shared_page_html(item: Dict[str, Any], share_id: str, app_url: str = "https://factguard-1gge.onrender.com") -> str:
    """Generate dynamic server-rendered HTML page with OpenGraph & Twitter Card tags"""
    raw_claim = sanitize_secrets(item.get("extracted_claim") or item.get("input_text") or "Verified Claim")
    claim = html.escape(raw_claim[:250])
    raw_verdict = str(item.get("verdict", "Unverifiable"))
    verdict = html.escape(raw_verdict if raw_verdict in ["True", "False", "Unverifiable"] else "Unverifiable")
    raw_reasoning = sanitize_secrets(item.get("reasoning", "Evidence analyzed against claim."))
    reasoning = html.escape(raw_reasoning[:1000])
    confidence_raw = item.get("confidence", 0.9)
    try:
        conf_val = float(confidence_raw)
        conf_pct = int(conf_val * 100) if conf_val <= 1.0 else int(conf_val)
    except Exception:
        conf_pct = 90

    if verdict == "True":
        verdict_color = "#22c55e"
        badge_bg = "rgba(34, 197, 94, 0.15)"
        badge_border = "#22c55e"
    elif verdict == "False":
        verdict_color = "#ef4444"
        badge_bg = "rgba(239, 68, 68, 0.15)"
        badge_border = "#ef4444"
    else:
        verdict_color = "#f59e0b"
        badge_bg = "rgba(245, 158, 11, 0.15)"
        badge_border = "#f59e0b"

    engine = item.get("engine", {})
    provider_name = engine.get("provider", "LLM").upper()
    model_name = engine.get("model", "default")
    performance = item.get("performance", {})
    total_time = performance.get("total_time", "N/A")

    # Render evidence items
    evidence_items = item.get("evidence", [])
    evidence_urls = item.get("evidence_urls", [])
    evidence_sources = item.get("evidence_sources", [])

    evidence_cards_html = ""
    for i, ev_text in enumerate(evidence_items):
        src = html.escape(evidence_sources[i]) if i < len(evidence_sources) else "Web"
        url = evidence_urls[i] if i < len(evidence_urls) and evidence_urls[i] else "#"
        clean_text = html.escape(ev_text)
        evidence_cards_html += f"""
        <div class="evidence-card">
            <div class="evidence-header">
                <span class="evidence-source-tag">{src}</span>
                {f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="evidence-link">View Original Source &#x2197;</a>' if url != '#' else ''}
            </div>
            <p class="evidence-text">{clean_text}</p>
        </div>
        """

    share_url = f"{app_url}/v/{share_id}"
    og_image_url = f"{app_url}/api/og/{share_id}.svg"
    github_repo = "https://github.com/santoshkkashyap25/live-rag-fact-checker"
    tweet_text = html.escape(f"Fact-checked with @FactGuard: '{claim[:80]}' is {verdict} ({conf_pct}% confidence). Live citations: {share_url}")
    tweet_intent = f"https://twitter.com/intent/tweet?text={tweet_text}"
    reddit_intent = f"https://reddit.com/submit?url={html.escape(share_url)}&title={html.escape(f'FactGuard: {verdict} - {claim[:80]}')}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FactGuard Verdict: {verdict} ({conf_pct}%) - "{claim}"</title>
    
    <!-- OpenGraph & Social Metadata -->
    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="FactGuard AI" />
    <meta property="og:title" content="FactGuard: {verdict} ({conf_pct}% Confidence) - \"{claim}\"" />
    <meta property="og:description" content="{reasoning[:240]}" />
    <meta property="og:url" content="{share_url}" />
    <meta property="og:image" content="{og_image_url}" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />

    <!-- Twitter Cards -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:site" content="@FactGuard" />
    <meta name="twitter:title" content="FactGuard: {verdict} - \"{claim}\"" />
    <meta name="twitter:description" content="{reasoning[:240]}" />
    <meta name="twitter:image" content="{og_image_url}" />

    <link rel="icon" href="/favicon.ico" />
    <style>
        :root {{
            --bg-primary: #070a13;
            --bg-secondary: #0f172a;
            --bg-card: rgba(15, 23, 42, 0.75);
            --border-color: rgba(255, 255, 255, 0.1);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #38bdf8;
            --verdict-color: {verdict_color};
            --verdict-bg: {badge_bg};
            --verdict-border: {badge_border};
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }}
        body {{
            background-color: var(--bg-primary);
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(129, 140, 248, 0.08) 0px, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 30px 16px 60px;
        }}
        .container {{
            width: 100%;
            max-width: 860px;
        }}
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 32px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: #fff;
        }}
        .brand svg {{
            width: 32px;
            height: 32px;
        }}
        .brand-title {{
            font-size: 1.4rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }}
        .brand-title span {{
            color: var(--accent);
        }}
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s ease;
            cursor: pointer;
            border: 1px solid var(--border-color);
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #fff;
            border-color: rgba(255,255,255,0.2);
        }}
        .btn-primary:hover {{
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.5);
            transform: translateY(-1px);
        }}
        .btn-outline {{
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }}
        .btn-outline:hover {{
            background: rgba(255, 255, 255, 0.1);
        }}
        .verdict-hero {{
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 32px;
            margin-bottom: 28px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }}
        .claim-label {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .claim-title {{
            font-size: 1.6rem;
            font-weight: 700;
            line-height: 1.4;
            color: #fff;
            margin-bottom: 24px;
        }}
        .verdict-status-row {{
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
            padding: 18px 24px;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 14px;
            margin-bottom: 24px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }}
        .verdict-badge {{
            padding: 8px 22px;
            border-radius: 12px;
            font-size: 1.25rem;
            font-weight: 900;
            letter-spacing: 0.5px;
            color: var(--verdict-color);
            background: var(--verdict-bg);
            border: 1.5px solid var(--verdict-border);
        }}
        .meta-metric {{
            display: flex;
            flex-direction: column;
        }}
        .meta-metric-label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            font-weight: 600;
        }}
        .meta-metric-val {{
            font-size: 1.15rem;
            font-weight: 700;
            color: #fff;
        }}
        .reasoning-box {{
            line-height: 1.7;
            font-size: 1.05rem;
            color: #e2e8f0;
            margin-bottom: 24px;
            padding-left: 16px;
            border-left: 3px solid var(--accent);
        }}
        .share-bar {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
        }}
        .evidence-section {{
            margin-top: 32px;
        }}
        .evidence-heading {{
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .evidence-card {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 14px;
        }}
        .evidence-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .evidence-source-tag {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            background: rgba(56, 189, 248, 0.12);
            color: var(--accent);
        }}
        .evidence-link {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-decoration: none;
        }}
        .evidence-link:hover {{
            color: #fff;
            text-decoration: underline;
        }}
        .evidence-text {{
            font-size: 0.95rem;
            color: #cbd5e1;
            line-height: 1.5;
        }}
        footer {{
            margin-top: 40px;
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <a href="/" class="brand">
                <svg viewBox="0 0 56 64" fill="none">
                    <path d="M28 4L6 14V30C6 44 15 56 28 60C41 56 50 44 50 30V14L28 4Z" fill="#38bdf8"/>
                    <path d="M22 30L26 34L34 24" stroke="#ffffff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <div class="brand-title">FactGuard<span>.AI</span></div>
            </a>
            <div class="header-actions">
                <a href="/" class="btn btn-primary">Verify Another Statement</a>
                <a href="{github_repo}" target="_blank" rel="noopener noreferrer" class="btn btn-outline">&#9733; Star on GitHub</a>
            </div>
        </header>

        <main class="verdict-hero">
            <div class="claim-label">Verified Statement</div>
            <h1 class="claim-title">"{claim}"</h1>

            <div class="verdict-status-row">
                <div class="verdict-badge">{verdict}</div>
                <div class="meta-metric">
                    <span class="meta-metric-label">Confidence</span>
                    <span class="meta-metric-val">{conf_pct}%</span>
                </div>
                <div class="meta-metric">
                    <span class="meta-metric-label">AI Engine</span>
                    <span class="meta-metric-val">{provider_name} ({model_name})</span>
                </div>
                <div class="meta-metric">
                    <span class="meta-metric-label">Execution Time</span>
                    <span class="meta-metric-val">{total_time}</span>
                </div>
            </div>

            <div class="claim-label">Verification Reasoning</div>
            <p class="reasoning-box">{reasoning}</p>

            <div class="share-bar">
                <span style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary);">Share this result:</span>
                <a href="{tweet_intent}" target="_blank" rel="noopener noreferrer" class="btn btn-outline">Share on Twitter / X</a>
                <a href="{reddit_intent}" target="_blank" rel="noopener noreferrer" class="btn btn-outline">Share on Reddit</a>
                <button onclick="navigator.clipboard.writeText(window.location.href); alert('Permalink copied to clipboard!');" class="btn btn-outline">Copy Link</button>
            </div>
        </main>

        <section class="evidence-section">
            <h2 class="evidence-heading">
                <span>Verified Web Evidence &amp; Citations ({len(evidence_items)})</span>
            </h2>
            {evidence_cards_html if evidence_cards_html else '<p style="color: var(--text-secondary);">No web evidence records available.</p>'}
        </section>

        <footer>
            <p>FactGuard AI &bull; Open-Source Real-Time Automated Fact-Checking</p>
            <p style="margin-top: 6px;"><a href="{github_repo}" target="_blank" rel="noopener noreferrer" style="color: var(--accent); text-decoration: none;">View source code &amp; contribute on GitHub</a></p>
        </footer>
    </div>
</body>
</html>"""
