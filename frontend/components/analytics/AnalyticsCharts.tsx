import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { ANALYTICS_DATA } from "@/lib/demo-data";
import { BarChart2, PieChart, Activity, Zap, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

export function AnalyticsCharts() {
  const maxWeekly = Math.max(...ANALYTICS_DATA.weeklyQueries.map((d) => d.count));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 1. Weekly Query Volume (Bar Chart via SVG & Tailwind) */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <BarChart2 className="w-5 h-5" />
              </div>
              <div>
                <CardTitle>Query Volume (Last 7 Days)</CardTitle>
                <CardDescription>
                  Daily GraphRAG questions processed across all departments
                </CardDescription>
              </div>
            </div>
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5" /> +18.3%
            </span>
          </div>
        </CardHeader>

        <CardContent>
          <div className="h-56 flex items-end justify-between gap-3 pt-6 pb-2 px-2">
            {ANALYTICS_DATA.weeklyQueries.map((item) => {
              const heightPercent = Math.round((item.count / maxWeekly) * 100);

              return (
                <div
                  key={item.day}
                  className="flex-1 flex flex-col items-center gap-2 group h-full justify-end"
                >
                  <span className="text-[10px] font-mono text-indigo-300 opacity-0 group-hover:opacity-100 transition-opacity">
                    {item.count}
                  </span>
                  <div
                    className="w-full max-w-[42px] bg-gradient-to-t from-indigo-600 to-sky-400 rounded-t-lg group-hover:from-indigo-500 group-hover:to-sky-300 transition-all shadow-md shadow-indigo-600/20"
                    style={{ height: `${heightPercent}%` }}
                  />
                  <span className="text-[11px] font-semibold text-slate-400 group-hover:text-white transition-colors">
                    {item.day}
                  </span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* 2. Entity Distribution by Type */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <PieChart className="w-5 h-5" />
              </div>
              <div>
                <CardTitle>Knowledge Graph Entity Breakdown</CardTitle>
                <CardDescription>
                  Ontology distribution across 18,420 mapped nodes
                </CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {ANALYTICS_DATA.entityDistribution.map((item) => (
            <div key={item.type} className="space-y-1.5 text-xs">
              <div className="flex justify-between font-medium">
                <span className="text-slate-300">{item.type}</span>
                <span className="text-slate-400 font-mono">
                  {item.percentage}% ({item.count} nodes)
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full rounded-full ${item.color} transition-all duration-500`}
                  style={{ width: `${item.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* 3. Retrieval Latency Breakdown */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <CardTitle>Hybrid RAG Latency Pipeline (Avg. 420ms)</CardTitle>
              <CardDescription>
                Execution profile from user prompt to citation synthesis
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Stacked bar visual */}
          <div className="h-3 w-full rounded-full bg-slate-800 flex overflow-hidden">
            <div className="h-full bg-sky-500" style={{ width: "26%" }} title="Vector Search: 110ms" />
            <div className="h-full bg-indigo-500" style={{ width: "33%" }} title="Neo4j Graph: 140ms" />
            <div className="h-full bg-amber-500" style={{ width: "10%" }} title="Hybrid Rerank: 40ms" />
            <div className="h-full bg-emerald-500" style={{ width: "31%" }} title="LLM Citation: 130ms" />
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
            {ANALYTICS_DATA.latencyBreakdown.map((stage) => (
              <div
                key={stage.stage}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1"
              >
                <span className="text-slate-400 text-[11px] font-medium">
                  {stage.stage}
                </span>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white font-mono">
                    {stage.durationMs} ms
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {stage.percentage}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 4. Top Queried Entities Leaderboard */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <CardTitle>Most Queried Knowledge Nodes</CardTitle>
              <CardDescription>
                High-centrality entities referenced in corporate inquiries
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          <div className="divide-y divide-slate-800/60">
            {ANALYTICS_DATA.topEntitiesQueried.map((item, idx) => (
              <div
                key={item.name}
                className="py-3 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-3">
                  <span className="w-5 text-center font-bold text-slate-500 font-mono">
                    #{idx + 1}
                  </span>
                  <div>
                    <p className="font-semibold text-white">{item.name}</p>
                    <p className="text-[10px] text-slate-400">{item.department}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Badge variant="purple" size="sm">
                    {item.type}
                  </Badge>
                  <span className="font-mono text-slate-300 font-semibold text-[11px]">
                    {item.queryCount} queries
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
