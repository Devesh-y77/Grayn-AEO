"use client";

import React from "react";
import {
  LayoutDashboard,
  Users,
  Activity,
  Key,
  BookOpen,
  ArrowUpCircle,
  Sun,
  User,
  MessageSquare
} from "lucide-react";

interface SidebarProps {
  workspaceName?: string;
}

export default function Sidebar({ workspaceName }: SidebarProps) {
  return (
    <div className="w-64 bg-[#111] border-r border-[#222] flex flex-col h-screen text-sm font-medium text-zinc-400">
      {/* Header */}
      <div className="p-4 border-b border-[#222] flex items-center gap-2">
        <div className="w-6 h-6 rounded bg-gradient-to-tr from-yellow-500 to-amber-600 flex items-center justify-center text-black font-bold">
          O
        </div>
        <span className="text-white font-semibold text-base tracking-wide">OpenLens</span>
      </div>

      {workspaceName && (
        <div className="p-4 border-b border-[#222]">
          <div className="flex items-center justify-between px-2 py-1.5 hover:bg-[#222] rounded cursor-pointer">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded bg-purple-600 flex items-center justify-center text-xs text-white">
                {workspaceName.charAt(0).toUpperCase()}
              </div>
              <span className="text-white truncate w-32">{workspaceName}</span>
            </div>
            <span className="text-xs">▼</span>
          </div>
        </div>
      )}

      {/* Nav Links */}
      <div className="flex-1 py-4 px-2 space-y-1">
        <div className="flex items-center gap-3 px-3 py-2 bg-yellow-600/10 text-yellow-500 rounded-md cursor-pointer">
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </div>
        <div className="flex items-center gap-3 px-3 py-2 hover:text-white hover:bg-[#222] rounded-md cursor-pointer transition-colors">
          <Users size={18} />
          <span>Team</span>
        </div>
        <div className="flex items-center gap-3 px-3 py-2 hover:text-white hover:bg-[#222] rounded-md cursor-pointer transition-colors">
          <Activity size={18} />
          <span>Usage</span>
        </div>
        <div className="flex items-center gap-3 px-3 py-2 hover:text-white hover:bg-[#222] rounded-md cursor-pointer transition-colors">
          <Key size={18} />
          <span>API Keys</span>
        </div>
        <div className="flex items-center justify-between px-3 py-2 hover:text-white hover:bg-[#222] rounded-md cursor-pointer transition-colors">
          <div className="flex items-center gap-3">
            <BookOpen size={18} />
            <span>Docs</span>
          </div>
          <ExternalLinkIcon />
        </div>
        <div className="flex items-center gap-3 px-3 py-2 hover:text-white hover:bg-[#222] rounded-md cursor-pointer transition-colors">
          <ArrowUpCircle size={18} />
          <span>Upgrade</span>
        </div>
      </div>

      {/* Footer Nav */}
      <div className="p-2 border-t border-[#222] space-y-1 pb-4">
        <div className="flex items-center gap-3 px-3 py-2 hover:text-white hover:bg-[#222] rounded-md cursor-pointer transition-colors">
          <Sun size={18} />
          <span>Light mode</span>
        </div>
        <div className="flex items-center justify-between px-3 py-2 hover:text-white hover:bg-[#222] rounded-md cursor-pointer transition-colors mt-2">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-white">
              D
            </div>
            <span>Account</span>
          </div>
          <button className="text-xs bg-[#222] px-2 py-1 rounded text-zinc-300 hover:text-white border border-[#333]">
            Feedback
          </button>
        </div>
      </div>
    </div>
  );
}

const ExternalLinkIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
    <polyline points="15 3 21 3 21 9"></polyline>
    <line x1="10" y1="14" x2="21" y2="3"></line>
  </svg>
);
