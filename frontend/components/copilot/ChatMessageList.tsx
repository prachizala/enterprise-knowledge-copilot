import React from "react";
import { CopilotMessage } from "@/lib/demo-data";
import { Bot, User, BookOpen, Network, CheckCircle2, Copy } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

export interface ChatMessageListProps {
  messages: CopilotMessage[];
  isTyping?: boolean;
  onSelectCitation?: (citation: any) => void;
}

export function ChatMessageList({
  messages,
  isTyping = false,
  onSelectCitation,
}: ChatMessageListProps) {
  return (
    <div className="space-y-6 py-4">
      {messages.map((msg) => {
        const isUser = msg.sender === "user";

        return (
          <div
            key={msg.id}
            className={`flex gap-3.5 sm:gap-4 ${isUser ? "justify-end" : "justify-start"}`}
          >
            {/* Avatar for Copilot */}
            {!isUser && (
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-blue-500 flex items-center justify-center text-white shrink-0 shadow-md shadow-indigo-600/20 mt-0.5">
                <Bot className="w-4 h-4" />
              </div>
            )}

            {/* Bubble Content */}
            <div
              className={`max-w-2xl rounded-2xl p-4 sm:p-5 text-sm ${
                isUser
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20 rounded-tr-none"
                  : "bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none shadow-xl"
              }`}
            >
              <div className="flex items-center justify-between gap-4 mb-1.5 text-[11px] opacity-70">
                <span className="font-semibold">
                  {isUser ? "You" : "Enterprise Knowledge Copilot"}
                </span>
                <span>{msg.timestamp}</span>
              </div>

              {/* Message text */}
              <p className="leading-relaxed whitespace-pre-line text-xs sm:text-sm">
                {msg.text}
              </p>

              {/* Neo4j Subgraph Insights (if copilot response) */}
              {msg.subgraphInsights && (
                <div className="mt-3.5 p-2.5 rounded-xl bg-slate-950/70 border border-indigo-500/20 text-xs text-indigo-300 flex items-start gap-2">
                  <Network className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <div className="text-[11px] leading-snug">
                    <span className="font-semibold text-indigo-200">
                      Graph Traversal Insight:{" "}
                    </span>
                    <span className="font-mono text-slate-300">
                      {msg.subgraphInsights}
                    </span>
                  </div>
                </div>
              )}

              {/* Matched Entities Tags */}
              {msg.entitiesMatched && msg.entitiesMatched.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-800 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mr-1">
                    Entities:
                  </span>
                  {msg.entitiesMatched.map((entity) => (
                    <Badge key={entity} variant="purple" size="sm">
                      {entity}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Grounded Source Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3.5 pt-3 border-t border-slate-800 space-y-2">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-300">
                    <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Verified Source Citations ({msg.citations.length})</span>
                  </div>

                  <div className="grid grid-cols-1 gap-2 pt-1">
                    {msg.citations.map((cite) => (
                      <div
                        key={cite.id}
                        onClick={() => onSelectCitation && onSelectCitation(cite)}
                        className={`p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300 transition-all ${
                          onSelectCitation ? "cursor-pointer hover:border-cyan-500/50 hover:bg-slate-900/90 shadow-sm" : ""
                        }`}
                        title="Click to view full grounded citation in provenance drawer"
                      >
                        <div className="flex items-center justify-between text-[11px] text-cyan-400 font-medium">
                          <span className="flex items-center gap-1">
                            [{cite.id}] {cite.title}
                          </span>
                          <span className="text-slate-500 text-[10px]">
                            {cite.location}
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] text-slate-400 italic">
                          &ldquo;{cite.snippet}&rdquo;
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Avatar for User */}
            {isUser && (
              <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200 shrink-0 shadow mt-0.5">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        );
      })}

      {/* Typing indicator */}
      {isTyping && (
        <div className="flex gap-3.5 sm:gap-4 justify-start">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-blue-500 flex items-center justify-center text-white shrink-0 shadow-md">
            <Bot className="w-4 h-4" />
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-none p-4 flex items-center gap-2 text-xs text-slate-400">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" />
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.2s]" />
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.4s]" />
            <span className="ml-1 text-[11px] text-slate-400">
              Retrieving from Neo4j &amp; Vector Store...
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
