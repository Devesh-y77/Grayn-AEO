"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";

interface AnalyzeStepProps {
  domain: string;
  setDomain: (val: string) => void;
  onComplete: () => void;
}

export default function AnalyzeStep({ domain, setDomain, onComplete }: AnalyzeStepProps) {
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [sourceIndex, setSourceIndex] = useState(1);

  const keywords = [
    "landscape design company location headquarters",
    "augmented reality landscape design software apps",
    "top competitors for landscape contractors app",
    "3D visualization plant library reviews",
    "client proposal generation pricing SaaS",
    "landscape professionals vs homeowners features",
    "realtime landscaping alternatives 2026",
    "best AR tools for outdoor yard design",
    "dynascape vs pro landscape comparison",
    "landscape design market share reports"
  ];

  useEffect(() => {
    if (analyzing) {
      let currentProgress = 0;
      let currentIndex = 1;

      const interval = setInterval(() => {
        currentProgress += Math.random() * 3;
        if (currentProgress > currentIndex * 10) {
          currentIndex++;
        }
        
        if (currentProgress >= 100 || currentIndex > 10) {
          clearInterval(interval);
          setProgress(100);
          setSourceIndex(10);
          setTimeout(onComplete, 1000);
        } else {
          setProgress(currentProgress);
          setSourceIndex(Math.min(currentIndex, 10));
        }
      }, 100);

      return () => clearInterval(interval);
    }
  }, [analyzing, onComplete]);

  return (
    <div className="flex-1 flex flex-col items-center pt-32 text-zinc-300">
      <div className="w-full max-w-4xl bg-yellow-600/20 text-yellow-500 p-4 rounded mb-20 relative">
        <button className="absolute right-4 top-4 text-yellow-500/50 hover:text-yellow-500">×</button>
        <span className="bg-yellow-500 text-black text-xs font-bold px-2 py-0.5 rounded mr-3 uppercase tracking-wider">Announcement</span>
        <span className="font-semibold text-white">Introducing Starter and Agency</span>
        <p className="mt-1 text-sm text-yellow-500/80">
          OpenLens has plans now. Existing accounts keep everything they have today, and early users have a founding-member offer waiting in their inbox.{" "}
          <a href="#" className="underline hover:text-white">Read the announcement &rarr;</a>
        </p>
      </div>

      <div className="text-zinc-500 text-sm mb-8 hover:text-white cursor-pointer">&larr; Back to clients</div>

      <h1 className="text-3xl font-semibold text-white mb-2 text-center">Add new client</h1>
      <p className="text-zinc-400 text-center mb-8 max-w-md">
        We'll show you how AI talks about your brand across ChatGPT, Perplexity, Google AI, Gemini, and DeepSeek.
      </p>

      {!analyzing ? (
        <div className="flex items-center gap-4 w-full max-w-lg">
          <input
            type="text"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="https://www.example.com/"
            className="flex-1 bg-transparent border border-zinc-700 rounded p-3 text-white focus:outline-none focus:border-yellow-500 transition-colors"
          />
          <button
            onClick={() => setAnalyzing(true)}
            disabled={!domain}
            className="bg-yellow-600 hover:bg-yellow-500 text-black font-semibold py-3 px-6 rounded disabled:opacity-50 transition-colors"
          >
            Start Analyzing
          </button>
        </div>
      ) : (
        <div className="w-full max-w-lg">
          <div className="flex items-center gap-4 mb-8 opacity-50 pointer-events-none">
            <input
              type="text"
              value={domain}
              readOnly
              className="flex-1 bg-transparent border border-zinc-700 rounded p-3 text-white"
            />
            <button className="bg-yellow-600/30 text-yellow-500/50 font-semibold py-3 px-6 rounded flex items-center gap-2">
              <span className="w-4 h-4 rounded-full border-2 border-t-yellow-500 animate-spin border-yellow-500/30"></span>
              Analyzing...
            </button>
          </div>

          <div className="w-full">
            <div className="flex justify-between items-end mb-2">
              <h3 className="text-white font-medium text-lg">Search {sourceIndex} of 10</h3>
              <span className="text-zinc-500 text-sm">{Math.min(100, Math.floor(progress))}%</span>
            </div>
            <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden mb-3">
              <motion.div
                className="bg-yellow-500 h-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.1 }}
              />
            </div>
            <p className="text-zinc-500 text-sm italic">
              "{domain.replace(/https?:\/\/(www\.)?/, '').replace('/', '')} {keywords[sourceIndex - 1]}"
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
