"use client";

import React, { useMemo } from "react";
import { 
  ScatterChart, 
  Scatter, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ZAxis,
  Cell
} from "recharts";
import { SetupData } from "./ConfirmSetupStep";

interface DashboardStepProps {
  reportData: any; // Using any for now, will map to real backend data
  setupData: SetupData;
}

export default function DashboardStep({ reportData, setupData }: DashboardStepProps) {
  
  const vis = reportData?.visibility || {};
  const sov = reportData?.share_of_voice || [];
  const leaderboard = reportData?.leaderboard || [];
  const scorecard = reportData?.platform_scorecard || [];
  const sources = reportData?.brand_citations || [];

  // Safely get top competitor stats
  const topCompetitor = leaderboard.find((l: any) => l.brand_name.toLowerCase() !== setupData.brandName.toLowerCase());

  // Scatter plot data mapping
  const scatterData = useMemo(() => {
    return leaderboard.map((l: any, i: number) => ({
      name: l.brand_name,
      x: i, // We'll just distribute them evenly on x-axis
      y: l.visibility_pct,
      z: 1, // dot size
      fill: l.brand_name.toLowerCase() === setupData.brandName.toLowerCase() ? '#10b981' : 
            i === 1 ? '#f59e0b' : 
            i === 2 ? '#8b5cf6' : 
            i === 3 ? '#ef4444' : '#3b82f6'
    }));
  }, [leaderboard, setupData.brandName]);

  if (!reportData) return <div className="p-8 text-white">Loading report data...</div>;

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0a0a] text-zinc-300 overflow-y-auto overflow-x-hidden">
      
      {/* Top Banner & Header */}
      <div className="p-6 pb-2 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">{setupData.brandName}</h1>
          <p className="text-sm text-zinc-500 mt-1">{setupData.domain}</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="text-sm text-zinc-400 bg-[#111] hover:text-white border border-[#333] px-4 py-2 rounded">Download Report</button>
          <button className="text-sm text-black bg-yellow-600 hover:bg-yellow-500 font-semibold px-4 py-2 rounded">Run Now</button>
        </div>
      </div>

      <div className="px-6 py-2 flex items-center justify-between text-xs text-zinc-500 border-b border-[#222]">
        <div className="flex gap-4">
          <span>Prompts: <strong>All prompts ▼</strong></span>
        </div>
        <div>Last run: <strong>Just now</strong></div>
      </div>

      {/* Main Content */}
      <div className="p-6 max-w-[1600px] w-full mx-auto space-y-6">
        
        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-6">
          <div className="bg-[#111] border border-[#222] rounded-lg p-5 shadow-lg">
            <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-2 uppercase flex justify-between">
              Visibility <span className="text-zinc-600">?</span>
            </h3>
            <div className="text-3xl font-bold text-white mb-1">{vis.visibility_pct}%</div>
            {topCompetitor && (
              <div className="text-xs text-zinc-500">{topCompetitor.brand_name} {topCompetitor.visibility_pct}%</div>
            )}
          </div>
          <div className="bg-[#111] border border-[#222] rounded-lg p-5 shadow-lg">
            <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-2 uppercase flex justify-between">
              Share of Voice <span className="text-zinc-600">?</span>
            </h3>
            <div className="text-3xl font-bold text-white mb-1">{sov[0]?.share_pct || 0}%</div>
            <div className="text-xs text-zinc-500">of {sov.length} brands</div>
          </div>
          <div className="bg-[#111] border border-[#222] rounded-lg p-5 shadow-lg">
            <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-2 uppercase flex justify-between">
              Avg Position <span className="text-zinc-600">?</span>
            </h3>
            <div className="text-3xl font-bold text-white mb-1">#{leaderboard.find((l:any) => l.brand_name.toLowerCase() === setupData.brandName.toLowerCase())?.avg_position || '-'}</div>
            {topCompetitor && (
              <div className="text-xs text-zinc-500">{topCompetitor.brand_name} #{topCompetitor.avg_position || '-'}</div>
            )}
          </div>
          <div className="bg-[#111] border border-[#222] rounded-lg p-5 shadow-lg relative overflow-hidden">
            <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-yellow-600/10 to-transparent pointer-events-none" />
            <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-2 uppercase flex justify-between">
              Mentions
            </h3>
            <div className="text-3xl font-bold text-white mb-1">{leaderboard.find((l:any) => l.brand_name.toLowerCase() === setupData.brandName.toLowerCase())?.mention_count || 0}</div>
            <div className="text-xs text-zinc-500">responses cited brand</div>
          </div>
        </div>

        {/* 2 Column Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          
          {/* Left Column (Main Stats) */}
          <div className="xl:col-span-2 space-y-6">
            
            {/* Platform Scorecard */}
            <div className="bg-[#111] border border-[#222] rounded-lg p-6 shadow-lg">
              <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-6 uppercase flex justify-between">
                Platform Scorecard <span className="text-zinc-600">?</span>
              </h3>
              
              <div className="space-y-6">
                <div className="grid grid-cols-12 text-xs text-zinc-500 font-medium pb-2 border-b border-[#222]">
                  <div className="col-span-2">PLATFORM</div>
                  <div className="col-span-4 text-center">YOUR VISIBILITY</div>
                  <div className="col-span-3 text-center">TOP COMPETITOR</div>
                  <div className="col-span-2 text-center">GAP</div>
                  <div className="col-span-1 text-right">STATUS</div>
                </div>
                
                {scorecard.map((s: any, idx: number) => (
                  <div key={idx} className="grid grid-cols-12 items-center text-sm">
                    <div className="col-span-2 font-medium text-white flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-zinc-600" />
                      {s.platform}
                    </div>
                    <div className="col-span-4 flex items-center gap-3 justify-center">
                      <div className="flex-1 max-w-[100px] h-1.5 bg-[#222] rounded-full overflow-hidden">
                        <div className="h-full bg-yellow-500" style={{ width: `${s.your_visibility}%` }} />
                      </div>
                      <span className="text-zinc-400 w-8">{s.your_visibility}%</span>
                    </div>
                    <div className="col-span-3 flex items-center gap-3 justify-center text-zinc-500">
                      <div className="flex-1 max-w-[80px] h-1.5 bg-[#222] rounded-full overflow-hidden">
                        <div className="h-full bg-zinc-600" style={{ width: `${s.top_competitor_visibility}%` }} />
                      </div>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className={`${s.gap > 0 ? 'text-emerald-400' : s.gap < 0 ? 'text-red-400' : 'text-zinc-400'}`}>
                        {s.gap > 0 ? '+' : ''}{s.gap}%
                      </span>
                    </div>
                    <div className="col-span-1 flex justify-end">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-medium border ${
                        s.status === 'Leading' ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' :
                        s.status === 'Behind' ? 'text-red-400 bg-red-400/10 border-red-400/20' :
                        'text-zinc-400 bg-zinc-800 border-zinc-700'
                      }`}>
                        {s.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Visibility Trend (Scatter) */}
            <div className="bg-[#111] border border-[#222] rounded-lg p-6 shadow-lg h-80">
              <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-2 uppercase flex justify-between">
                Visibility Trend <span className="text-zinc-600">?</span>
              </h3>
              <div className="h-48 w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 0, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                    <XAxis type="number" dataKey="x" hide domain={[-1, scatterData.length]} />
                    <YAxis type="number" dataKey="y" stroke="#555" tick={{ fill: '#666', fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                    <ZAxis type="number" range={[50, 50]} />
                    <Tooltip 
                      cursor={{ strokeDasharray: '3 3' }} 
                      contentStyle={{ backgroundColor: '#111', borderColor: '#333', color: '#fff', fontSize: '12px' }}
                      formatter={(val: any, name: any, props: any) => [val + '%', props.payload.name]}
                    />
                    <Scatter name="Visibility" data={scatterData} fill="#8884d8">
                      {scatterData.map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
              <div className="flex items-center justify-center gap-4 mt-2 flex-wrap">
                {scatterData.map((d: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-zinc-400">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: d.fill }} />
                    {d.name}
                  </div>
                ))}
              </div>
            </div>

            {/* Competitive Landscape Table */}
            <div className="bg-[#111] border border-[#222] rounded-lg p-6 shadow-lg">
              <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-6 uppercase flex justify-between">
                Competitive Landscape <span className="text-zinc-600">?</span>
              </h3>
              <table className="w-full text-sm">
                <thead className="text-xs text-zinc-500 font-medium border-b border-[#222]">
                  <tr>
                    <th className="text-left pb-3 font-medium">RANK</th>
                    <th className="text-left pb-3 font-medium">BRAND</th>
                    <th className="text-left pb-3 font-medium">VISIBILITY</th>
                    <th className="text-left pb-3 font-medium">SHARE OF VOICE</th>
                    <th className="text-center pb-3 font-medium">POSITION</th>
                    <th className="text-right pb-3 font-medium">SENTIMENT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#222]">
                  {leaderboard.map((l: any, idx: number) => {
                    const isTarget = l.brand_name.toLowerCase() === setupData.brandName.toLowerCase();
                    return (
                      <tr key={idx}>
                        <td className="py-4 text-zinc-500">{l.rank}</td>
                        <td className="py-4 font-medium text-white flex items-center gap-2">
                          {l.brand_name}
                          {isTarget && <span className="text-[9px] bg-yellow-600/20 text-yellow-500 px-1.5 py-0.5 rounded uppercase tracking-wide">You</span>}
                        </td>
                        <td className="py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-24 h-1.5 bg-[#222] rounded-full overflow-hidden">
                              <div className={`h-full ${isTarget ? 'bg-yellow-500' : 'bg-zinc-600'}`} style={{ width: `${l.visibility_pct}%` }} />
                            </div>
                            <span className="text-zinc-400 text-xs">{l.visibility_pct}%</span>
                          </div>
                        </td>
                        <td className="py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-24 h-1.5 bg-[#222] rounded-full overflow-hidden">
                              <div className={`h-full ${isTarget ? 'bg-yellow-600' : 'bg-zinc-700'}`} style={{ width: `${l.share_pct}%` }} />
                            </div>
                            <span className="text-zinc-400 text-xs">{l.share_pct}%</span>
                          </div>
                        </td>
                        <td className="py-4 text-center text-white">
                          #{l.avg_position || '-'}
                        </td>
                        <td className="py-4 text-right">
                          <span className={`text-xs px-2 py-1 rounded font-medium ${
                            l.sentiment === 'Positive' ? 'text-emerald-400 bg-emerald-400/10' :
                            l.sentiment === 'Negative' ? 'text-red-400 bg-red-400/10' :
                            'text-zinc-400 bg-zinc-800'
                          }`}>
                            {l.sentiment}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

          </div>

          {/* Right Column (Sidebar Stats) */}
          <div className="xl:col-span-1 space-y-6">
            
            {/* Search Topics */}
            <div className="bg-[#111] border border-[#222] rounded-lg p-6 shadow-lg">
              <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-4 uppercase">
                Search Topics
              </h3>
              <div className="space-y-3">
                {setupData.searchTopics.map((topic, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 shrink-0" />
                    <span className="text-sm text-zinc-300 truncate" title={topic}>{topic}</span>
                  </div>
                ))}
              </div>
              <button className="text-xs text-zinc-500 mt-4 hover:text-white">Manage topics &rarr;</button>
            </div>

            {/* AI Sources */}
            <div className="bg-[#111] border border-[#222] rounded-lg shadow-lg flex flex-col h-[800px]">
              <div className="p-6 border-b border-[#222]">
                <h3 className="text-xs font-semibold text-zinc-500 tracking-wider mb-1 uppercase">AI Sources</h3>
                <p className="text-sm text-white">Top 10</p>
              </div>
              
              <div className="flex-1 overflow-y-auto p-2">
                {sources.slice(0, 20).map((s: any, idx: number) => {
                  
                  // Map source_type to a styled tag
                  let typeClass = "bg-zinc-800 text-zinc-400";
                  let typeLabel = s.source_type || "third-party";
                  if (s.is_brand_citation) { typeClass = "bg-blue-500/20 text-blue-400"; typeLabel = "own"; }
                  else if (s.source_type === "community") typeClass = "bg-purple-500/20 text-purple-400";
                  else if (s.source_type === "competitor") typeClass = "bg-orange-500/20 text-orange-400";
                  else if (s.source_type === "review") typeClass = "bg-emerald-500/20 text-emerald-400";

                  return (
                    <div key={idx} className="p-4 hover:bg-[#1a1a1a] rounded cursor-pointer border-b border-[#222] last:border-0">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-zinc-500 text-xs mt-0.5">&gt;</span>
                          <span className="text-white font-medium text-sm">{s.domain}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold ${typeClass}`}>
                            {typeLabel}
                          </span>
                        </div>
                        <span className="text-white font-semibold text-sm">{s.count}</span>
                      </div>
                      <div className="text-xs text-zinc-500 ml-4 flex items-center gap-1.5">
                        <span className="w-3 h-3 text-[10px] bg-[#333] rounded-full flex items-center justify-center text-zinc-300 shadow">C</span>
                        <span className="w-3 h-3 text-[10px] bg-[#333] rounded-full flex items-center justify-center text-zinc-300 shadow">G</span>
                        <span className="w-3 h-3 text-[10px] bg-[#333] rounded-full flex items-center justify-center text-zinc-300 shadow">P</span>
                        <span className="truncate ml-1">ChatGPT • Google AI • Perplexity</span>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="p-4 border-t border-[#222] text-center">
                <button className="text-xs text-zinc-500 hover:text-white">View all sources</button>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
