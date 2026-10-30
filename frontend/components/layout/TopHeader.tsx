"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, Bell, CheckCircle2, ChevronRight, Sparkles } from "lucide-react";

export interface TopHeaderProps {
  onToggleSidebar?: () => void;
}

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/copilot": "AI Copilot",
  "/documents": "Documents",
  "/knowledge-graph": "Knowledge Graph",
  "/analytics": "Analytics",
  "/settings": "Settings",
};

export function TopHeader({ onToggleSidebar }: TopHeaderProps) {
  const pathname = usePathname();
  const currentTitle = PAGE_TITLES[pathname] || "Dashboard";
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md px-4 sm:px-6">
      <div className="flex items-center justify-between h-full">
        {/* Left Side: Mobile toggle + Breadcrumb / Page Title */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            className="p-2 -ml-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2 text-xs sm:text-sm">
            <span className="text-slate-400 font-medium hidden sm:inline">
              Workspace
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-600 hidden sm:inline" />
            <h1 className="font-semibold text-white text-sm sm:text-base">
              {currentTitle}
            </h1>
          </div>
        </div>

        {/* Right Side: System Status, Notifications, User Avatar */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* System Status: Operational */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="hidden sm:inline">System Status:</span>
            <span>Operational</span>
          </div>

          {/* Notification Icon */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/80 border border-slate-800 transition-colors"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-indigo-500 ring-2 ring-slate-950" />
            </button>

            {/* Notification Popover preview */}
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-72 rounded-2xl border border-slate-800 bg-slate-900 p-4 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs font-semibold text-white">
                  <span>Notifications</span>
                  <span className="text-indigo-400 text-[11px]">2 New</span>
                </div>
                <div className="mt-2 space-y-2 text-xs">
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800">
                    <p className="font-medium text-slate-200">
                      Security Policy.pdf processed
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      142 entities extracted to Neo4j • 2h ago
                    </p>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800">
                    <p className="font-medium text-slate-200">
                      Weekly hybrid retrieval report
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Query accuracy at 98.4% • 5h ago
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* User Avatar */}
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-sky-400 flex items-center justify-center font-bold text-white text-xs shadow-inner ring-1 ring-slate-700">
              AM
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
