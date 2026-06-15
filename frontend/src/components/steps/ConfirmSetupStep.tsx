"use client";

import React, { useState } from "react";

export interface SetupData {
  domain: string;
  brandName: string;
  location: string;
  languages: string[];
  competitors: Array<{ name: string; url: string; description: string }>;
  attributes: string[];
  searchTopics: string[];
  promptsPerTopic: number;
}

interface ConfirmSetupStepProps {
  initialData: SetupData;
  onComplete: (data: SetupData) => void;
  onTryDifferentUrl: () => void;
}

export default function ConfirmSetupStep({ initialData, onComplete, onTryDifferentUrl }: ConfirmSetupStepProps) {
  const [data, setData] = useState<SetupData>(initialData);
  const [newAttribute, setNewAttribute] = useState("");

  const handleAddCompetitor = () => {
    setData({
      ...data,
      competitors: [...data.competitors, { name: "", url: "", description: "" }]
    });
  };

  const handleRemoveCompetitor = (idx: number) => {
    setData({
      ...data,
      competitors: data.competitors.filter((_, i) => i !== idx)
    });
  };

  const handleAddAttribute = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && newAttribute.trim()) {
      e.preventDefault();
      if (!data.attributes.includes(newAttribute.trim())) {
        setData({ ...data, attributes: [...data.attributes, newAttribute.trim()] });
      }
      setNewAttribute("");
    }
  };

  const removeAttribute = (attr: string) => {
    setData({ ...data, attributes: data.attributes.filter(a => a !== attr) });
  };

  return (
    <div className="flex-1 overflow-y-auto pt-16 pb-32 text-zinc-300">
      <div className="max-w-2xl mx-auto">
        
        <div className="flex flex-col items-center mb-10 text-center">
          <div className="flex items-center gap-2 mb-6">
            <span className="bg-[#222] border border-[#333] px-3 py-1.5 rounded text-sm">{data.domain}</span>
            <button onClick={onTryDifferentUrl} className="text-zinc-400 hover:text-white bg-[#222] border border-[#333] px-3 py-1.5 rounded text-sm transition-colors">
              Try different URL
            </button>
          </div>
          <h1 className="text-3xl font-semibold text-white mb-2">Confirm your setup</h1>
          <p className="text-zinc-400 text-sm">
            Edit anything below, then start tracking.<br />
            <span className="text-zinc-500">Detected: Landscape Design Software</span>
          </p>
        </div>

        <div className="space-y-8">
          
          {/* Brand */}
          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Your brand</label>
            <input 
              type="text" 
              value={data.brandName} 
              onChange={e => setData({...data, brandName: e.target.value})}
              className="w-full bg-[#111] border border-[#333] rounded p-3 text-white focus:outline-none focus:border-yellow-500"
            />
          </div>

          {/* Location & Languages */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Location</label>
              <input 
                type="text" 
                value={data.location} 
                onChange={e => setData({...data, location: e.target.value})}
                className="w-full bg-[#111] border border-[#333] rounded p-3 text-white focus:outline-none focus:border-yellow-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Languages</label>
              <div className="flex items-center flex-wrap gap-2">
                {data.languages.map(lang => (
                  <span key={lang} className="bg-[#222] border border-[#333] px-3 py-1.5 rounded-full text-sm flex items-center gap-2">
                    {lang} <button className="text-zinc-500 hover:text-white">&times;</button>
                  </span>
                ))}
                <button className="text-zinc-500 hover:text-white text-sm ml-2">+ add</button>
              </div>
            </div>
          </div>

          {/* Competitors */}
          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Competitors</label>
            <div className="space-y-4">
              {data.competitors.map((comp, idx) => (
                <div key={idx} className="relative bg-[#111] border border-[#333] rounded p-1">
                  <input 
                    type="text" 
                    value={comp.name} 
                    onChange={e => {
                      const newComps = [...data.competitors];
                      newComps[idx].name = e.target.value;
                      setData({...data, competitors: newComps});
                    }}
                    placeholder="Competitor Name"
                    className="w-full bg-transparent border-b border-[#333] p-3 text-white focus:outline-none focus:border-yellow-500"
                  />
                  <input 
                    type="text" 
                    value={comp.url} 
                    onChange={e => {
                      const newComps = [...data.competitors];
                      newComps[idx].url = e.target.value;
                      setData({...data, competitors: newComps});
                    }}
                    placeholder="Website URL (optional)"
                    className="w-full bg-transparent p-3 text-sm text-zinc-400 focus:outline-none"
                  />
                  {comp.description && (
                    <p className="px-3 pb-3 text-xs text-zinc-500 italic">
                      {comp.description}
                    </p>
                  )}
                  <button 
                    onClick={() => handleRemoveCompetitor(idx)}
                    className="absolute top-3 right-3 text-xs text-zinc-500 hover:text-red-400"
                  >
                    remove
                  </button>
                </div>
              ))}
              <button onClick={handleAddCompetitor} className="text-yellow-500 text-sm hover:text-yellow-400 font-medium">
                + add competitor
              </button>
            </div>
          </div>

          {/* Attributes */}
          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Custom prompt attributes</label>
            <input 
              type="text" 
              value={newAttribute}
              onChange={e => setNewAttribute(e.target.value)}
              onKeyDown={handleAddAttribute}
              placeholder="type an attribute + Enter"
              className="w-full bg-[#111] border border-[#333] rounded p-3 text-white focus:outline-none focus:border-yellow-500 mb-3"
            />
            <p className="text-xs text-zinc-500 mb-3">Useful labels include buyer themes, product lines, audiences, locations, pricing, comparisons, and alternatives.</p>
            <div className="flex flex-wrap gap-2">
              {data.attributes.map(attr => (
                <span key={attr} className="bg-[#222] border border-[#333] px-3 py-1 rounded-full text-xs text-zinc-300 flex items-center gap-1">
                  {attr} <button onClick={() => removeAttribute(attr)} className="text-zinc-500 hover:text-white ml-1">&times;</button>
                </span>
              ))}
            </div>
          </div>

          {/* Search Topics */}
          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Search topics ({data.searchTopics.length})</label>
            <div className="space-y-2">
              {data.searchTopics.map((topic, idx) => (
                <div key={idx} className="flex items-center">
                  <input 
                    type="text" 
                    value={topic}
                    onChange={e => {
                      const newTopics = [...data.searchTopics];
                      newTopics[idx] = e.target.value;
                      setData({...data, searchTopics: newTopics});
                    }}
                    className="flex-1 bg-[#111] border border-[#333] rounded-l p-3 text-white focus:outline-none focus:border-yellow-500"
                  />
                  <button className="bg-[#222] border border-l-0 border-[#333] rounded-r p-3 text-zinc-500 hover:text-white">
                    &times;
                  </button>
                </div>
              ))}
              <button className="bg-[#222] border border-[#333] rounded p-2 px-4 text-zinc-400 hover:text-white text-sm">
                + add
              </button>
            </div>
          </div>

          {/* Prompts per topic */}
          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Prompts per topic</label>
            <div className="flex gap-2">
              {[5, 10, 15, 20].map(num => (
                <button 
                  key={num}
                  onClick={() => setData({...data, promptsPerTopic: num})}
                  className={`w-12 h-10 rounded text-sm font-medium border ${data.promptsPerTopic === num ? 'bg-yellow-600/20 text-yellow-500 border-yellow-600/50' : 'bg-[#111] text-zinc-400 border-[#333] hover:border-[#444]'}`}
                >
                  {num}
                </button>
              ))}
            </div>
          </div>

        </div>

        {/* Footer Actions */}
        <div className="fixed bottom-0 left-64 right-0 p-4 bg-[#0a0a0a]/90 backdrop-blur border-t border-[#222] flex justify-end gap-4 z-10">
           <button onClick={() => onComplete(data)} className="bg-yellow-600 hover:bg-yellow-500 text-black font-semibold py-2 px-6 rounded transition-colors">
              Continue
           </button>
        </div>

      </div>
    </div>
  );
}
