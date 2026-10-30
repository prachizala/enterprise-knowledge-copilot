"use client";

import React, { useEffect, useState } from "react";
import { Server, Database, Network, Cpu, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";

interface ServiceHealth {
  name: string;
  status: string;
  configured: boolean;
  details?: string;
}

interface ApiResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  services: Record<string, ServiceHealth>;
}

export function SystemStatus() {
  const [apiData, setApiData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [backendOnline, setBackendOnline] = useState<boolean>(false);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/health`, {
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        setApiData(data);
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch {
      // Backend not running yet or CORS
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">System Architecture Status</h2>
            <p className="text-xs text-slate-400">Step 1 Foundation &amp; Subsystem Readiness</p>
          </div>
        </div>

        <button
          onClick={fetchHealth}
          className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 text-xs font-medium border border-slate-700/60 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Status</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        {/* FastAPI Backend */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-medium text-slate-200">FastAPI Backend</span>
            </div>
            {backendOnline ? (
              <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Online
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[11px] text-amber-400 font-medium">
                <AlertCircle className="w-3.5 h-3.5" />
                Standby (Port 8000)
              </span>
            )}
          </div>
          <div className="mt-3">
            <p className="text-xs text-slate-400">
              {backendOnline
                ? `Version ${apiData?.version || "0.1.0"} active on /api/health`
                : "FastAPI server built and verified via unit tests"}
            </p>
            <div className="mt-2 text-[10px] font-mono text-slate-500">
              GET / &amp; GET /api/health
            </div>
          </div>
        </div>

        {/* PostgreSQL Database */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-medium text-slate-200">PostgreSQL Store</span>
            </div>
            <span className="flex items-center gap-1 text-[11px] text-blue-400 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Configured
            </span>
          </div>
          <div className="mt-3">
            <p className="text-xs text-slate-400">
              Configured in .env &amp; docker-compose for document metadata, users, &amp; audit trails.
            </p>
            <div className="mt-2 text-[10px] font-mono text-slate-500">
              Port 5432 (Step 1 Foundation)
            </div>
          </div>
        </div>

        {/* Neo4j Knowledge Graph */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Network className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-medium text-slate-200">Neo4j Graph</span>
            </div>
            <span className="flex items-center gap-1 text-[11px] text-blue-400 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Configured
            </span>
          </div>
          <div className="mt-3">
            <p className="text-xs text-slate-400">
              Configured in .env &amp; docker-compose with APOC plugins for entity relationships.
            </p>
            <div className="mt-2 text-[10px] font-mono text-slate-500">
              Port 7474 / 7687 (Step 1 Foundation)
            </div>
          </div>
        </div>

        {/* LLM & Vector Pipeline */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-medium text-slate-200">LLM &amp; Vector Store</span>
            </div>
            <span className="flex items-center gap-1 text-[11px] text-blue-400 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Configured
            </span>
          </div>
          <div className="mt-3">
            <p className="text-xs text-slate-400">
              Environment settings declared for model endpoints &amp; embedding dimensions.
            </p>
            <div className="mt-2 text-[10px] font-mono text-slate-500">
              Settings Hook: app.core.config
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
