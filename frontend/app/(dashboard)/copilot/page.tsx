"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChatMessageList } from "@/components/copilot/ChatMessageList";
import { CopilotInput } from "@/components/copilot/CopilotInput";
import {
  INITIAL_COPILOT_MESSAGES,
  EXAMPLE_QUESTIONS,
  CopilotMessage,
  TraversedSubgraphData,
} from "@/lib/demo-data";
import {
  vectorSearch,
  VectorSearchResultItem,
  VectorSearchResponse,
  sendCopilotChat,
  streamCopilotChat,
  listConversations,
  getConversation,
  submitMessageFeedback,
  ConversationSummary,
} from "@/lib/api";
import { CitationDrawer, CitationDetail } from "@/components/copilot/CitationDrawer";
import { TraversedGraphModal } from "@/components/copilot/TraversedGraphModal";
import {
  Bot,
  Sparkles,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Layers,
  FileText,
  Clock,
  Hash,
  AlertCircle,
  ExternalLink,
  CheckCircle2,
  History,
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  Network,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/Button";

const VECTOR_EXAMPLE_QUERIES = [
  "What are the password and authentication requirements?",
  "Quarterly revenue, EBITDA, and financial profits",
  "Automated testing and branch pull request merge policy",
  "Data backup routines and retention procedures",
];

function CopilotChatContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  // Active workspace mode: "chat" (Live GraphRAG Copilot) or "search" (pgvector Workbench)
  const [activeMode, setActiveMode] = useState<"chat" | "search">("chat");

  // =========================================================================
  // LIVE CONVERSATIONAL COPILOT STATE
  // =========================================================================
  const [messages, setMessages] = useState<CopilotMessage[]>(INITIAL_COPILOT_MESSAGES);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [recentConversations, setRecentConversations] = useState<ConversationSummary[]>([]);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<Record<string, string>>({});
  const [chatError, setChatError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<CitationDetail | null>(null);
  const [activeVisualizerSubgraph, setActiveVisualizerSubgraph] = useState<TraversedSubgraphData | null>(null);
  const [visualizerCategory, setVisualizerCategory] = useState<string>("Neo4j Multi-Hop Traversal");

  // Load recent conversations on mount
  useEffect(() => {
    loadConversationHistory();
  }, []);

  const loadConversationHistory = async () => {
    try {
      const convs = await listConversations(20);
      setRecentConversations(convs);
    } catch {
      // Offline fallback
    }
  };

  const handleSelectConversation = async (convId: string) => {
    try {
      const detail = await getConversation(convId);
      setConversationId(detail.id);
      const convertedMessages: CopilotMessage[] = detail.messages.map((m) => ({
        id: m.id,
        sender: m.sender,
        timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: m.content,
        citations: (m.citations || []).map((c) => ({
          id: Number(c.citation_index),
          title: c.document_name,
          location: c.section_title ? `${c.section_title} (p.${c.page_start || 1})` : `Page ${c.page_start || 1}`,
          snippet: c.excerpt,
        })),
        entitiesMatched: m.retrieval_metadata?.query_analysis?.detected_entities || [],
        traversedSubgraph: m.retrieval_metadata?.traversed_subgraph,
        subgraphInsights: m.retrieval_metadata?.graph_paths_count
          ? `Verified ${m.retrieval_metadata.graph_paths_count} Knowledge Graph path(s) using Neo4j (${m.query_category || "multi-hop"})`
          : undefined,
      }));
      setMessages(convertedMessages);
      setShowHistoryModal(false);
    } catch (err: any) {
      setChatError("Failed to load conversation history.");
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMsg: CopilotMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      timestamp: "Just now",
      text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);
    setChatError(null);

    const assistantMsgId = `copilot-${Date.now()}`;
    let accumulatedText = "";
    let messageCreated = false;

    try {
      await streamCopilotChat(
        {
          message: text,
          conversation_id: conversationId,
          include_graph: true,
          max_depth: 2,
        },
        (token: string) => {
          setIsTyping(false);
          accumulatedText += token;
          if (!messageCreated) {
            messageCreated = true;
            setMessages((prev) => [
              ...prev,
              {
                id: assistantMsgId,
                sender: "copilot",
                timestamp: "Just now",
                text: accumulatedText,
              },
            ]);
          } else {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, text: accumulatedText } : m
              )
            );
          }
        },
        (meta: any) => {
          if (!conversationId && meta?.conversation_id) {
            setConversationId(meta.conversation_id);
            loadConversationHistory();
          }
          if (meta?.traversed_subgraph) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      traversedSubgraph: meta.traversed_subgraph,
                      subgraphInsights: meta.traversed_subgraph?.traversal_stats?.nodes_count
                        ? `Traversed ${meta.traversed_subgraph.traversal_stats.nodes_count} nodes & ${meta.traversed_subgraph.traversal_stats.edges_count} edges in Neo4j (${meta.traversed_subgraph.traversal_stats.query_category || "multi-hop"})`
                        : m.subgraphInsights,
                    }
                  : m
              )
            );
          }
        },
        (citations: any[]) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    citations: (citations || []).map((c: any) => ({
                      id: Number(c.citation_index),
                      title: c.document_name,
                      location: c.section_title ? `${c.section_title} (p.${c.page_start || 1})` : `Page ${c.page_start || 1}`,
                      snippet: c.excerpt,
                      document_id: c.document_id,
                      chunk_id: c.chunk_id,
                      relevance_score: c.relevance_score,
                    })),
                  }
                : m
            )
          );
        },
        (subgraph: any) => {
          if (subgraph) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      traversedSubgraph: subgraph,
                      subgraphInsights: subgraph?.traversal_stats?.nodes_count
                        ? `Traversed ${subgraph.traversal_stats.nodes_count} nodes & ${subgraph.traversal_stats.edges_count} edges in Neo4j (${subgraph.traversal_stats.query_category || "multi-hop"})`
                        : m.subgraphInsights,
                    }
                  : m
              )
            );
          }
        }
      );
    } catch (err: any) {
      console.warn("SSE stream failed, falling back to standard chat:", err);
      try {
        const resp = await sendCopilotChat({
          message: text,
          conversation_id: conversationId,
          include_graph: true,
          max_depth: 2,
        });

        if (!conversationId && resp.conversation_id) {
          setConversationId(resp.conversation_id);
          loadConversationHistory();
        }

        const copilotMsg: CopilotMessage = {
          id: resp.id,
          sender: "copilot",
          timestamp: "Just now",
          text: resp.content,
          citations: (resp.citations || []).map((c) => ({
            id: Number(c.citation_index),
            title: c.document_name,
            location: c.section_title ? `${c.section_title} (p.${c.page_start || 1})` : `Page ${c.page_start || 1}`,
            snippet: c.excerpt,
          })),
          entitiesMatched: resp.retrieval_metadata?.query_analysis?.detected_entities || [],
          traversedSubgraph: resp.retrieval_metadata?.traversed_subgraph,
          subgraphInsights: resp.retrieval_metadata?.graph_paths_count
            ? `Verified ${resp.retrieval_metadata.graph_paths_count} Knowledge Graph path(s) using Neo4j (${resp.query_category || "multi-hop"})`
            : undefined,
        };

        if (messageCreated) {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantMsgId ? copilotMsg : m))
          );
        } else {
          setMessages((prev) => [...prev, copilotMsg]);
        }
      } catch (fallbackErr: any) {
        setChatError(fallbackErr.message || "Failed to reach backend Copilot service.");
      }
    } finally {
      setIsTyping(false);
    }
  };

  const handleFeedback = async (messageId: string, rating: "helpful" | "not_helpful") => {
    try {
      await submitMessageFeedback(messageId, rating);
      setFeedbackSubmitted((prev) => ({ ...prev, [messageId]: rating }));
    } catch {
      setFeedbackSubmitted((prev) => ({ ...prev, [messageId]: rating }));
    }
  };

  const handleResetChat = () => {
    setMessages(INITIAL_COPILOT_MESSAGES);
    setConversationId(null);
    setChatError(null);
  };

  // =========================================================================
  // VECTOR SEARCH WORKBENCH STATE
  // =========================================================================
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [topK, setTopK] = useState(8);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.0);
  const [departmentFilter, setDepartmentFilter] = useState("All");
  const [fileTypeFilter, setFileTypeFilter] = useState("All");

  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<VectorSearchResponse | null>(null);

  const executeVectorSearch = async (queryText: string) => {
    if (!queryText.trim()) return;
    setIsSearching(true);
    setSearchError(null);
    try {
      const resp = await vectorSearch({
        query: queryText.trim(),
        top_k: topK,
        similarity_threshold: similarityThreshold,
        department: departmentFilter !== "All" ? departmentFilter : undefined,
        file_type: fileTypeFilter !== "All" ? fileTypeFilter.toLowerCase() : undefined,
      });
      setSearchResults(resp);
    } catch (err: any) {
      setSearchError(err.message || "Vector search failed. Ensure backend is running.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleVectorSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeVectorSearch(searchQuery);
  };

  const handleSelectExampleQuery = (example: string) => {
    setSearchQuery(example);
    executeVectorSearch(example);
  };

  useEffect(() => {
    if (initialQuery) {
      if (activeMode === "search") {
        executeVectorSearch(initialQuery);
      } else {
        handleSendMessage(initialQuery);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] max-w-5xl mx-auto space-y-4">
      {/* Top Header & Mode Toggle Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            {activeMode === "chat" ? (
              <Bot className="w-5 h-5 text-indigo-400" />
            ) : (
              <Sparkles className="w-5 h-5 text-emerald-400" />
            )}
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
              Enterprise Knowledge Copilot
              {activeMode === "chat" ? (
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-indigo-400" />
                  Live GraphRAG Engine
                </span>
              ) : (
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  Live pgvector Search
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400">
              {activeMode === "chat"
                ? "Grounded enterprise conversational copilot powered by hybrid vector retrieval, Neo4j multi-hop reasoning, and strict citations."
                : "Inspect raw semantic chunk embeddings and cosine similarity scores."}
            </p>
          </div>
        </div>

        {/* View Toggle & Actions */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-slate-900 p-1 rounded-xl border border-slate-800">
            <button
              type="button"
              onClick={() => setActiveMode("chat")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeMode === "chat"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              <span>Grounded Copilot</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveMode("search")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeMode === "search"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span>Vector Workbench</span>
            </button>
          </div>

          {activeMode === "chat" && (
            <>
              <Button
                onClick={() => setShowHistoryModal(true)}
                variant="outline"
                size="sm"
                className="text-xs"
                title="View previous conversation sessions"
              >
                <History className="w-3.5 h-3.5 mr-1" />
                History
              </Button>
              <Button
                onClick={handleResetChat}
                variant="outline"
                size="sm"
                className="text-xs"
                title="Start a new conversation"
              >
                <RefreshCw className="w-3.5 h-3.5 mr-1" />
                New Chat
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {chatError && (
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{chatError}</span>
          </div>
          <button
            onClick={() => setChatError(null)}
            className="text-amber-400 hover:text-amber-300 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 1: LIVE CONVERSATIONAL COPILOT                                       */}
      {/* ========================================================================= */}
      {activeMode === "chat" && (
        <div className="flex-1 flex flex-col min-h-0">
          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto pr-1">
            <ChatMessageList
              messages={messages}
              isTyping={isTyping}
              onSelectCitation={(c) => setSelectedCitation(c)}
              onOpenGraphVisualizer={(subgraph, category) => {
                setActiveVisualizerSubgraph(subgraph);
                if (category) setVisualizerCategory(category);
              }}
            />
          </div>

          {/* Input area */}
          <div className="pt-3 border-t border-slate-800 shrink-0">
            <CopilotInput
              onSend={handleSendMessage}
              isLoading={isTyping}
              placeholder="Ask anything about enterprise documents, projects, or policies..."
              suggestedQuestions={EXAMPLE_QUESTIONS}
              onSelectSuggestion={handleSendMessage}
            />
            <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2 px-1">
              <span className="flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                Anti-prompt injection protected &bull; Grounded truth only
              </span>
              <span>
                {conversationId ? `Session ID: ${conversationId.slice(0, 8)}...` : "New Session"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 2: VECTOR SEARCH WORKBENCH                                           */}
      {/* ========================================================================= */}
      {activeMode === "search" && (
        <div className="flex-1 flex flex-col min-h-0 space-y-3">
          {/* Query Bar */}
          <form
            onSubmit={handleVectorSearchSubmit}
            className="flex flex-col sm:flex-row gap-2 shrink-0"
          >
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Ask or search natural language query (e.g. 'authentication requirements and password policies')..."
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-4 py-2.5 text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 shadow-sm"
              />
            </div>
            <Button
              type="submit"
              variant="primary"
              disabled={isSearching || !searchQuery.trim()}
              className="px-5 py-2.5 text-xs sm:text-sm"
            >
              <Sparkles
                className={`w-4 h-4 mr-1.5 text-emerald-400 ${
                  isSearching ? "animate-spin" : ""
                }`}
              />
              <span>{isSearching ? "Searching..." : "Search Chunks"}</span>
            </Button>
          </form>

          {/* Controls & Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs shrink-0">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-1.5">
                <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-400" />
                <span className="text-slate-400 font-medium">Top K:</span>
                <select
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value={4}>4 Chunks</option>
                  <option value={8}>8 Chunks</option>
                  <option value={15}>15 Chunks</option>
                  <option value={25}>25 Chunks</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-slate-400 font-medium">Department:</span>
                <select
                  value={departmentFilter}
                  onChange={(e) => setDepartmentFilter(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="All">All Departments</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Security">Security</option>
                  <option value="Legal">Legal</option>
                  <option value="Finance">Finance</option>
                  <option value="Operations">Operations</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-slate-400 font-medium">Min Similarity:</span>
                <input
                  type="range"
                  min="0.0"
                  max="0.8"
                  step="0.05"
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                  className="w-20 accent-indigo-500 cursor-pointer"
                />
                <span className="text-slate-300 font-mono text-[11px] w-8">
                  {similarityThreshold.toFixed(2)}
                </span>
              </div>
            </div>

            {searchResults && (
              <div className="flex items-center gap-2 text-slate-400 text-[11px]">
                <Clock className="w-3.5 h-3.5 text-indigo-400" />
                <span>
                  Query embedded &amp; matched in{" "}
                  <strong className="text-slate-200 font-mono">
                    {(searchResults.search_time_ms ?? 0).toFixed(1)}ms
                  </strong>
                </span>
              </div>
            )}
          </div>

          {/* Results Scroll Area */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-1">
            {searchError && (
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-200 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <p>{searchError}</p>
              </div>
            )}

            {searchResults && searchResults.results.length > 0 ? (
              searchResults.results.map((item, index) => (
                <div
                  key={item.chunk_id}
                  className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all space-y-2.5 shadow-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 font-mono text-xs flex items-center justify-center font-bold">
                        #{index + 1}
                      </span>
                      <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-cyan-400" />
                        {item.document_original_filename || item.document_filename}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                        {item.department}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-mono font-bold">
                        <Sparkles className="w-3 h-3" />
                        <span>{(item.similarity_score * 100).toFixed(1)}% match</span>
                      </div>
                    </div>
                  </div>

                  {item.section_header && (
                    <div className="text-[11px] text-indigo-300/90 font-medium flex items-center gap-1">
                      <Layers className="w-3 h-3 text-indigo-400" />
                      <span>{item.section_header}</span>
                    </div>
                  )}

                  <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs sm:text-[13px] leading-relaxed text-slate-200 whitespace-pre-wrap font-sans">
                    {item.content}
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-500 font-mono pt-1">
                    <div className="flex items-center gap-3">
                      <span>Owner: {item.owner}</span>
                      <span>•</span>
                      <span>Length: {item.char_count} chars (~{item.token_count} tokens)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span>ID: {item.chunk_id.slice(0, 8)}...</span>
                      <span>•</span>
                      <span className="text-indigo-400">{item.model}</span>
                    </div>
                  </div>
                </div>
              ))
            ) : searchResults && searchResults.results.length === 0 ? (
              <div className="p-12 text-center text-slate-400 bg-slate-900/30 rounded-2xl border border-slate-800 space-y-2">
                <AlertCircle className="w-8 h-8 text-amber-400/80 mx-auto" />
                <p className="text-sm font-semibold text-slate-200">
                  No chunks matched your query and threshold criteria
                </p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Try lowering the minimum similarity threshold or selecting &ldquo;All Departments&rdquo;.
                </p>
              </div>
            ) : (
              <div className="p-10 text-center text-slate-400 bg-slate-900/20 rounded-2xl border border-dashed border-slate-800 space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-emerald-400 mx-auto">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div className="max-w-md mx-auto space-y-1">
                  <h3 className="text-sm font-semibold text-slate-200">
                    Semantic Vector Search Workbench
                  </h3>
                  <p className="text-xs text-slate-500">
                    Query your ingested enterprise knowledge using dense vector similarity over pgvector chunk embeddings.
                  </p>
                </div>

                <div className="pt-2">
                  <span className="text-xs text-slate-400 font-medium block mb-2">
                    Click to try a sample query:
                  </span>
                  <div className="flex flex-wrap justify-center gap-2 max-w-xl mx-auto">
                    {VECTOR_EXAMPLE_QUERIES.map((q, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => handleSelectExampleQuery(q)}
                        className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/60 hover:border-indigo-500/40 text-xs text-slate-300 hover:text-white transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* History Modal Drawer */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <History className="w-4 h-4 text-indigo-400" />
                Previous Conversations
              </h3>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
              {recentConversations.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-6">
                  No previous conversations found.
                </p>
              ) : (
                recentConversations.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => handleSelectConversation(c.id)}
                    className="w-full text-left p-3 rounded-xl bg-slate-950/70 hover:bg-indigo-600/20 border border-slate-800 hover:border-indigo-500/40 transition-colors flex items-center justify-between group"
                  >
                    <div className="truncate pr-2">
                      <p className="text-xs font-medium text-slate-200 group-hover:text-indigo-200 truncate">
                        {c.title}
                      </p>
                      <p className="text-[10px] text-slate-500">
                        {c.message_count} turn(s) &bull; {new Date(c.updated_at).toLocaleDateString()}
                      </p>
                    </div>
                    <MessageSquare className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 shrink-0" />
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Citation Provenance Drawer */}
      <CitationDrawer
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />

      {/* Interactive 3D/2D Knowledge Graph Visualizer Modal */}
      <TraversedGraphModal
        isOpen={!!activeVisualizerSubgraph}
        onClose={() => setActiveVisualizerSubgraph(null)}
        subgraph={activeVisualizerSubgraph}
        queryCategory={visualizerCategory}
      />
    </div>
  );
}

export default function CopilotPage() {
  return (
    <Suspense
      fallback={
        <div className="p-12 text-center text-slate-400 text-sm">
          Loading Copilot Workspace...
        </div>
      }
    >
      <CopilotChatContent />
    </Suspense>
  );
}
