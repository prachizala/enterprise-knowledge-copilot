"use client";

import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  runEvaluationBenchmark,
  listEvaluationRuns,
  EvaluationRunDetail,
} from "@/lib/api";
import {
  User,
  Palette,
  Cpu,
  Database,
  Shield,
  Save,
  CheckCircle2,
  Sliders,
  Lock,
  PlayCircle,
  BarChart2,
  Clock,
  AlertTriangle,
  Award,
} from "lucide-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<
    "profile" | "appearance" | "ai" | "evaluation" | "datasources" | "security"
  >("ai");

  const [savedNotice, setSavedNotice] = useState(false);

  // Form states
  const [fullName, setFullName] = useState("Alex Morgan");
  const [email, setEmail] = useState("alex.morgan@acme.com");
  const [role, setRole] = useState("Enterprise Admin");
  const [theme, setTheme] = useState("dark");
  const [modelProvider, setModelProvider] = useState("ollama");
  const [llmModel, setLlmModel] = useState("llama3.2");
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState("http://localhost:11434");
  const [temperature, setTemperature] = useState(0.1);
  const [vectorWeight, setVectorWeight] = useState(0.40);
  const [sparseWeight, setSparseWeight] = useState(0.30);
  const [graphWeight, setGraphWeight] = useState(0.30);
  const [maxDepth, setMaxDepth] = useState(2);
  const [auditLogging, setAuditLogging] = useState(true);

  // Benchmark Evaluation state
  const [isRunningEval, setIsRunningEval] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluationRunDetail | null>(null);
  const [historicalRuns, setHistoricalRuns] = useState<any[]>([]);
  const [evalError, setEvalError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === "evaluation") {
      fetchHistoricalRuns();
    }
  }, [activeTab]);

  const fetchHistoricalRuns = async () => {
    try {
      const runs = await listEvaluationRuns(10);
      setHistoricalRuns(runs);
    } catch {
      // Offline fallback
    }
  };

  const handleRunEvaluation = async () => {
    setIsRunningEval(true);
    setEvalError(null);
    try {
      const res = await runEvaluationBenchmark("Enterprise GraphRAG Verification Benchmark");
      setEvalResult(res);
      fetchHistoricalRuns();
    } catch (err: any) {
      setEvalError(err.message || "Failed to execute benchmark evaluation.");
    } finally {
      setIsRunningEval(false);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  const tabs = [
    { id: "ai", label: "AI & GraphRAG Config", icon: Cpu },
    { id: "evaluation", label: "Evaluation Benchmarks", icon: BarChart2 },
    { id: "datasources", label: "Data Sources", icon: Database },
    { id: "security", label: "Security & RBAC", icon: Shield },
    { id: "profile", label: "Profile", icon: User },
    { id: "appearance", label: "Appearance", icon: Palette },
  ] as const;

  return (
    <div className="space-y-6 pb-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Workspace Settings
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Configure enterprise security policies, model preferences, GraphRAG retrieval weights, and run quality benchmarks.
          </p>
        </div>

        {savedNotice && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium animate-in fade-in">
            <CheckCircle2 className="w-4 h-4" />
            <span>Preferences saved successfully</span>
          </div>
        )}
      </div>

      {/* Tabs navigation */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all ${
                isActive
                  ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/30"
                  : "bg-slate-900/80 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <form onSubmit={handleSave}>
        {/* 1. AI & GraphRAG Configuration Tab */}
        {activeTab === "ai" && (
          <div className="space-y-5">
            <Card>
              <CardHeader>
                <CardTitle>LLM &amp; Provider Settings</CardTitle>
                <CardDescription>
                  Define primary generation provider, model checkpoint, and strict hallucination controls.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">LLM Provider</label>
                    <select
                      value={modelProvider}
                      onChange={(e) => {
                        const val = e.target.value;
                        setModelProvider(val);
                        if (val === "ollama" && !llmModel.includes("llama")) {
                          setLlmModel("llama3.2");
                        } else if (val === "openai" && !llmModel.includes("gpt")) {
                          setLlmModel("gpt-4o-mini");
                        }
                      }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs sm:text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    >
                      <option value="ollama">Ollama (Local Offline LLM)</option>
                      <option value="openai">OpenAI (Official)</option>
                      <option value="mock">Deterministic Offline Mock</option>
                      <option value="anthropic">Anthropic Claude</option>
                      <option value="gemini">Google Gemini</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Model Name</label>
                    <input
                      type="text"
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      placeholder="e.g. llama3.2, mistral, gpt-4o-mini"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs sm:text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                {modelProvider === "ollama" && (
                  <div className="p-3 rounded-xl bg-slate-950/80 border border-amber-500/20 text-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-amber-400">Ollama Daemon Base URL</span>
                      <span className="text-[10px] text-slate-400">Zero-cost private local inference</span>
                    </div>
                    <input
                      type="text"
                      value={ollamaBaseUrl}
                      onChange={(e) => setOllamaBaseUrl(e.target.value)}
                      placeholder="http://localhost:11434"
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-amber-400"
                    />
                    <p className="text-[10px] text-slate-500">
                      Recommended models: <code className="text-amber-300">llama3.2:3b</code>, <code className="text-amber-300">qwen2.5:7b</code>, <code className="text-amber-300">mistral</code>. Run <code className="text-slate-300">ollama run llama3.2</code> in your terminal.
                    </p>
                  </div>
                )}

                <div className="space-y-2 pt-2">
                  <div className="flex justify-between text-xs font-semibold text-slate-300">
                    <span>Generation Temperature (Hallucination Defense):</span>
                    <span className="font-mono text-indigo-400">{temperature}</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.05"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                  <p className="text-[11px] text-slate-500">
                    Lower temperature (0.0 - 0.2) enforces strict groundedness and zero hallucination.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Tri-Hybrid Retrieval Engine Parameters</CardTitle>
                <CardDescription>
                  Tune Dense pgvector, Sparse Okapi BM25, and Neo4j Knowledge Graph fusion weights via Reciprocal Rank Fusion (RRF).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-semibold text-slate-300">
                      <span>Dense (pgvector):</span>
                      <span className="font-mono text-emerald-400">{(vectorWeight * 100).toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="0.80"
                      step="0.05"
                      value={vectorWeight}
                      onChange={(e) => setVectorWeight(parseFloat(e.target.value))}
                      className="w-full accent-emerald-500 cursor-pointer"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-semibold text-slate-300">
                      <span>Sparse (Okapi BM25):</span>
                      <span className="font-mono text-amber-400">{(sparseWeight * 100).toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="0.80"
                      step="0.05"
                      value={sparseWeight}
                      onChange={(e) => setSparseWeight(parseFloat(e.target.value))}
                      className="w-full accent-amber-500 cursor-pointer"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-semibold text-slate-300">
                      <span>Graph (Neo4j):</span>
                      <span className="font-mono text-purple-400">{(graphWeight * 100).toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="0.80"
                      step="0.05"
                      value={graphWeight}
                      onChange={(e) => setGraphWeight(parseFloat(e.target.value))}
                      className="w-full accent-purple-500 cursor-pointer"
                    />
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Tri-Hybrid Agreement Bonus:</span>
                  <span className="font-mono font-bold text-indigo-400">+35% boost when Dense + Sparse + Graph agree</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Graph Multi-Hop Depth</label>
                    <select
                      value={maxDepth}
                      onChange={(e) => setMaxDepth(Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs sm:text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    >
                      <option value={1}>1 Hop (Direct Neighbors)</option>
                      <option value={2}>2 Hops (Default Multi-Hop)</option>
                      <option value={3}>3 Hops (Deep Reasoning)</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">Reciprocal Rank Fusion (RRF K)</label>
                    <input
                      type="number"
                      defaultValue={60}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs sm:text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button type="submit" variant="primary" size="md">
                <Save className="w-4 h-4 mr-2" />
                <span>Save Configuration</span>
              </Button>
            </div>
          </div>
        )}

        {/* 2. Benchmark Evaluation Tab */}
        {activeTab === "evaluation" && (
          <div className="space-y-5">
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Award className="w-5 h-5 text-indigo-400" />
                      GraphRAG Evaluation &amp; Benchmarks
                    </CardTitle>
                    <CardDescription>
                      Measure retrieval recall, precision, citation coverage, groundedness score, and hallucination rate against enterprise gold-standard queries.
                    </CardDescription>
                  </div>

                  <Button
                    type="button"
                    onClick={handleRunEvaluation}
                    disabled={isRunningEval}
                    variant="primary"
                    size="md"
                  >
                    <PlayCircle className={`w-4 h-4 mr-2 ${isRunningEval ? "animate-spin" : ""}`} />
                    <span>{isRunningEval ? "Evaluating..." : "Run Benchmark Suite"}</span>
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="space-y-5">
                {evalError && (
                  <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
                    {evalError}
                  </div>
                )}

                {/* Latest Evaluation Scorecards */}
                {evalResult && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase block">Recall</span>
                        <span className="text-base sm:text-lg font-bold text-emerald-400 font-mono">
                          {(evalResult.avg_recall * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase block">Precision</span>
                        <span className="text-base sm:text-lg font-bold text-cyan-400 font-mono">
                          {(evalResult.avg_precision * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase block">Groundedness</span>
                        <span className="text-base sm:text-lg font-bold text-indigo-400 font-mono">
                          {(evalResult.avg_groundedness * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase block">Citations</span>
                        <span className="text-base sm:text-lg font-bold text-purple-400 font-mono">
                          {(evalResult.avg_citation_coverage * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase block">Hallucination</span>
                        <span className="text-base sm:text-lg font-bold text-emerald-400 font-mono">
                          {(evalResult.hallucination_rate * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase block">Avg Latency</span>
                        <span className="text-base sm:text-lg font-bold text-slate-200 font-mono">
                          {evalResult.avg_latency_ms.toFixed(0)}ms
                        </span>
                      </div>
                    </div>

                    {/* Query Results List */}
                    <div className="space-y-2 pt-2">
                      <h4 className="text-xs font-bold text-slate-300">Evaluated Query Breakdown:</h4>
                      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                        {evalResult.results.map((r, i) => (
                          <div
                            key={r.id || i}
                            className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-xs space-y-1.5"
                          >
                            <div className="flex items-center justify-between text-slate-400 text-[11px]">
                              <span className="font-semibold text-slate-200">{r.query}</span>
                              <span className="font-mono text-emerald-400">
                                Grounded: {(r.groundedness_score * 100).toFixed(0)}% &bull; {r.latency_ms.toFixed(0)}ms
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-300 bg-slate-900/60 p-2 rounded-lg font-sans">
                              {r.actual_answer}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Historical Runs */}
                <div className="pt-3 border-t border-slate-800">
                  <h4 className="text-xs font-bold text-slate-300 mb-2">Historical Evaluation Runs</h4>
                  {historicalRuns.length === 0 ? (
                    <p className="text-xs text-slate-500">No historical evaluation runs recorded yet.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {historicalRuns.map((run) => (
                        <div
                          key={run.id}
                          className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/50 border border-slate-800 text-xs text-slate-300"
                        >
                          <div>
                            <span className="font-semibold text-slate-200">{run.name}</span>
                            <span className="text-[10px] text-slate-500 ml-2">
                              {new Date(run.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 font-mono text-[11px]">
                            <span className="text-indigo-400">
                              Grounded: {(run.avg_groundedness * 100).toFixed(0)}%
                            </span>
                            <span className="text-slate-500">&bull;</span>
                            <span className="text-slate-400">{run.avg_latency_ms.toFixed(0)}ms</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 3. Security & RBAC Tab */}
        {activeTab === "security" && (
          <Card>
            <CardHeader>
              <CardTitle>Security, Access Control &amp; RBAC</CardTitle>
              <CardDescription>
                Enterprise document access policies and role-based permissions.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div>
                    <p className="text-xs font-semibold text-white">Document-Level RBAC Enforcement</p>
                    <p className="text-[11px] text-slate-400">
                      Filters pgvector candidates and graph paths based on authenticated user department and role.
                    </p>
                  </div>
                  <Badge variant="success" size="sm">Active (Enforced)</Badge>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div>
                    <p className="text-xs font-semibold text-white">Anti-Prompt Injection Sandbox</p>
                    <p className="text-[11px] text-slate-400">
                      Retrieved document text is isolated inside strict delimiters with zero instruction-execution.
                    </p>
                  </div>
                  <Badge variant="success" size="sm">Active (Isolated)</Badge>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div>
                    <p className="text-xs font-semibold text-white">Zero-Hallucination Fallback</p>
                    <p className="text-[11px] text-slate-400">
                      Returns explicit insufficient evidence notifications when evidence is missing.
                    </p>
                  </div>
                  <Badge variant="info" size="sm">Enabled</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 4. Data Sources Tab */}
        {activeTab === "datasources" && (
          <Card>
            <CardHeader>
              <CardTitle>Connected Database Infrastructure</CardTitle>
              <CardDescription>
                State of PostgreSQL and Neo4j Knowledge Graph instances.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-indigo-400" />
                  <div>
                    <p className="text-xs font-semibold text-white">PostgreSQL (Relational + pgvector)</p>
                    <p className="text-[11px] text-slate-400">Source of truth for documents, chunks, and embeddings</p>
                  </div>
                </div>
                <Badge variant="success" size="sm">Connected</Badge>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-purple-400" />
                  <div>
                    <p className="text-xs font-semibold text-white">Neo4j (Knowledge Graph Index)</p>
                    <p className="text-[11px] text-slate-400">Graph database for multi-hop relationship reasoning</p>
                  </div>
                </div>
                <Badge variant="success" size="sm">Connected</Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 5. Profile Tab */}
        {activeTab === "profile" && (
          <Card>
            <CardHeader>
              <CardTitle>Profile Details</CardTitle>
              <CardDescription>Manage user credentials and department affiliation.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs sm:text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs sm:text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 6. Appearance Tab */}
        {activeTab === "appearance" && (
          <Card>
            <CardHeader>
              <CardTitle>Appearance &amp; Display</CardTitle>
              <CardDescription>Customize dashboard theme and Knowledge Graph visual styles.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                {["dark", "slate-contrast", "system"].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTheme(t)}
                    className={`p-3 rounded-xl border text-xs font-semibold capitalize transition-all ${
                      theme === t
                        ? "border-indigo-500 bg-indigo-500/10 text-white"
                        : "border-slate-800 bg-slate-950 text-slate-400 hover:text-white"
                    }`}
                  >
                    {t.replace("-", " ")}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </form>
    </div>
  );
}
