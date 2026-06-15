"use client";

import React, { useState } from "react";
import { SetupData } from "./ConfirmSetupStep";

export interface PromptData {
  id: string;
  text: string;
  topic: string;
  active: boolean;
  attributes: string[];
}

interface ReviewPromptsStepProps {
  setupData: SetupData;
  onRunPrompts: (prompts: PromptData[]) => void;
}

export default function ReviewPromptsStep({ setupData, onRunPrompts }: ReviewPromptsStepProps) {
  // Generate mock prompts based on the topics and attributes provided
  const [prompts, setPrompts] = useState<PromptData[]>(() => {
    const list: PromptData[] = [];
    setupData.searchTopics.forEach((topic, i) => {
      const variations = [
        "What is the best",
        "Top rated",
        "Compare",
        "Reviews for",
        "Which is better for"
      ];
      for (let j = 0; j < setupData.promptsPerTopic; j++) {
        const prefix = variations[j % variations.length];
        const attr = setupData.attributes[j % setupData.attributes.length] || 'features';
        
        list.push({
          id: `p_${i}_${j}`,
          text: `${prefix} ${topic.toLowerCase()} near ${setupData.location} considering ${attr}?`,
          topic,
          active: true,
          attributes: setupData.languages.slice(0, 1), // Default tag
        });
      }
    });
    return list;
  });

  const [activeTopic, setActiveTopic] = useState<string>("All Topics");

  const filteredPrompts = prompts.filter(p => activeTopic === "All Topics" || p.topic === activeTopic);
  const activeCount = prompts.filter(p => p.active).length;

  const togglePrompt = (id: string) => {
    setPrompts(prompts.map(p => p.id === id ? { ...p, active: !p.active } : p));
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0a0a] text-zinc-300">
      
      {/* Header */}
      <div className="p-6 border-b border-[#222] flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Review your prompts</h1>
          <p className="text-sm text-zinc-500 mt-1">These prompts were auto-generated for your topics. Edit, add, or remove any before running them across AI platforms.</p>
        </div>
        <button 
          onClick={() => onRunPrompts(prompts.filter(p => p.active))}
          className="bg-yellow-600 hover:bg-yellow-500 text-black font-semibold py-2 px-6 rounded transition-colors"
        >
          Run {activeCount} Prompts
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar (Topics) */}
        <div className="w-64 border-r border-[#222] p-4 flex flex-col overflow-y-auto">
          <div className="space-y-1">
            <button 
              onClick={() => setActiveTopic("All Topics")}
              className={`w-full text-left px-3 py-2 rounded text-sm ${activeTopic === "All Topics" ? 'bg-[#222] text-white font-medium' : 'text-zinc-400 hover:text-white'}`}
            >
              All Topics
            </button>
            {setupData.searchTopics.map((topic, idx) => (
              <button 
                key={idx}
                onClick={() => setActiveTopic(topic)}
                className={`w-full text-left px-3 py-2 rounded text-sm truncate ${activeTopic === topic ? 'bg-[#222] text-white font-medium' : 'text-zinc-400 hover:text-white'}`}
                title={topic}
              >
                {topic}
              </button>
            ))}
          </div>
          <button className="text-yellow-500 text-sm mt-4 px-3 hover:text-yellow-400">+ Add Topic</button>
        </div>

        {/* Main Table Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          
          {/* Table Header Controls */}
          <div className="p-4 border-b border-[#222] flex items-center justify-between">
            <div className="flex items-center gap-4">
              <input 
                type="text" 
                placeholder="Search prompts..." 
                className="bg-[#111] border border-[#333] rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-yellow-500 w-64"
              />
              <div className="flex gap-2">
                <button className="text-xs text-zinc-400 border border-[#333] px-2 py-1 rounded bg-[#111] hover:text-white">Filter attributes</button>
                <button className="text-xs text-zinc-400 hover:text-white pt-1">Manage attributes</button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">Prompts:</span>
              <div className="flex gap-1">
                {[5, 10, 15, 20].map(n => (
                   <span key={n} className={`text-xs px-2 py-0.5 rounded border ${setupData.promptsPerTopic === n ? 'bg-yellow-600/20 border-yellow-600/50 text-yellow-500' : 'bg-[#111] border-[#333] text-zinc-500'}`}>{n}</span>
                ))}
              </div>
              <button className="text-xs bg-[#222] text-white border border-[#333] px-2 py-1 rounded ml-2">+ Add Prompt</button>
            </div>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="sticky top-0 bg-[#0a0a0a] border-b border-[#222] z-10 text-xs text-zinc-500 uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3 font-medium">Prompt</th>
                  <th className="px-6 py-3 font-medium">Topic</th>
                  <th className="px-6 py-3 font-medium w-24 text-center">Active</th>
                  <th className="px-6 py-3 font-medium w-48">Attributes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a1a1a]">
                {filteredPrompts.map((p) => (
                  <tr key={p.id} className="hover:bg-[#111]">
                    <td className="px-6 py-4 text-zinc-300 whitespace-normal min-w-[400px]">
                      {p.text}
                    </td>
                    <td className="px-6 py-4 text-zinc-500 truncate max-w-[200px]" title={p.topic}>
                      {p.topic}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <button 
                        onClick={() => togglePrompt(p.id)}
                        className={`w-10 h-5 rounded-full relative transition-colors ${p.active ? 'bg-emerald-500' : 'bg-zinc-700'}`}
                      >
                        <div className={`w-3 h-3 bg-white rounded-full absolute top-1 transition-all ${p.active ? 'right-1' : 'left-1'}`} />
                      </button>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1 flex-wrap">
                        {p.attributes.map(attr => (
                          <span key={attr} className="bg-[#222] border border-[#333] px-2 py-0.5 rounded text-xs text-zinc-400">
                            {attr}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>
      </div>
    </div>
  );
}
