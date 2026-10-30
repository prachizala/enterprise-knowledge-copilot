"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Bot, ArrowRight, CornerDownLeft, Sparkles } from "lucide-react";
import { EXAMPLE_QUESTIONS } from "@/lib/demo-data";

export function CopilotCard() {
  const router = useRouter();
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      router.push(`/copilot?q=${encodeURIComponent(question.trim())}`);
    } else {
      router.push("/copilot");
    }
  };

  const handleSelectExample = (example: string) => {
    setQuestion(example);
  };

  return (
    <Card className="relative overflow-hidden border-indigo-500/20 bg-gradient-to-b from-slate-900/90 to-slate-950/90 shadow-2xl">
      {/* Subtle background glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

      <CardHeader className="pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2.5 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <CardTitle className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              Ask your enterprise knowledge
              <Sparkles className="w-4 h-4 text-indigo-400" />
            </CardTitle>
            <CardDescription className="text-xs sm:text-sm text-slate-400">
              Search across documents, projects, policies, people and relationships.
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        {/* Search input form */}
        <form onSubmit={handleSubmit} className="relative mt-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What would you like to know?"
            className="w-full pl-4 pr-32 py-3.5 bg-slate-950/80 border border-slate-700/80 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all shadow-inner"
          />

          <div className="absolute inset-y-1.5 right-1.5 flex items-center">
            <Button type="submit" variant="primary" size="sm" className="h-9 px-3">
              <span>Ask Copilot</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
            </Button>
          </div>
        </form>

        {/* Example Questions */}
        <div className="space-y-2 pt-1">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Example queries:
          </span>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUESTIONS.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => handleSelectExample(ex)}
                className="text-left text-xs px-3 py-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-indigo-300 border border-slate-700/50 hover:border-indigo-500/30 transition-all active:scale-[0.98]"
              >
                &ldquo;{ex}&rdquo;
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
