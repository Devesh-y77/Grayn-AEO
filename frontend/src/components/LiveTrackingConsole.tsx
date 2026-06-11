"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Terminal, CheckCircle2, AlertCircle } from "lucide-react";

interface RunLogItem {
  engine: string;
  prompt_text: string;
  status: string;
  created_at: string;
}

interface RunStatus {
  progress_pct: number;
  completed: number;
  total: number;
  is_running: boolean;
  latest_logs: RunLogItem[];
}

interface LiveTrackingConsoleProps {
  apiKey: string;
  backendUrl: string;
  enginesCount: number;
  onComplete: () => void;
  title?: string;
  subtitle?: string;
}

export default function LiveTrackingConsole({
  apiKey,
  backendUrl,
  enginesCount,
  onComplete,
  title = "Tracking AI Visibility",
  subtitle = "Querying target engines and extracting citations live..."
}: LiveTrackingConsoleProps) {
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [status?.latest_logs]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    const fetchStatus = async () => {
      try {
        let base = backendUrl.replace(/\/$/, ""); // trim trailing slash

        const res = await fetch(`${base}/v1/runs/status?engines_count=${enginesCount}`, {
          headers: {
            "Authorization": `Bearer ${apiKey}`,
            "Content-Type": "application/json"
          }
        });
        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`Failed to fetch status: ${res.status} ${errText.substring(0, 50)}`);
        }
        const data: RunStatus = await res.json();
        setStatus(data);

        if (data.progress_pct >= 100) {
          clearInterval(interval);
          // Wait 1 second before calling onComplete so user sees 100%
          setTimeout(onComplete, 1000);
        }
      } catch (err: any) {
        console.warn("[browser] LiveTrackingConsole fetch failed (will retry):", err);
        // Do not clear the interval; allow it to retry on the next tick
        // in case the backend is temporarily restarting or Supabase is flaky.
      }
    };

    fetchStatus(); // initial
    interval = setInterval(fetchStatus, 2000);

    return () => clearInterval(interval);
  }, [apiKey, backendUrl, enginesCount, onComplete]);

  const pct = status ? status.progress_pct : 0;
  
  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col gap-6">
      {/* Header Info */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white flex items-center justify-center gap-3">
          {pct < 100 ? (
            <Loader2 className="h-6 w-6 text-purple-400 animate-spin" />
          ) : (
            <CheckCircle2 className="h-6 w-6 text-emerald-400" />
          )}
          {title}
        </h2>
        <p className="text-zinc-400">{subtitle}</p>
      </div>

      {/* Progress Bar */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 backdrop-blur-sm shadow-xl relative overflow-hidden">
        {/* Glow effect based on progress */}
        <div 
          className="absolute inset-0 bg-purple-500/10 blur-3xl transition-all duration-1000"
          style={{ width: `${pct}%` }}
        />
        
        <div className="flex justify-between items-end mb-4 relative z-10">
          <div>
            <span className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Overall Progress</span>
            <div className="text-3xl font-bold text-white mt-1">
              {pct.toFixed(0)}%
            </div>
          </div>
          <div className="text-right">
            <span className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">Queries</span>
            <div className="text-xl font-medium text-zinc-300 mt-1">
              {status ? `${status.completed} / ${status.total}` : "0 / 0"}
            </div>
          </div>
        </div>

        {/* Bar */}
        <div className="h-3 w-full bg-zinc-800 rounded-full overflow-hidden relative z-10">
          <motion.div 
            className="h-full bg-gradient-to-r from-purple-500 to-indigo-500"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ type: "spring", bounce: 0, duration: 0.8 }}
          />
        </div>
      </div>

      {/* Terminal View */}
      <div className="bg-zinc-950 border border-zinc-800/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col relative">
        <div className="bg-zinc-900/80 px-4 py-3 border-b border-zinc-800 flex items-center gap-3">
          <Terminal className="h-4 w-4 text-zinc-400" />
          <span className="text-xs font-mono text-zinc-400 uppercase tracking-widest">Live Engine Output</span>
        </div>
        
        <div className="p-4 h-64 overflow-y-auto font-mono text-sm space-y-3">
          {error ? (
            <div className="text-rose-400 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" /> {error}
            </div>
          ) : !status ? (
            <div className="text-zinc-500 animate-pulse">Connecting to workers...</div>
          ) : status.latest_logs.length === 0 ? (
            <div className="text-zinc-500">Waiting for first query to complete...</div>
          ) : (
            <AnimatePresence>
              {status.latest_logs.map((log, i) => (
                <motion.div 
                  key={`${log.created_at}-${log.engine}-${log.prompt_text}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex gap-3 text-zinc-300"
                >
                  <span className="text-zinc-500 shrink-0">
                    [{new Date(log.created_at).toLocaleTimeString()}]
                  </span>
                  <span className={`shrink-0 font-bold ${
                    log.engine === 'openai' ? 'text-emerald-400' :
                    log.engine === 'gemini' ? 'text-blue-400' :
                    log.engine === 'claude' ? 'text-orange-400' :
                    log.engine === 'perplexity' ? 'text-cyan-400' :
                    'text-purple-400'
                  }`}>
                    [{log.engine}]
                  </span>
                  <span className="truncate">"{log.prompt_text}"</span>
                  <span className={`shrink-0 ml-auto ${log.status === 'error' ? 'text-rose-400' : 'text-zinc-500'}`}>
                    {log.status === 'error' ? 'FAILED' : 'OK'}
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
