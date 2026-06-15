"use client";

import React, { useEffect } from "react";
import { motion } from "framer-motion";

interface QueryingModalProps {
  onComplete: () => void;
}

export default function QueryingModal({ onComplete }: QueryingModalProps) {
  useEffect(() => {
    // Simulate the time it takes to query platforms (approx 3-5s for demo)
    const timer = setTimeout(() => {
      onComplete();
    }, 4000);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center backdrop-blur-sm">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-[#111] border border-[#222] rounded-xl p-8 max-w-sm w-full text-center shadow-2xl"
      >
        <div className="flex justify-center mb-6">
          <div className="w-10 h-10 border-4 border-yellow-600 border-t-yellow-400 rounded-full animate-spin"></div>
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">Querying platforms</h2>
        <p className="text-sm text-zinc-400">
          Sending your prompts to your selected AI platforms. This typically takes about <strong className="text-zinc-300">1-3 minutes.</strong>
        </p>
      </motion.div>
    </div>
  );
}
