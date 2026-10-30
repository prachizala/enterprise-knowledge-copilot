"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/Button";
import { CornerDownLeft, Sparkles, Send } from "lucide-react";

export interface CopilotInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  suggestedQuestions?: string[];
  onSelectSuggestion?: (question: string) => void;
}

export function CopilotInput({
  onSend,
  isLoading = false,
  placeholder = "Ask anything about enterprise documents, projects, or policies...",
  suggestedQuestions,
  onSelectSuggestion,
}: CopilotInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSend(text.trim());
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="space-y-3">
      {/* Suggested Questions */}
      {suggestedQuestions && suggestedQuestions.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mr-1">
            Suggested:
          </span>
          {suggestedQuestions.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => {
                if (onSelectSuggestion) onSelectSuggestion(q);
                else setText(q);
              }}
              className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-indigo-300 border border-slate-800 transition-colors text-xs"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input Box */}
      <form
        onSubmit={handleSubmit}
        className="relative rounded-2xl border border-slate-800 bg-slate-900/90 shadow-xl focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 transition-all p-2 sm:p-3"
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={2}
          className="w-full bg-transparent resize-none border-none text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-0 leading-relaxed"
        />

        <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Hybrid GraphRAG Model</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500 hidden sm:inline">
              Press Enter ↵
            </span>
            <Button
              type="submit"
              size="sm"
              variant="primary"
              disabled={!text.trim() || isLoading}
              isLoading={isLoading}
              className="h-8 px-3"
            >
              <span>Ask Copilot</span>
              <Send className="w-3.5 h-3.5 ml-1.5" />
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
