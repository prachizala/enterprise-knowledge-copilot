"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Clock, MessageSquare, ArrowRight, CornerDownLeft } from "lucide-react";
import { RECENT_QUERIES } from "@/lib/demo-data";

export function RecentQueries() {
  const router = useRouter();

  const handleRunQuery = (queryText: string) => {
    router.push(`/copilot?q=${encodeURIComponent(queryText)}`);
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <CardTitle>Recent Queries</CardTitle>
              <CardDescription>
                Audited questions asked across enterprise workspaces
              </CardDescription>
            </div>
          </div>
          <Link href="/copilot" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">
            Open Copilot →
          </Link>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="divide-y divide-slate-800/60">
          {RECENT_QUERIES.map((q) => (
            <div
              key={q.id}
              onClick={() => handleRunQuery(q.query)}
              className="py-3.5 flex items-start justify-between gap-3 group cursor-pointer hover:bg-slate-800/30 px-2 -mx-2 rounded-xl transition-all"
            >
              <div className="space-y-1">
                <p className="text-xs sm:text-sm font-medium text-slate-200 group-hover:text-indigo-300 transition-colors">
                  &ldquo;{q.query}&rdquo;
                </p>
                <div className="flex items-center gap-3 text-[11px] text-slate-500">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {q.timeAgo}
                  </span>
                  <span>•</span>
                  <span>{q.entitiesMatched} Entities matched</span>
                  <span>•</span>
                  <span>{q.sourcesCount} Citations</span>
                </div>
              </div>

              <div className="p-1.5 rounded-lg text-slate-500 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 transition-colors shrink-0 mt-0.5">
                <CornerDownLeft className="w-3.5 h-3.5" />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
