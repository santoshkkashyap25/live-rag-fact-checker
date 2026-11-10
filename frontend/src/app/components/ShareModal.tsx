"use client";

import React, { useState } from "react";
import { X, Share2, Copy, Check, MessageSquare, ExternalLink, ShieldCheck } from "lucide-react";
import styles from "./ShareModal.module.css";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  shareUrl: string;
  claim: string;
  verdict: string;
  confidence: string | number;
}

export default function ShareModal({ isOpen, onClose, shareUrl, claim, verdict, confidence }: Props) {
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedBadge, setCopiedBadge] = useState(false);

  if (!isOpen) return null;

  const confStr = typeof confidence === "number" ? `${Math.round(confidence * 100)}%` : confidence;
  const tweetText = encodeURIComponent(
    `Fact-checked with @FactGuard: "${claim.slice(0, 80)}" is ${verdict} (${confStr} confidence).\n\nLive citations & RAG breakdown: ${shareUrl}\n\n#FactGuard #AI #RAG #OpenSource`
  );
  const twitterShareUrl = `https://twitter.com/intent/tweet?text=${tweetText}`;
  const redditShareUrl = `https://reddit.com/submit?url=${encodeURIComponent(shareUrl)}&title=${encodeURIComponent(`FactGuard: ${verdict} - ${claim.slice(0, 80)}`)}`;
  const linkedInShareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;

  const badgeColor = verdict === "True" ? "22c55e" : verdict === "False" ? "ef4444" : "f59e0b";
  const markdownBadge = `[![FactGuard: ${verdict}](https://img.shields.io/badge/FactGuard-${verdict}-${badgeColor})](${shareUrl})`;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  const handleCopyBadge = () => {
    navigator.clipboard.writeText(markdownBadge);
    setCopiedBadge(true);
    setTimeout(() => setCopiedBadge(false), 2000);
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.titleArea}>
            <Share2 size={20} className={styles.headerIcon} />
            <h2 className={styles.headerTitle}>Share Fact-Checked Result</h2>
          </div>
          <button onClick={onClose} className={styles.closeBtn} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.previewSnippet}>
            <div className={styles.previewLabel}>Verified Claim &bull; {verdict}</div>
            <div className={styles.previewClaim}>"{claim}"</div>
          </div>

          <div>
            <label className={styles.sectionLabel}>Direct Permalink</label>
            <div className={styles.urlInputRow}>
              <input
                type="text"
                readOnly
                value={shareUrl}
                className={styles.urlInput}
                onClick={(e) => (e.target as HTMLInputElement).select()}
              />
              <button
                onClick={handleCopyLink}
                className={`${styles.copyBtn} ${copiedLink ? styles.copyBtnSuccess : ""}`}
              >
                {copiedLink ? <Check size={16} /> : <Copy size={16} />}
                <span>{copiedLink ? "Copied!" : "Copy"}</span>
              </button>
            </div>
          </div>

          <div>
            <label className={styles.sectionLabel}>Social Media One-Click Share</label>
            <div className={styles.socialRow}>
              <a
                href={twitterShareUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.socialBtn}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" color="#38bdf8">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                <span>Twitter / X</span>
              </a>
              <a
                href={redditShareUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.socialBtn}
              >
                <MessageSquare size={18} color="#f97316" />
                <span>Reddit</span>
              </a>
              <a
                href={linkedInShareUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.socialBtn}
              >
                <ExternalLink size={18} color="#818cf8" />
                <span>LinkedIn</span>
              </a>
            </div>
          </div>

          <div>
            <label className={styles.sectionLabel}>Embed Markdown / GitHub Badge</label>
            <div className={styles.badgeCopyArea}>
              <code>{markdownBadge.slice(0, 42)}...</code>
              <button onClick={handleCopyBadge} className={styles.badgeCopyBtn}>
                {copiedBadge ? "Copied!" : "Copy Markdown"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
