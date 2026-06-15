"use client";

import React, { useState, useEffect } from "react";
import {
  OpenAILogo,
  GeminiLogo,
  PerplexityLogo,
  ClaudeLogo,
  GrokLogo,
  GroqLogo,
  DeepSeekLogo,
} from "@/components/EngineLogos";
import {
  Activity,
  AlertTriangle,
  Award,
  BookOpen,
  ChevronRight,
  Clipboard,
  Cpu,
  Database,
  ExternalLink,
  FileText,
  Key,
  Layers,
  ListFilter,
  Loader2,
  MapPin,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Sparkles,
  TrendingUp,
  User,
  Users,
  Check,
  TrendingDown,
  Target,
  Volume2
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import LiveTrackingConsole from "../components/LiveTrackingConsole";

// Configured local storage keys
const LOCAL_STORAGE_KEY = "grayn_aeo_config";

interface Config {
  backendUrl: string;
  apiKey: string;
}

const TerminalScanner = ({ onComplete, domain }: { onComplete: () => void, domain: string }) => {
  const [messages, setMessages] = useState<string[]>([]);
  
  useEffect(() => {
    const sequence = [
      `Establishing connection to ${domain || 'target'}...`,
      "Scraping site metadata and topic clusters...",
      "Extracting brand entity graph...",
      "Identifying key industry competitors...",
      "Querying search volumes...",
      "Analysis complete."
    ];
    let i = 0;
    const interval = setInterval(() => {
      setMessages(prev => [...prev, sequence[i]]);
      i++;
      if (i === sequence.length) {
        clearInterval(interval);
        setTimeout(onComplete, 800);
      }
    }, 600);
    return () => clearInterval(interval);
  }, [domain, onComplete]);

  return (
    <div className="w-full max-w-2xl mx-auto bg-black border border-zinc-800 rounded-xl p-6 font-mono text-sm shadow-2xl">
      <div className="flex items-center gap-2 mb-4 border-b border-zinc-800 pb-4">
        <div className="h-3 w-3 rounded-full bg-red-500" />
        <div className="h-3 w-3 rounded-full bg-yellow-500" />
        <div className="h-3 w-3 rounded-full bg-green-500" />
        <span className="ml-4 text-zinc-500 text-xs">Terminal — AEO Discovery</span>
      </div>
      <div className="space-y-2 h-48 overflow-y-auto flex flex-col justify-end text-left">
        {messages.map((msg, idx) => (
          <div key={idx} className="text-emerald-400">
            <span className="text-zinc-600 mr-2">{'>'}</span> {msg}
          </div>
        ))}
        {messages.length < 6 && (
          <div className="text-emerald-400 animate-pulse flex items-center">
            <span className="text-zinc-600 mr-2">{'>'}</span> <span className="inline-block w-2 h-4 bg-emerald-400 ml-1" />
          </div>
        )}
      </div>
    </div>
  );
};

const EnginePinger = ({ engines, onComplete }: { engines: string[], onComplete: () => void }) => {
  const [completed, setCompleted] = useState<string[]>([]);
  
  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      if (i < engines.length) {
        setCompleted(prev => [...prev, engines[i]]);
        i++;
      } else {
        clearInterval(interval);
        setTimeout(onComplete, 1000);
      }
    }, 800);
    return () => clearInterval(interval);
  }, [engines, onComplete]);

  return (
    <div className="space-y-4 max-w-md mx-auto text-left bg-zinc-900/50 p-6 rounded-xl border border-zinc-800">
      <h3 className="text-white font-semibold mb-4 border-b border-zinc-800 pb-2 flex items-center gap-2">
        <Activity className="h-4 w-4 text-emerald-400" /> Initializing Engines
      </h3>
      {engines.map((eng) => {
        const isDone = completed.includes(eng);
        return (
          <div key={eng} className="flex items-center gap-3">
            {isDone ? (
              <Check className="h-5 w-5 text-emerald-400" />
            ) : (
              <Loader2 className="h-5 w-5 text-purple-400 animate-spin" />
            )}
            <span className={isDone ? "text-zinc-300" : "text-zinc-500 animate-pulse capitalize"}>
              {isDone ? `Tracking configured for ${eng}` : `Pinging ${eng}...`}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export default function Home() {
  // ── States ──────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"dashboard" | "workstreams" | "clusters" | "prompts" | "competitors" | "settings">("dashboard");
  const [config, setConfig] = useState<Config>({
    backendUrl: process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? `http://${window.location.hostname}:8000` : "http://localhost:8000"),
    apiKey: "gk_devprefix_devsecretkey123456789", // Dev API key seeded in DB
  });
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Core Data States
  const [workspace, setWorkspace] = useState<any>(null);
  const [report, setReport] = useState<any>({});
  const [prompts, setPrompts] = useState<any[]>([]);
  const [workstreams, setWorkstreams] = useState<any[]>([]);
  const [clusters, setClusters] = useState<any[]>([]);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [compSources, setCompSources] = useState<Record<string, any[]>>({});
  
  // Interactive UI States
  const [selectedCluster, setSelectedCluster] = useState<any>(null);
  const [brief, setBrief] = useState<any>(null);
  const [draft, setDraft] = useState<any>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const [copiedText, setCopiedText] = useState(false);

  // Prompt creation states
  const [newPromptText, setNewPromptText] = useState("");
  const [newPromptCluster, setNewPromptCluster] = useState("");
  const [newPromptIntent, setNewPromptIntent] = useState("informational");
  const [newPromptPersona, setNewPromptPersona] = useState("developer");
  const [bulkPromptsText, setBulkPromptsText] = useState("");
  const [promptSubmitLoading, setPromptSubmitLoading] = useState(false);

  // Manual trigger states
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [triggerStatus, setTriggerStatus] = useState<string | null>(null);
  const [isLiveTracking, setIsLiveTracking] = useState(false);

  // Onboarding states
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [discoverUrl, setDiscoverUrl] = useState("");
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverResult, setDiscoverResult] = useState<any>(null);
  const [onboardLoading, setOnboardLoading] = useState(false);
  const [onboardingStep, setOnboardingStep] = useState(1);
  const [selectedEngines, setSelectedEngines] = useState<string[]>(["openai", "gemini"]);
  const [numQueries, setNumQueries] = useState(10);

  // Remove fallback mode flag completely

  // ── Load Config on Mount ──────────────────────────────────────────
  useEffect(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Automatically fix localhost references if accessed via LAN IP
        if (typeof window !== "undefined" && window.location.hostname !== "localhost" && parsed.backendUrl.includes("localhost")) {
          parsed.backendUrl = parsed.backendUrl.replace("localhost", window.location.hostname);
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(parsed));
        }
        // Fallback to dev key unconditionally to avoid broken localStorage
        parsed.apiKey = "gk_devprefix_devsecretkey123456789";
        setConfig(parsed);
      } catch (e) {
        // ignore parse error
      }
    }
  }, []);

  // ── Helper to normalize Backend URL ───────────────────────────────
  const getApiUrl = (path: string) => {
    // Hardcoding to bypass any corrupted localStorage values or Vercel env cache issues
    if (typeof window !== "undefined" && window.location.hostname.includes("vercel.app")) {
      return `https://grayn-aeo-production.up.railway.app${path}`;
    }
    let base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return `${base}${path}`;
  };

  // ── Fetch Data ────────────────────────────────────────────────────
  const fetchData = async (currentConfig: Config) => {
    setLoading(true);
    setError(null);

    try {
      const headers = {
        "Authorization": `Bearer ${currentConfig.apiKey}`,
        "Content-Type": "application/json",
      };

      // Stagger data loading to prevent connection pool exhaustion on the backend
      const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
      
      const wsRes = await fetch(getApiUrl("/v1/me"), { headers, cache: "no-store" }).then(r => { if (!r.ok) throw new Error("Auth failed"); return r.json(); });
      
      const [reportRes, promptsRes, clustersRes, competitorsRes, compSourcesRes, workstreamsRes] = await Promise.all([
        delay(100).then(() => fetch(getApiUrl("/v1/report"), { headers, cache: "no-store" })).then(r => r.ok ? r.json() : {}).catch(() => ({})),
        delay(200).then(() => fetch(getApiUrl("/v1/prompts"), { headers, cache: "no-store" })).then(r => r.ok ? r.json() : []).catch(() => []),
        delay(300).then(() => fetch(getApiUrl("/v1/clusters"), { headers, cache: "no-store" })).then(r => r.ok ? r.json() : []).catch(() => []),
        delay(400).then(() => fetch(getApiUrl("/v1/competitors"), { headers, cache: "no-store" })).then(r => r.ok ? r.json() : []).catch(() => []),
        delay(500).then(() => fetch(getApiUrl("/v1/competitors/sources"), { headers, cache: "no-store" })).then(r => r.ok ? r.json() : {}).catch(() => ({})),
        delay(600).then(() => fetch(getApiUrl("/v1/workstreams"), { headers, cache: "no-store" })).then(r => r.ok ? r.json() : []).catch(() => [])
      ]);

      setWorkspace(wsRes);
      setReport(reportRes);
      setPrompts(promptsRes);
      setClusters(clustersRes);
      setCompetitors(competitorsRes);
      setCompSources(compSourcesRes);
      setWorkstreams(workstreamsRes);
      
      if (!wsRes || !wsRes.id) {
        setIsOnboarding(true);
      } else if (wsRes.brand_name) {
        setIsOnboarding(false);
      }
      
    } catch (err: any) {
      console.warn("FastAPI backend error. Switching to onboarding mode.", err.message);
      setIsOnboarding(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(config);
  }, [config]);

  // ── Discovery & Onboarding ───────────────────────────────────────
  const handleDiscover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!discoverUrl.trim()) return;
    setDiscoverLoading(true);
    setOnboardingStep(2); // Start scanning immediately

    try {
      const urlToFetch = getApiUrl("/v1/discover");
      console.log("Fetching Discovery URL:", urlToFetch);
      
      const res = await fetch(urlToFetch, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: discoverUrl, num_queries: numQueries })
      });
      
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Failed to discover: ${res.status} ${errText}`);
      }
      const data = await res.json();
      setDiscoverResult(data);
      // We don't advance to step 3 here; the TerminalScanner's onComplete handles that.
    } catch (err) {
      console.error(err);
      setOnboardingStep(1); // Go back on error
    } finally {
      setDiscoverLoading(false);
    }
  };

  const applyOnboarding = async () => {
    setOnboardingStep(5); // Show EnginePinger immediately
    setOnboardLoading(true);
    console.log("DEBUG applyOnboarding - current config:", config);
    try {
      const headers = {
        "Authorization": `Bearer ${config.apiKey}`,
        "Content-Type": "application/json"
      };
      
      const payload = {
        competitors: [
          { brand_name: discoverResult?.brand_name || "Brand", domain: discoverUrl || "", aliases: [] },
          ...(discoverResult?.suggested_competitors || [])
        ],
        queries: discoverResult?.suggested_queries || [],
        engines: selectedEngines
      };

      const res = await fetch(getApiUrl("/v1/workspaces/onboard"), {
        method: "POST",
        headers,
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Failed to onboard: ${res.status} ${errText}`);
      }

      // Step 6 will render LiveTrackingConsole to monitor the background run
      setOnboardingStep(6);
    } catch (err: any) {
      console.error(err);
      alert(err.message); // Simple alert to inform the user of what went wrong
      setOnboardingStep(4); // fallback on error to Review stage
    } finally {
      setOnboardLoading(false);
    }
  };

  // ── Fetch Content Brief ──────────────────────────────────────────
  const fetchBrief = async (cluster: any) => {
    setSelectedCluster(cluster);
    setBriefLoading(true);
    setBrief(null);
    setDraft(null);

    try {
      if (!selectedCluster) {
        // Just fail silently or show error
        setBriefLoading(false);
        return;
      }
      const headers = { "Authorization": `Bearer ${config.apiKey}` };
      const res = await fetch(getApiUrl(`/v1/clusters/${cluster.id}/brief`), { headers });
      const data = await res.json();
      setBrief(data);
    } catch (err) {
      console.error(err);
    } finally {
      setBriefLoading(false);
    }
  };

  // ── Generate Content Draft ────────────────────────────────────────
  const fetchDraft = async () => {
    if (!selectedCluster) return;
    setDraftLoading(true);
    setDraft(null);

    try {
      const headers = { "Authorization": `Bearer ${config.apiKey}` };
      const res = await fetch(getApiUrl(`/v1/clusters/${selectedCluster.id}/draft`), {
        method: "POST",
        headers
      });
      const data = await res.json();
      setDraft(data);
    } catch (err) {
      console.error(err);
    } finally {
      setDraftLoading(false);
    }
  };

  // ── Trigger Manual Tracking Run ─────────────────────────────────
  const triggerBatch = async () => {
    setTriggerLoading(true);
    setTriggerStatus(null);
    try {
      const headers = {
        "Authorization": `Bearer ${config.apiKey}`,
        "Content-Type": "application/json"
      };
      const res = await fetch(getApiUrl("/v1/runs/trigger"), {
        method: "POST",
        headers,
        body: JSON.stringify({ engines: selectedEngines, prompt_ids: null })
      });
      const data = await res.json();
      setTriggerStatus(`Batch run started!`);
      setIsLiveTracking(true);
    } catch (err: any) {
      setTriggerStatus(`Error triggering runs: ${err.message}`);
    } finally {
      setTriggerLoading(false);
    }
  };

  // ── Add New Prompt ────────────────────────────────────────────────
  const addPrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPromptText.trim()) return;
    setPromptSubmitLoading(true);

    try {
      const payload = {
        prompt_text: newPromptText,
        intent: newPromptIntent,
        persona: newPromptPersona,
        topic_cluster: newPromptCluster || "General"
      };

      const headers = {
        "Authorization": `Bearer ${config.apiKey}`,
        "Content-Type": "application/json"
      };
      const res = await fetch(getApiUrl("/v1/prompts"), {
        method: "POST",
        headers,
        body: JSON.stringify(payload)
      });
      const added = await res.json();
      setPrompts([added, ...prompts]);
      setNewPromptText("");
    } catch (err) {
      console.error(err);
    } finally {
      setPromptSubmitLoading(false);
    }
  };

  // ── Bulk Add Prompts ──────────────────────────────────────────────
  const addBulkPrompts = async (e: React.FormEvent) => {
    e.preventDefault();
    const lines = bulkPromptsText.split("\n").map(l => l.trim()).filter(Boolean);
    if (lines.length === 0) return;
    setPromptSubmitLoading(true);

    try {
      const list = lines.map(line => ({
        prompt_text: line,
        intent: "informational",
        persona: "developer",
        topic_cluster: "Bulk Upload"
      }));

      const headers = {
        "Authorization": `Bearer ${config.apiKey}`,
        "Content-Type": "application/json"
      };
      const res = await fetch(getApiUrl("/v1/prompts/bulk"), {
        method: "POST",
        headers,
        body: JSON.stringify({ prompts: list })
      });
      const addedList = await res.json();
      setPrompts([...addedList, ...prompts]);
      setBulkPromptsText("");
    } catch (err) {
      console.error(err);
    } finally {
      setPromptSubmitLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  const saveConfig = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const backendUrl = data.get("backendUrl") as string;
    const apiKey = data.get("apiKey") as string;

    const newConfig = { backendUrl, apiKey };
    setConfig(newConfig);
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(newConfig));
    setShowConfigModal(false);
  };

  // ── Render Helpers ────────────────────────────────────────────────
  if (loading && !isOnboarding) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center bg-zinc-950 text-zinc-100 font-sans">
        <Loader2 className="h-10 w-10 animate-spin text-purple-500 mb-4" />
        <p className="text-zinc-400 text-sm animate-pulse">Initializing Grayn visibility pipeline...</p>
      </div>
    );
  }

  const AVAILABLE_ENGINES = [
    { id: "openai", name: "ChatGPT", icon: <OpenAILogo className="h-5 w-5" />, color: "from-emerald-400 to-emerald-600", bg: "bg-emerald-500/10", border: "border-emerald-500/30" },
    { id: "gemini", name: "Gemini", icon: <GeminiLogo className="h-5 w-5" />, color: "from-blue-400 to-indigo-600", bg: "bg-blue-500/10", border: "border-blue-500/30" },
    { id: "perplexity", name: "Perplexity", icon: <PerplexityLogo className="h-5 w-5" />, color: "from-cyan-400 to-blue-500", bg: "bg-cyan-500/10", border: "border-cyan-500/30" },
    { id: "claude", name: "Claude", icon: <ClaudeLogo className="h-5 w-5" />, color: "from-orange-400 to-red-500", bg: "bg-orange-500/10", border: "border-orange-500/30" },
    { id: "grok", name: "Grok", icon: <GrokLogo className="h-5 w-5" />, color: "from-zinc-400 to-zinc-600", bg: "bg-zinc-500/10", border: "border-zinc-500/30" },
    { id: "groq", name: "Groq", icon: <GroqLogo className="h-5 w-5" />, color: "from-rose-400 to-rose-600", bg: "bg-rose-500/10", border: "border-rose-500/30" },
    { id: "deepseek", name: "DeepSeek", icon: <DeepSeekLogo className="h-5 w-5" />, color: "from-indigo-400 to-purple-600", bg: "bg-indigo-500/10", border: "border-indigo-500/30" },
  ];

  if (isOnboarding) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center bg-[#0a0a0a] text-zinc-100 font-sans relative overflow-hidden">
        {/* Animated Background */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden">
          <motion.div 
            animate={{ scale: [1, 1.2, 1], opacity: [0.1, 0.2, 0.1] }}
            transition={{ duration: 8, repeat: Infinity }}
            className="absolute h-[600px] w-[600px] bg-purple-600/20 rounded-full blur-[120px] top-[-20%] left-[-10%]" 
          />
          <motion.div 
            animate={{ scale: [1, 1.5, 1], opacity: [0.1, 0.15, 0.1] }}
            transition={{ duration: 10, repeat: Infinity, delay: 2 }}
            className="absolute h-[500px] w-[500px] bg-blue-600/20 rounded-full blur-[100px] bottom-[-20%] right-[-10%]" 
          />
        </div>

        <div className="z-10 w-full max-w-3xl px-6">
          <AnimatePresence mode="wait">
            {onboardingStep === 1 && (
              <motion.div 
                key="step1"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20, filter: "blur(10px)" }}
                className="w-full"
              >
                <div className="mb-10 text-center">
                  <div className="h-16 w-16 mx-auto rounded-2xl bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center shadow-[0_0_40px_rgba(147,51,234,0.3)] mb-6">
                    <Sparkles className="h-8 w-8 text-white" />
                  </div>
                  <h1 className="text-5xl font-extrabold tracking-tight text-white mb-4">Discover AI Visibility</h1>
                  <p className="text-zinc-400 text-xl">Enter your brand's website to automatically map your ecosystem.</p>
                </div>
                <form onSubmit={handleDiscover} className="bg-zinc-900/60 p-3 rounded-2xl border border-zinc-800/80 shadow-2xl backdrop-blur-2xl flex gap-3 group focus-within:border-purple-500/50 focus-within:shadow-[0_0_30px_rgba(147,51,234,0.15)] transition-all">
                  <div className="flex-1 flex items-center px-4 bg-zinc-950/50 rounded-xl border border-transparent group-focus-within:bg-zinc-950 transition-all">
                    <Search className="h-6 w-6 text-zinc-500 mr-3" />
                    <input
                      type="text"
                      placeholder="https://stripe.com"
                      value={discoverUrl}
                      onChange={(e) => setDiscoverUrl(e.target.value)}
                      className="w-full bg-transparent border-none py-5 text-xl focus:outline-none text-white placeholder-zinc-700"
                    />
                    <div className="flex items-center gap-2 border-l border-zinc-800 pl-4 ml-2">
                      <span className="text-xs text-zinc-500 font-semibold whitespace-nowrap">Queries:</span>
                      <input
                        type="number"
                        min={1}
                        max={50}
                        value={numQueries}
                        onChange={(e) => setNumQueries(parseInt(e.target.value) || 10)}
                        className="w-16 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-white text-sm focus:outline-none focus:border-purple-500"
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={discoverLoading || !discoverUrl.trim()}
                    className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold px-10 rounded-xl transition-all disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-purple-500/25"
                  >
                    {discoverLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : <Sparkles className="h-6 w-6" />}
                    Analyze
                  </button>
                </form>
              </motion.div>
            )}

            {onboardingStep === 2 && (
              <motion.div 
                key="step2"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, filter: "blur(10px)" }}
                className="w-full"
              >
                <div className="mb-8 text-center">
                  <h2 className="text-3xl font-bold text-white mb-2">Analyzing Domain</h2>
                  <p className="text-zinc-400 animate-pulse">Running advanced AEO discovery on {discoverUrl}</p>
                </div>
                <TerminalScanner domain={discoverUrl} onComplete={() => setOnboardingStep(3)} />
              </motion.div>
            )}

            {onboardingStep === 3 && (
              <motion.div 
                key="step3"
                initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -20, filter: "blur(10px)" }}
                className="w-full"
              >
                <div className="mb-8 text-center">
                  <h2 className="text-3xl font-bold text-white mb-2">Select Target Engines</h2>
                  <p className="text-zinc-400">Which AI models do you want to track for {discoverUrl}?</p>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-10">
                  {AVAILABLE_ENGINES.map((engine, i) => {
                    const isSelected = selectedEngines.includes(engine.id);
                    return (
                      <motion.button
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.1 }}
                        key={engine.id}
                        onClick={() => {
                          if (isSelected && selectedEngines.length > 1) setSelectedEngines(prev => prev.filter(e => e !== engine.id));
                          else if (!isSelected) setSelectedEngines(prev => [...prev, engine.id]);
                        }}
                        className={`relative p-5 rounded-2xl border flex flex-col items-center justify-center gap-3 transition-all duration-300 overflow-hidden ${isSelected ? `${engine.bg} ${engine.border} shadow-[0_0_20px_rgba(255,255,255,0.05)]` : 'bg-zinc-900/40 border-zinc-800/50 hover:bg-zinc-800/50'}`}
                      >
                        {isSelected && <div className={`absolute top-0 w-full h-1 bg-gradient-to-r ${engine.color}`} />}
                        <div className={`p-3 rounded-xl ${isSelected ? 'bg-zinc-950/50 text-white' : 'bg-zinc-900 text-zinc-500'}`}>
                          {engine.icon}
                        </div>
                        <span className={`font-semibold ${isSelected ? 'text-white' : 'text-zinc-400'}`}>{engine.name}</span>
                        {isSelected && (
                          <div className="absolute top-3 right-3">
                            <Check className="h-4 w-4 text-emerald-400" />
                          </div>
                        )}
                      </motion.button>
                    )
                  })}
                </div>

                <div className="flex justify-center items-center">
                  <button onClick={() => setOnboardingStep(4)} className="bg-white text-black hover:bg-zinc-200 font-semibold px-8 py-4 rounded-xl transition flex items-center gap-2">
                    Review Discoveries <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </motion.div>
            )}

            {onboardingStep === 4 && discoverResult && (
              <motion.div 
                key="step4"
                initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }}
                className="w-full bg-zinc-900/40 p-8 rounded-[2rem] border border-zinc-800/50 backdrop-blur-xl shadow-2xl"
              >
                <div className="text-center space-y-2 mb-8">
                  <h2 className="text-3xl font-bold text-white">Context Discovered</h2>
                  <p className="text-zinc-400">We extracted the top competitors and queries for <strong className="text-white bg-zinc-800 px-2 py-1 rounded-md">{discoverUrl}</strong></p>
                </div>

                <div className="grid grid-cols-2 gap-8 max-h-[50vh] overflow-y-auto pr-4 custom-scrollbar">
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500 flex items-center gap-2">
                      <Users className="h-4 w-4 text-purple-400" /> Competitors
                    </h3>
                    <motion.div 
                      initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}
                      className="space-y-2"
                    >
                      {discoverResult.suggested_competitors?.map((c: any, i: number) => (
                        <motion.div 
                          variants={{ hidden: { opacity: 0, x: -20 }, visible: { opacity: 1, x: 0 } }}
                          key={i} className="px-5 py-3 bg-zinc-950/80 border border-zinc-800/80 rounded-xl text-sm text-zinc-200 shadow-sm flex justify-between items-center group hover:border-purple-500/30 transition-colors"
                        >
                          <span className="font-semibold">{c.brand_name}</span>
                          <span className="text-zinc-600 text-xs">{c.domain}</span>
                        </motion.div>
                      ))}
                    </motion.div>
                  </div>
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500 flex items-center gap-2">
                      <Search className="h-4 w-4 text-blue-400" /> Queries to Track
                    </h3>
                    <motion.div 
                      initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}
                      className="space-y-2"
                    >
                      {discoverResult.suggested_queries?.map((q: any, i: number) => (
                        <motion.div 
                          variants={{ hidden: { opacity: 0, x: 20 }, visible: { opacity: 1, x: 0 } }}
                          key={i} className="px-5 py-3 bg-zinc-950/80 border border-zinc-800/80 rounded-xl text-sm text-zinc-300 shadow-sm flex items-center justify-between group hover:border-blue-500/30 transition-colors" title={q.text}
                        >
                          <span className="truncate">{q.text}</span>
                          <div className="flex gap-2">
                            {q.attributes?.map((attr: string, j: number) => (
                              <span key={j} className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-md text-[10px] font-medium uppercase tracking-wider">
                                {attr}
                              </span>
                            ))}
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  </div>
                </div>

                <div className="pt-8 mt-8 border-t border-zinc-800/50 flex justify-between items-center">
                  <button onClick={() => setOnboardingStep(3)} className="text-zinc-500 hover:text-white font-medium px-4 py-2 transition-colors">Back</button>
                  <button
                    onClick={applyOnboarding}
                    className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white font-semibold px-8 py-4 rounded-xl transition shadow-lg shadow-emerald-500/20 flex items-center gap-2"
                  >
                    <Play className="h-5 w-5 fill-current" /> Initialize Tracking
                  </button>
                </div>
              </motion.div>
            )}

            {onboardingStep === 5 && (
              <motion.div 
                key="step5"
                initial={{ opacity: 0, scale: 0.9, filter: "blur(20px)" }}
                animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                exit={{ opacity: 0, scale: 0.9, filter: "blur(20px)" }}
                className="w-full flex flex-col items-center justify-center text-center py-20"
              >
                <div className="relative mb-8">
                  <div className="absolute inset-0 bg-purple-500 rounded-full blur-[50px] opacity-20 animate-pulse" />
                  <div className="h-24 w-24 bg-zinc-900 border border-zinc-800 rounded-full flex items-center justify-center relative z-10 shadow-2xl">
                    <Activity className="h-10 w-10 text-purple-400 animate-pulse" />
                  </div>
                </div>
                <h2 className="text-3xl font-bold text-white mb-3">Provisioning Workspace</h2>
                <p className="text-zinc-400 text-lg max-w-md mx-auto mb-8">
                  Configuring your brand, competitors, and database tables.
                </p>
                <Loader2 className="h-8 w-8 text-purple-400 animate-spin" />
              </motion.div>
            )}

            {onboardingStep === 6 && (
              <motion.div 
                key="step6"
                initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                className="w-full"
              >
                <LiveTrackingConsole 
                  apiKey={""}
                  backendUrl={getApiUrl("")}
                  enginesCount={selectedEngines.length || 10}
                  onComplete={async () => {
                    setIsOnboarding(false);
                    setDiscoverResult(null);
                    setOnboardingStep(1);
                    await fetchData(config);
                  }}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-zinc-950 text-zinc-100 font-sans overflow-hidden">
      {/* ── SIDEBAR ─────────────────────────────────────────────────── */}
      <aside className="w-64 border-r border-zinc-900 bg-zinc-950 flex flex-col justify-between">
        <div>
          <div className="h-16 flex items-center gap-3 px-6 border-b border-zinc-900 bg-zinc-900/10">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-500/15">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <span className="font-bold tracking-tight text-white block text-sm">GRAYN AEO</span>
              <span className="text-[10px] text-zinc-500 font-medium block uppercase tracking-wider">Answer Engine Optimization</span>
            </div>
          </div>

          <nav className="p-4 space-y-1">
            <button
              onClick={() => setActiveTab("dashboard")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === "dashboard"
                  ? "bg-zinc-900 text-white shadow-inner border border-zinc-800"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900/50"
              }`}
            >
              <Activity className="h-4 w-4" />
              Overview Dashboard
            </button>
            <button
              onClick={() => setActiveTab("workstreams")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === "workstreams"
                  ? "bg-zinc-900 text-white shadow-inner border border-zinc-800"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900/50"
              }`}
            >
              <Target className="h-4 w-4" />
              Workstreams
            </button>
            <button
              onClick={() => setActiveTab("clusters")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === "clusters"
                  ? "bg-zinc-900 text-white shadow-inner border border-zinc-800"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900/50"
              }`}
            >
              <Layers className="h-4 w-4" />
              Content Gaps Studio
            </button>
            <button
              onClick={() => setActiveTab("prompts")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === "prompts"
                  ? "bg-zinc-900 text-white shadow-inner border border-zinc-800"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900/50"
              }`}
            >
              <FileText className="h-4 w-4" />
              Query Manager
            </button>
            <button
              onClick={() => setActiveTab("competitors")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === "competitors"
                  ? "bg-zinc-900 text-white shadow-inner border border-zinc-800"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900/50"
              }`}
            >
              <Users className="h-4 w-4" />
              Competitor Analysis
            </button>
          </nav>
        </div>

        {/* Workspace Profile & Config Footer */}
        <div className="p-4 border-t border-zinc-900 space-y-3 bg-zinc-900/10">
          <div className="flex items-center gap-3 px-2">
            <div className="h-9 w-9 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300">
              <User className="h-4 w-4" />
            </div>
            <div className="overflow-hidden">
              <span className="font-semibold text-sm text-zinc-200 block truncate">{workspace?.brand_name || "Guest Brand"}</span>
              <span className="text-[11px] text-zinc-500 block truncate">{workspace?.domain || "no-domain.com"}</span>
            </div>
          </div>
          
          {error && (
            <div className="px-2 py-1.5 rounded bg-rose-500/10 border border-rose-500/20 text-[10px] text-rose-400 leading-tight">
              ⚠️ {error}
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => {
                setIsOnboarding(true);
                setOnboardingStep(1);
                setDiscoverUrl("");
                setDiscoverResult(null);
              }}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-800 hover:border-zinc-700 bg-zinc-900 text-[11px] font-semibold transition duration-150"
            >
              <Search className="h-3 w-3" />
              New Search
            </button>
            <button
              onClick={() => fetchData(config)}
              className="px-2.5 py-1.5 rounded-lg border border-zinc-800 hover:border-zinc-700 bg-zinc-900 text-zinc-400 hover:text-white transition duration-150"
              title="Sync Database"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT AREA ───────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
        
        {/* Top Header */}
        <header className="h-16 border-b border-zinc-900 px-8 flex items-center justify-between bg-zinc-900/10 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-white tracking-tight">
              {activeTab === "dashboard" && "Workspace Summary"}
              {activeTab === "workstreams" && "Workstreams"}
              {activeTab === "clusters" && "Topic Cluster & Opportunity Index"}
              {activeTab === "prompts" && "AEO Tracking Query Manager"}
              {activeTab === "competitors" && "Competitor & citation Intel"}
              {activeTab === "settings" && "Workspace Settings"}
            </h2>
            <div className={`h-2 w-2 rounded-full bg-emerald-500 animate-pulse`} />
            <span className="text-xs text-zinc-500 font-semibold uppercase tracking-wider">
              Live Data
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="px-3 py-1 rounded-full border border-purple-500/20 bg-purple-500/5 text-purple-400 text-xs font-semibold">
              Current Period: {report?.iso_week || "2026-W23"}
            </div>
            <button
              onClick={triggerBatch}
              disabled={triggerLoading}
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-purple-600/20 transition-all duration-150 disabled:opacity-50"
            >
              {triggerLoading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Play className="h-3 w-3" />
              )}
              Trigger Tracking Run
            </button>
          </div>
        </header>

        {/* Content Scrolling Container */}
        <div className="flex-1 overflow-y-auto p-8 space-y-8">
          
          {triggerStatus && (
            <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs flex justify-between items-center">
              <span>{triggerStatus}</span>
              <button onClick={() => setTriggerStatus(null)} className="text-purple-400 hover:text-white font-semibold">Dismiss</button>
            </div>
          )}

          {/* ────────────────────────────────────────────────────────
              TAB: OVERVIEW DASHBOARD
             ──────────────────────────────────────────────────────── */}
          {activeTab === "dashboard" && report ? (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, staggerChildren: 0.1 }}
              className="space-y-8"
            >
              <div className="p-6 rounded-2xl border border-purple-500/20 bg-purple-500/5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                    Latest AI Insight
                  </h3>
                  <span className="text-[10px] text-purple-400 font-bold uppercase tracking-wider px-2 py-1 bg-purple-500/10 rounded">Auto-Generated</span>
                </div>
                <div className="text-zinc-300 text-sm leading-relaxed">
                  {report.leaderboard?.length > 0 ? (
                    <>
                      <span className="font-bold text-white capitalize">{report.workspace?.brand_name}</span> has <span className="font-bold text-emerald-400">{report.visibility?.visibility_pct}% visibility</span> across recent queries.
                      You are maintaining strong positioning for <strong>{report.topic_performance?.[0]?.topic || 'core features'}</strong>,
                      but <strong>{report.platform_scorecard?.[0]?.top_competitor || 'competitors'}</strong> is capturing share in <strong>{report.platform_scorecard?.[0]?.platform || 'certain engines'}</strong>.
                      Immediately focus on publishing comparison content highlighting your positive attributes ({report.attribute_breakdown?.slice(0, 2).map((a: any) => a.attribute).join(', ') || 'key features'}) to regain momentum and close the gap.
                    </>
                  ) : report.recent_runs?.some((r: any) => r.status === 'error') ? (
                    <div className="flex items-start gap-2 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg">
                      <AlertTriangle className="h-5 w-5 text-rose-400 mt-0.5 shrink-0" />
                      <div className="text-rose-200/80 text-sm">
                        Tracking failed due to AI API errors. <br/>
                        <span className="font-mono text-xs text-rose-400/80 line-clamp-2">
                          {report.recent_runs.find((r: any) => r.status === 'error')?.error_message || "Unknown error"}
                        </span>
                        Please check your API quota or consider using a different model.
                      </div>
                    </div>
                  ) : (
                    "No tracking data available yet. Run a tracking batch to generate insights."
                  )}
                </div>
              </div>

              {/* Stat Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                
                {/* Stat 1: Brand AI Visibility */}
                <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/20 backdrop-blur-xl hover:border-zinc-800 transition duration-150 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-purple-600/5 rounded-full blur-2xl group-hover:bg-purple-600/10 transition duration-200" />
                  <div className="flex items-center justify-between text-zinc-500 mb-4">
                    <span className="text-xs font-bold uppercase tracking-wider">Brand AI Visibility</span>
                    <TrendingUp className="h-4 w-4 text-purple-400" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold tracking-tight text-white">
                      {report.visibility?.visibility_pct}%
                    </span>
                    {report.visibility?.week_over_week_delta != null && (
                      <span className={`text-xs font-semibold flex items-center gap-0.5 ${
                        report.visibility.week_over_week_delta >= 0 ? "text-emerald-400" : "text-rose-400"
                      }`}>
                        {report.visibility.week_over_week_delta >= 0 ? "+" : ""}
                        {report.visibility.week_over_week_delta}%
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-2">Target brand citations in AI output</p>
                </div>

                {/* Stat 2: Share of Voice */}
                <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/20 backdrop-blur-xl hover:border-zinc-800 transition duration-150 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-600/5 rounded-full blur-2xl group-hover:bg-indigo-600/10 transition duration-200" />
                  <div className="flex items-center justify-between text-zinc-500 mb-4">
                    <span className="text-xs font-bold uppercase tracking-wider">Share of Voice</span>
                    <Award className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold tracking-tight text-white">
                      {report.share_of_voice?.share_pct}%
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-2">Proportion of mentions vs competitors</p>
                </div>

                {/* Stat 3: Average Position */}
                <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/20 backdrop-blur-xl hover:border-zinc-800 transition duration-150 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-600/5 rounded-full blur-2xl group-hover:bg-emerald-600/10 transition duration-200" />
                  <div className="flex items-center justify-between text-zinc-500 mb-4">
                    <span className="text-xs font-bold uppercase tracking-wider">Average Position</span>
                    <Layers className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold tracking-tight text-white">
                      {report.share_of_voice?.avg_position || 1.0}
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-2">Rank index in responses when mentioned</p>
                </div>

                {/* Stat 4: Tracked Prompts */}
                <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/20 backdrop-blur-xl hover:border-zinc-800 transition duration-150 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-amber-600/5 rounded-full blur-2xl group-hover:bg-amber-600/10 transition duration-200" />
                  <div className="flex items-center justify-between text-zinc-500 mb-4">
                    <span className="text-xs font-bold uppercase tracking-wider">Active Queries</span>
                    <Database className="h-4 w-4 text-amber-400" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold tracking-tight text-white">
                      {prompts.length}
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-2">Queries tracked for visibility analyses</p>
                </div>
              </div>

              {/* Charts & Lead Board Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                
                {/* Left Column (3 spans) */}
                <div className="col-span-1 lg:col-span-3 space-y-6">
                  
                  {/* Platform Scorecard */}
                  <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6 overflow-x-auto">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      Platform Scorecard
                      <span className="w-4 h-4 rounded-full bg-zinc-800 text-zinc-400 flex items-center justify-center text-[10px]">?</span>
                    </h3>
                    <table className="w-full text-left text-xs min-w-[600px]">
                      <thead>
                        <tr className="text-zinc-500 border-b border-zinc-900/50">
                          <th className="pb-3 font-semibold uppercase tracking-wider">Platform</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider">Your Visibility</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider">Top Competitor</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider">Gap</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-900/50">
                        {report.platform_scorecard?.map((entry: any) => (
                          <tr key={entry.platform} className="hover:bg-zinc-900/20">
                            <td className="py-4 font-bold text-white">{entry.platform}</td>
                            <td className="py-4">
                              <div className="flex items-center gap-3 w-32">
                                <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                  <div className="h-full rounded-full bg-emerald-500" style={{ width: `${entry.your_visibility}%` }} />
                                </div>
                                <span className="text-zinc-400 w-8">{entry.your_visibility}%</span>
                              </div>
                            </td>
                            <td className="py-4">
                              <div className="flex flex-col gap-1">
                                <span className="text-zinc-500 text-[10px] uppercase font-bold">{entry.top_competitor}</span>
                                <div className="flex items-center gap-3 w-32">
                                  <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                    <div className="h-full rounded-full bg-zinc-600" style={{ width: `${entry.top_competitor_visibility}%` }} />
                                  </div>
                                  <span className="text-zinc-400 w-8">{entry.top_competitor_visibility}%</span>
                                </div>
                              </div>
                            </td>
                            <td className="py-4">
                              <span className={`font-semibold ${entry.gap > 0 ? 'text-emerald-400' : entry.gap < 0 ? 'text-rose-400' : 'text-zinc-400'}`}>
                                {entry.gap > 0 ? '+' : ''}{entry.gap}
                              </span>
                            </td>
                            <td className="py-4 text-right">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                                entry.status === 'Leading' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                entry.status === 'Behind' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
                              }`}>
                                {entry.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Competitive Landscape */}
                  <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6 overflow-x-auto">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      Competitive Landscape
                    </h3>
                    <table className="w-full text-left text-xs min-w-[600px]">
                      <thead>
                        <tr className="text-zinc-500 border-b border-zinc-900/50">
                          <th className="pb-3 font-semibold uppercase tracking-wider">Brand</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider">Visibility</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider">Share of Voice</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider">Position</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider text-right">Sentiment</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-900/50">
                        {report.leaderboard?.map((entry: any, idx: number) => {
                          const isYou = report.workspace?.brand_name && (
                            entry.brand_name.toLowerCase().includes(report.workspace.brand_name.toLowerCase()) ||
                            report.workspace.brand_name.toLowerCase().includes(entry.brand_name.toLowerCase()) ||
                            (report.workspace.aliases || []).some((a: string) => entry.brand_name.toLowerCase().includes(a.toLowerCase()))
                          );
                          return (
                            <tr key={entry.brand_name} className="hover:bg-zinc-900/20">
                              <td className="py-4">
                                <div className="flex items-center gap-3">
                                  <span className="text-zinc-600 font-bold w-4">{idx + 1}</span>
                                  <span className={`font-bold ${isYou ? 'text-white' : 'text-zinc-300'}`}>
                                    {entry.brand_name}
                                  </span>
                                  {isYou && <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-[9px] font-bold uppercase tracking-wider">You</span>}
                                </div>
                              </td>
                              <td className="py-4">
                                <div className="flex items-center gap-3 w-32">
                                  <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full ${isYou ? 'bg-emerald-500' : 'bg-zinc-600'}`} style={{ width: `${entry.visibility_pct}%` }} />
                                  </div>
                                  <span className="text-zinc-400 w-8">{entry.visibility_pct}%</span>
                                </div>
                              </td>
                              <td className="py-4">
                                <div className="flex items-center gap-3 w-32">
                                  <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full ${isYou ? 'bg-emerald-500' : 'bg-zinc-600'}`} style={{ width: `${entry.share_pct}%` }} />
                                  </div>
                                  <span className="text-zinc-400 w-8">{entry.share_pct}%</span>
                                </div>
                              </td>
                              <td className="py-4">
                                <span className="font-semibold text-zinc-300">#{entry.avg_position || '-'}</span>
                              </td>
                              <td className="py-4 text-right">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                                  entry.sentiment === 'Positive' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                  entry.sentiment === 'Negative' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                  'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
                                }`}>
                                  {entry.sentiment}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Topic Performance */}
                  <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6 overflow-x-auto">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      Topic Performance
                      <span className="w-4 h-4 rounded-full bg-zinc-800 text-zinc-400 flex items-center justify-center text-[10px]">?</span>
                    </h3>
                    <table className="w-full text-left text-xs min-w-[600px]">
                      <thead>
                        <tr className="text-zinc-500 border-b border-zinc-900/50">
                          <th className="pb-3 font-semibold uppercase tracking-wider w-1/3">Topic</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider">Your Visibility</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider">Top Competitor</th>
                          <th className="pb-3 font-semibold uppercase tracking-wider text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-900/50">
                        {report.topic_performance?.map((entry: any, i: number) => (
                          <tr key={i} className="hover:bg-zinc-900/20">
                            <td className="py-4 pr-4">
                              <p className="text-emerald-400 font-medium leading-relaxed">{entry.topic}</p>
                            </td>
                            <td className="py-4">
                              <div className="flex items-center gap-3 w-32">
                                <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                  <div className="h-full rounded-full bg-emerald-500" style={{ width: `${entry.your_visibility}%` }} />
                                </div>
                                <span className="text-zinc-400 w-8">{entry.your_visibility}%</span>
                              </div>
                            </td>
                            <td className="py-4">
                              <div className="flex flex-col gap-1">
                                <span className="text-zinc-500 text-[10px] uppercase font-bold">{entry.top_competitor}</span>
                                <div className="flex items-center gap-3 w-32">
                                  <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                    <div className="h-full rounded-full bg-zinc-600" style={{ width: `${entry.top_competitor_visibility}%` }} />
                                  </div>
                                  <span className="text-zinc-400 w-8">{entry.top_competitor_visibility}%</span>
                                </div>
                              </div>
                            </td>
                            <td className="py-4 text-right">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                                entry.status === 'Leading' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                entry.status === 'Behind' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
                              }`}>
                                {entry.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  
                </div>

                {/* Right Column (1 span) */}
                <div className="col-span-1 space-y-6">
                  {/* AI Sources Sidebar */}
                  <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6 sticky top-6">
                    <h3 className="text-sm font-bold text-white flex items-center justify-between">
                      AI Sources
                      <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Top 10</span>
                    </h3>
                    <div className="space-y-4">
                      {report.brand_citations?.slice(0, 10).map((cit: any, idx: number) => (
                        <div key={idx} className="flex flex-col gap-1 py-2 border-b border-zinc-900/50 last:border-0">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-zinc-600 text-[10px]">▸</span>
                              <span className={`text-xs font-bold ${cit.is_brand_citation ? 'text-emerald-400' : 'text-zinc-200'}`}>{cit.domain}</span>
                              {cit.is_brand_citation && <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-[8px] font-bold uppercase tracking-wider">Own</span>}
                            </div>
                            <span className="text-xs font-bold text-zinc-400">{cit.count}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

              </div>

              {/* Recent Tracking Runs Log */}
              <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6">
                <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Recent Tracking Batches</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-zinc-900 text-zinc-500">
                        <th className="pb-3 font-semibold">Run ID</th>
                        <th className="pb-3 font-semibold">Engine</th>
                        <th className="pb-3 font-semibold">Target Week</th>
                        <th className="pb-3 font-semibold">Estimated Cost</th>
                        <th className="pb-3 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-900/50 text-zinc-300">
                      {report.recent_runs?.map((run: any) => (
                        <tr key={run.id} className="hover:bg-zinc-900/25">
                          <td className="py-3 font-mono text-zinc-500">{run.id.slice(0, 8)}...</td>
                          <td className="py-3 font-medium capitalize">{run.engine}</td>
                          <td className="py-3">{run.iso_week}</td>
                          <td className="py-3">${run.cost_usd.toFixed(4)}</td>
                          <td className="py-3">
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold text-[10px]">
                              {run.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </motion.div>
          ) : activeTab === "dashboard" && !report ? (
            <div className="h-[60vh] flex flex-col items-center justify-center space-y-6">
              <div className="relative">
                <div className="absolute inset-0 bg-purple-500 rounded-full blur-[40px] opacity-20 animate-pulse" />
                <div className="h-20 w-20 bg-zinc-900 border border-zinc-800 rounded-full flex items-center justify-center relative z-10 shadow-xl">
                  <Activity className="h-8 w-8 text-purple-400 animate-pulse" />
                </div>
              </div>
              <div className="text-center space-y-2">
                <h3 className="text-xl font-bold text-white">Tracking in Progress</h3>
                <p className="text-zinc-400 max-w-sm mx-auto text-sm">
                  We are querying the AI engines in the background. It takes about 30 seconds for the first visibility report to compile.
                </p>
              </div>
            </div>
          ) : null}

          {/* ────────────────────────────────────────────────────────
              TAB: WORKSTREAMS
             ──────────────────────────────────────────────────────── */}
          {activeTab === "workstreams" && (
            <motion.div initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }} className="space-y-8">
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-xl font-bold text-white">Workstreams</h3>
                  <p className="text-sm text-zinc-400">Track portfolio-level goals across subsets of your prompts.</p>
                </div>
                <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg text-sm transition-colors shadow-[0_0_15px_rgba(37,99,235,0.3)]">
                  Create Workstream
                </button>
              </div>

              {workstreams.length === 0 ? (
                <div className="p-12 text-center border border-zinc-900 rounded-2xl bg-zinc-900/10">
                  <Target className="h-10 w-10 text-zinc-600 mx-auto mb-4" />
                  <p className="text-zinc-400">No workstreams created yet. Build one to track a specific campaign's visibility.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {workstreams.map((ws: any) => (
                    <div key={ws.id} className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/20 hover:border-zinc-700 transition-colors cursor-pointer group">
                      <div className="flex justify-between items-start mb-4">
                        <h4 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors">{ws.name}</h4>
                        <span className="text-xs font-semibold px-2 py-1 bg-zinc-800 rounded-md text-zinc-300">Target: {ws.target_visibility}%</span>
                      </div>
                      <div className="space-y-3">
                        <div>
                          <span className="text-xs text-zinc-500 uppercase font-semibold">Topics</span>
                          <div className="flex flex-wrap gap-2 mt-1">
                            {ws.topics?.length ? ws.topics.map((t: string) => <span key={t} className="px-2 py-1 bg-zinc-900 rounded-md text-xs text-zinc-400">{t}</span>) : <span className="text-xs text-zinc-600">All Topics</span>}
                          </div>
                        </div>
                        <div>
                          <span className="text-xs text-zinc-500 uppercase font-semibold">Attribute Filters</span>
                          <div className="flex flex-wrap gap-2 mt-1">
                            {ws.attribute_filters?.length ? ws.attribute_filters.map((a: string) => <span key={a} className="px-2 py-1 bg-blue-900/20 border border-blue-500/20 rounded-md text-xs text-blue-400 uppercase tracking-wider">{a}</span>) : <span className="text-xs text-zinc-600">No Filters</span>}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* ────────────────────────────────────────────────────────
              TAB: TOPIC CLUSTERS / CONTENT GAPS
             ──────────────────────────────────────────────────────── */}
          {activeTab === "clusters" && (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
              
              {/* Clusters List */}
              <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6">
                <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Tracked Topic Clusters</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-zinc-900 text-zinc-500">
                        <th className="pb-3 font-semibold">Topic Cluster</th>
                        <th className="pb-3 font-semibold">Search Vol</th>
                        <th className="pb-3 font-semibold">AI Visibility</th>
                        <th className="pb-3 font-semibold">Opp. Score</th>
                        <th className="pb-3 font-semibold">Action</th>
                        <th className="pb-3"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-900/50 text-zinc-300">
                      {clusters.map((cluster) => (
                        <tr key={cluster.id} className="hover:bg-zinc-900/25 cursor-pointer" onClick={() => fetchBrief(cluster)}>
                          <td className="py-4 font-semibold text-zinc-200">{cluster.cluster_name}</td>
                          <td className="py-4">{cluster.search_volume?.toLocaleString() || "0"}</td>
                          <td className="py-4">{cluster.brand_ai_visibility}%</td>
                          <td className="py-4 text-purple-400 font-bold">{cluster.opportunity_score}</td>
                          <td className="py-4">
                            <span className="px-2 py-0.5 rounded bg-zinc-800 text-[10px] uppercase font-semibold text-zinc-400 border border-zinc-700">
                              {cluster.refill_action}
                            </span>
                          </td>
                          <td className="py-4 text-right">
                            <ChevronRight className="h-4 w-4 text-zinc-600 inline" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Opportunities Details Panel */}
              <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6 min-h-[400px]">
                {!selectedCluster ? (
                  <div className="flex flex-col items-center justify-center h-full text-zinc-500 space-y-2 py-20">
                    <Layers className="h-8 w-8 text-zinc-700" />
                    <span className="text-xs">Select a topic cluster to generate content briefs and optimized drafts.</span>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="flex items-center justify-between border-b border-zinc-900 pb-4">
                      <div>
                        <h4 className="text-base font-bold text-white">{selectedCluster.cluster_name}</h4>
                        <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">
                          Recommended Action: {selectedCluster.refill_action}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-zinc-500 block">Opportunity Score</span>
                        <span className="text-lg font-bold text-purple-400">{selectedCluster.opportunity_score}</span>
                      </div>
                    </div>

                    {briefLoading && (
                      <div className="flex items-center justify-center py-20 text-xs text-zinc-500 gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-purple-500" />
                        Generating Brief from historical signals...
                      </div>
                    )}

                    {brief && !briefLoading && (
                      <div className="space-y-6">
                        
                        {/* Target Queries */}
                        <div className="space-y-2">
                          <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider block">Target Queries to capture</span>
                          <div className="flex flex-wrap gap-2">
                            {brief.target_queries.map((q: string) => (
                              <span key={q} className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-300">
                                {q}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Structural Outline */}
                        <div className="space-y-2">
                          <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider block">Suggested Article Structure</span>
                          <ul className="space-y-1.5 list-disc pl-4 text-xs text-zinc-300">
                            {brief.outline.map((o: string, idx: number) => (
                              <li key={idx} className="leading-relaxed">{o}</li>
                            ))}
                          </ul>
                        </div>

                        {/* Sources to Win */}
                        <div className="space-y-2">
                          <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider block">Required Information / Sources</span>
                          <ul className="space-y-1.5 list-disc pl-4 text-xs text-zinc-300">
                            {brief.sources_to_win.map((s: string, idx: number) => (
                              <li key={idx} className="leading-relaxed text-indigo-300">{s}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="border-t border-zinc-900 pt-4 flex gap-4">
                          <button
                            onClick={fetchDraft}
                            disabled={draftLoading}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold transition"
                          >
                            {draftLoading ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Sparkles className="h-3.5 w-3.5" />
                            )}
                            Write Content Draft with AEO Engine
                          </button>
                        </div>
                      </div>
                    )}

                    {draftLoading && (
                      <div className="flex items-center justify-center py-20 text-xs text-zinc-500 gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-purple-500" />
                        Generating AEO-optimized draft article...
                      </div>
                    )}

                    {draft && !draftLoading && (
                      <div className="space-y-4 border-t border-zinc-900 pt-6">
                        <div className="flex justify-between items-center bg-zinc-900/50 px-4 py-2 rounded-lg border border-zinc-800">
                          <span className="text-xs font-bold text-zinc-400">Optimized Draft Ready</span>
                          <button
                            onClick={() => copyToClipboard(draft.body)}
                            className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 font-semibold"
                          >
                            {copiedText ? (
                              <>
                                <Check className="h-3.5 w-3.5" />
                                Copied!
                              </>
                            ) : (
                              <>
                                <Clipboard className="h-3.5 w-3.5" />
                                Copy Markdown
                              </>
                            )}
                          </button>
                        </div>
                        <div className="p-4 rounded-xl border border-zinc-900 bg-zinc-900/30 max-h-[400px] overflow-y-auto font-mono text-[11px] text-zinc-300 whitespace-pre-wrap leading-relaxed">
                          {draft.body}
                        </div>
                      </div>
                    )}

                  </div>
                )}
              </div>

            </div>
          )}

          {/* ────────────────────────────────────────────────────────
              TAB: QUERY MANAGER
             ──────────────────────────────────────────────────────── */}
          {activeTab === "prompts" && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
              
              {/* Add Prompts Panel */}
              <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6 h-fit">
                
                {/* Single Prompt */}
                <form onSubmit={addPrompt} className="space-y-4">
                  <h4 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Add Single Query</h4>
                  
                  <div className="space-y-1.5">
                    <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-semibold">Query Text</label>
                    <input
                      type="text"
                      placeholder="e.g. Which serverless platform has the lowest latency?"
                      value={newPromptText}
                      onChange={(e) => setNewPromptText(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-600 transition"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-semibold">Search Intent</label>
                      <select
                        value={newPromptIntent}
                        onChange={(e) => setNewPromptIntent(e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-600"
                      >
                        <option value="informational">Informational</option>
                        <option value="commercial">Commercial</option>
                        <option value="transactional">Transactional</option>
                        <option value="navigational">Navigational</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-semibold">Target Persona</label>
                      <select
                        value={newPromptPersona}
                        onChange={(e) => setNewPromptPersona(e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-600"
                      >
                        <option value="developer">Developer</option>
                        <option value="architect">Architect</option>
                        <option value="executive">Executive</option>
                        <option value="general">General</option>
                      </select>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-semibold">Topic Cluster Assignment</label>
                    <input
                      type="text"
                      placeholder="e.g. Serverless Hosting Comparison"
                      value={newPromptCluster}
                      onChange={(e) => setNewPromptCluster(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-600 transition"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={promptSubmitLoading || !newPromptText.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-semibold transition disabled:opacity-50"
                  >
                    <Plus className="h-4 w-4" />
                    Save Query
                  </button>
                </form>

                <div className="border-t border-zinc-900 pt-6" />

                {/* Bulk upload */}
                <form onSubmit={addBulkPrompts} className="space-y-4">
                  <h4 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Bulk Upload Queries</h4>
                  <div className="space-y-1.5">
                    <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-semibold">Queries (One per line)</label>
                    <textarea
                      rows={5}
                      placeholder="e.g. Best cloud database 2026&#10;Supabase vs Postgres comparison&#10;How to host serverless backend"
                      value={bulkPromptsText}
                      onChange={(e) => setBulkPromptsText(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-xs text-white font-mono focus:outline-none focus:border-purple-600 transition"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={promptSubmitLoading || !bulkPromptsText.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-semibold transition disabled:opacity-50"
                  >
                    <UploadIcon className="h-4 w-4" />
                    Upload Batch
                  </button>
                </form>

              </div>

              {/* Prompts list table */}
              <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 xl:col-span-2 space-y-6">
                <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Currently Tracked Queries</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-zinc-900 text-zinc-500">
                        <th className="pb-3 font-semibold">Query Text</th>
                        <th className="pb-3 font-semibold">Intent</th>
                        <th className="pb-3 font-semibold">Persona</th>
                        <th className="pb-3 font-semibold">Topic Cluster</th>
                        <th className="pb-3 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-900/50 text-zinc-300">
                      {prompts.map((p) => (
                        <tr key={p.id} className="hover:bg-zinc-900/25">
                          <td className="py-3.5 pr-4 font-medium text-zinc-200">{p.prompt_text}</td>
                          <td className="py-3.5">
                            <span className="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-900 text-[10px] text-zinc-400 uppercase font-semibold">
                              {p.intent}
                            </span>
                          </td>
                          <td className="py-3.5 text-zinc-400 font-medium capitalize">{p.persona}</td>
                          <td className="py-3.5 text-zinc-400">{p.topic_cluster || "Unassigned"}</td>
                          <td className="py-3.5">
                            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] uppercase font-bold border border-emerald-500/20" title="Query is active and will be tracked in the next batch">Active</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* ────────────────────────────────────────────────────────
              TAB: COMPETITOR ANALYSIS
             ──────────────────────────────────────────────────────── */}
          {activeTab === "competitors" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              
              {/* Add competitor form & Tracked List */}
              <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 space-y-6 h-fit">
                <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Track Competitors</h3>
                
                <div className="space-y-4">
                  {competitors.map((c) => (
                    <div key={c.id} className="p-4 rounded-xl border border-zinc-900 bg-zinc-900/20 flex items-center justify-between">
                      <div>
                        <span className="font-bold text-xs text-white block">{c.brand_name}</span>
                        <span className="text-[10px] text-zinc-500 block">{c.domain}</span>
                      </div>
                      <span className="text-[10px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded font-semibold uppercase">
                        Active
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Competitor citation source list */}
              <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-900/10 lg:col-span-2 space-y-6">
                <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Competitor Citation Sources</h3>
                <p className="text-xs text-zinc-500">Domains the AI engines cite when referencing competitors in answers.</p>
                
                <div className="space-y-6">
                  {Object.entries(compSources || {}).map(([brand, sources]: [string, any]) => (
                    <div key={brand} className="space-y-3">
                      <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider">{brand}</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {sources.map((s: any, idx: number) => (
                          <div key={idx} className="p-3 rounded-lg bg-zinc-950 border border-zinc-900 flex items-center justify-between">
                            <span className="text-xs font-medium text-zinc-300 font-mono flex items-center gap-1.5">
                              <ExternalLink className="h-3 w-3 text-zinc-600" />
                              {s.domain}
                            </span>
                            <span className="text-[10px] text-zinc-500 font-semibold uppercase">{s.count} mentions</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

        </div>
      </main>

      {/* ── LIVE TRACKING MODAL OVERLAY ─────────────────────────────── */}
      {isLiveTracking && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-[100] flex flex-col items-center justify-center p-8">
          <div className="w-full max-w-4xl relative">
            <LiveTrackingConsole 
              apiKey={config.apiKey}
              backendUrl={config.backendUrl}
              enginesCount={selectedEngines.length || 6}
              title="Manual Batch Run in Progress"
              subtitle="Executing active tracking across selected AI engines..."
              onComplete={async () => {
                setIsLiveTracking(false);
                setTriggerStatus(null);
                await fetchData(config);
              }}
            />
          </div>
        </div>
      )}


    </div>
  );
}

// Simple Helper Icon
function UploadIcon(props: any) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" x2="12" y1="3" y2="15" />
    </svg>
  );
}
