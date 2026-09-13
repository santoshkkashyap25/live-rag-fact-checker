"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Eye,
  EyeOff,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Cpu,
  Save,
  RotateCcw
} from "lucide-react";
import styles from "./LLMSettingsModal.module.css";

export type LLMProviderType = "groq" | "openai" | "gemini" | "claude";

export interface LLMConfig {
  provider: LLMProviderType;
  apiKey: string;
  model: string;
  isCustomKey: boolean;
}

interface ProviderMeta {
  id: LLMProviderType;
  name: string;
  desc: string;
  keyUrl: string;
  keyPlaceholder: string;
  defaultModel: string;
  models: Array<{ id: string; label: string }>;
}

const PROVIDERS: ProviderMeta[] = [
  {
    id: "groq",
    name: "Groq",
    desc: "Ultra-fast LPU inference (GPT-OSS, Compound, Llama)",
    keyUrl: "https://console.groq.com/keys",
    keyPlaceholder: "gsk_...",
    defaultModel: "groq/compound-mini",
    models: [
      { id: "groq/compound-mini", label: "Compound Mini (High Precision • Server Default)" },
      { id: "openai/gpt-oss-20b", label: "GPT-OSS 20B (Fast Reasoning)" },
      { id: "openai/gpt-oss-120b", label: "GPT-OSS 120B (High Capacity)" },
      { id: "qwen/qwen3.6-27b", label: "Qwen 3.6 27B" },
    ]
  },
  {
    id: "openai",
    name: "OpenAI",
    desc: "GPT-4o & GPT-4o-mini reasoning",
    keyUrl: "https://platform.openai.com/api-keys",
    keyPlaceholder: "sk-proj-...",
    defaultModel: "gpt-4o-mini",
    models: [
      { id: "gpt-4o-mini", label: "GPT-4o Mini (Fast & Cost-Efficient)" },
      { id: "gpt-4o", label: "GPT-4o (Flagship Model)" },
      { id: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
    ]
  },
  {
    id: "gemini",
    name: "Google Gemini",
    desc: "Gemini 1.5 & 2.0 Flash multimodal",
    keyUrl: "https://aistudio.google.com/app/apikey",
    keyPlaceholder: "AIzaSy...",
    defaultModel: "gemini-1.5-flash",
    models: [
      { id: "gemini-1.5-flash", label: "Gemini 1.5 Flash (Fast & Capable)" },
      { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash (Next-Gen)" },
      { id: "gemini-1.5-pro", label: "Gemini 1.5 Pro (Deep Analysis)" },
    ]
  },
  {
    id: "claude",
    name: "Anthropic Claude",
    desc: "Claude 3.5 Sonnet & Haiku precision",
    keyUrl: "https://console.anthropic.com/settings/keys",
    keyPlaceholder: "sk-ant-api03-...",
    defaultModel: "claude-3-5-haiku-20241022",
    models: [
      { id: "claude-3-5-haiku-20241022", label: "Claude 3.5 Haiku (Fast & Precise)" },
      { id: "claude-3-5-sonnet-20241022", label: "Claude 3.5 Sonnet (State of the Art)" },
      { id: "claude-3-haiku-20240307", label: "Claude 3 Haiku" },
    ]
  }
];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  currentConfig: LLMConfig;
  onSave: (config: LLMConfig) => void;
}

export default function LLMSettingsModal({ isOpen, onClose, currentConfig, onSave }: Props) {
  const [provider, setProvider] = useState<LLMProviderType>(currentConfig.provider);
  const [apiKey, setApiKey] = useState(currentConfig.apiKey);
  const [selectedModel, setSelectedModel] = useState(currentConfig.model);
  const [customModel, setCustomModel] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Sync state when modal opens
  useEffect(() => {
    if (isOpen) {
      setProvider(currentConfig.provider);
      setApiKey(currentConfig.apiKey);
      setSelectedModel(currentConfig.model);
      setShowKey(false);
      setTestResult(null);
    }
  }, [isOpen, currentConfig]);

  if (!isOpen) return null;

  const activeProviderMeta = PROVIDERS.find((p) => p.id === provider) || PROVIDERS[0];
  const isCustomModelChosen = selectedModel === "custom";

  const handleProviderSelect = (newProvider: LLMProviderType) => {
    setProvider(newProvider);
    const meta = PROVIDERS.find((p) => p.id === newProvider);
    if (meta) {
      setSelectedModel(meta.defaultModel);
    }
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    if (!apiKey.trim()) {
      setTestResult({ success: false, message: "Please enter an API key to test." });
      return;
    }

    const effectiveModel = isCustomModelChosen ? customModel : selectedModel;
    setTesting(true);
    setTestResult(null);

    try {
      const res = await fetch("/api/llm/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider,
          api_key: apiKey.trim(),
          model: effectiveModel || undefined
        })
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.message || data.detail || "Connection test failed.");
      }

      setTestResult({ success: true, message: data.message || "Connected successfully!" });
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || "Failed to connect." });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    const effectiveModel = isCustomModelChosen ? customModel.trim() : selectedModel;
    const isCustomKey = apiKey.trim().length > 0;
    
    onSave({
      provider,
      apiKey: apiKey.trim(),
      model: effectiveModel || activeProviderMeta.defaultModel,
      isCustomKey
    });
    onClose();
  };

  const handleReset = () => {
    if (confirm("Reset to server default Groq model? Your custom keys will be removed from your browser.")) {
      const defaultConfig: LLMConfig = {
        provider: "groq",
        apiKey: "",
        model: "groq/compound-mini",
        isCustomKey: false
      };
      onSave(defaultConfig);
      onClose();
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.titleArea}>
            <Cpu size={20} className={styles.headerIcon} />
            <h2 className={styles.headerTitle}>LLM Engine & API Settings</h2>
          </div>
          <button onClick={onClose} className={styles.closeBtn} title="Close">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className={styles.body}>
          {/* Privacy Banner */}
          <div className={styles.privacyNotice}>
            <ShieldCheck size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
            <span>
              <strong>Zero-Storage BYOK:</strong> Your API keys are encrypted in your browser's local memory and sent over secure HTTPS directly for evaluation. They are never stored on our database.
            </span>
          </div>

          {/* Provider Selection */}
          <div>
            <label className={styles.sectionLabel}>Select Verification Provider</label>
            <div className={styles.providerGrid}>
              {PROVIDERS.map((p) => {
                const isActive = p.id === provider;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handleProviderSelect(p.id)}
                    className={`${styles.providerCard} ${isActive ? styles.providerCardActive : ""}`}
                  >
                    <div className={styles.providerTop}>
                      <span className={styles.providerName}>{p.name}</span>
                      {isActive && <span className={styles.providerActiveDot} />}
                    </div>
                    <span className={styles.providerDesc}>{p.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* API Key Input */}
          <div className={styles.fieldGroup}>
            <div className={styles.fieldHeader}>
              <label className={styles.sectionLabel} style={{ marginBottom: 0 }}>
                {activeProviderMeta.name} API Key
              </label>
              <a
                href={activeProviderMeta.keyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.keyLink}
              >
                <span>Get key on {activeProviderMeta.name}</span>
                <ExternalLink size={12} />
              </a>
            </div>

            <div className={styles.inputWrapper}>
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setTestResult(null);
                }}
                placeholder={activeProviderMeta.keyPlaceholder}
                className={styles.textInput}
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className={styles.inputIconBtn}
                title={showKey ? "Hide key" : "Show key"}
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Model Selection */}
          <div className={styles.fieldGroup}>
            <label className={styles.sectionLabel}>Model Selection</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className={styles.selectInput}
            >
              {activeProviderMeta.models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label} ({m.id})
                </option>
              ))}
              <option value="custom">Custom Model Name...</option>
            </select>

            {isCustomModelChosen && (
              <input
                type="text"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                placeholder="e.g. gpt-4o-2024-08-06 or llama-3.2-3b-preview"
                className={styles.textInput}
                style={{ marginTop: "0.5rem" }}
              />
            )}
          </div>

          {/* Test Connection Row */}
          <div className={styles.testRow}>
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing || !apiKey.trim()}
              className={styles.testBtn}
            >
              <RefreshCw size={14} className={testing ? styles.spin : ""} />
              <span>{testing ? "Testing..." : "Test Connection"}</span>
            </button>

            {testResult && (
              <div className={`${styles.testResult} ${testResult.success ? styles.testSuccess : styles.testError}`}>
                {testResult.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                <span>{testResult.message}</span>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <button
            type="button"
            onClick={handleReset}
            className={styles.resetBtn}
            title="Clear custom keys and return to server default Groq"
          >
            <RotateCcw size={14} style={{ display: "inline", marginRight: "4px" }} />
            Reset to Default
          </button>

          <div className={styles.actionRight}>
            <button type="button" onClick={onClose} className={styles.cancelBtn}>
              Cancel
            </button>
            <button type="button" onClick={handleSave} className={styles.saveBtn}>
              <Save size={15} />
              <span>Save & Apply</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
