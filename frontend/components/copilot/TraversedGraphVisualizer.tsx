"use client";

import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { TraversedSubgraphData } from "@/lib/demo-data";
import { getEntityColor } from "@/components/graph/GraphCanvas";
import {
  Network,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
  Layers,
  Play,
  Pause,
  ChevronRight,
  ChevronLeft,
  X,
  Compass,
  CheckCircle2,
  ArrowRight,
  Eye,
  Sliders,
  Box,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export interface TraversedGraphVisualizerProps {
  subgraph: TraversedSubgraphData;
  queryCategory?: string;
  onClose?: () => void;
  isModal?: boolean;
}

interface SimulatedNode {
  id: string;
  label: string;
  canonical_name?: string;
  display_name?: string;
  entity_type: string;
  description?: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  stepIndex?: number;
}

export function TraversedGraphVisualizer({
  subgraph,
  queryCategory = "multi-hop traversal",
  onClose,
  isModal = false,
}: TraversedGraphVisualizerProps) {
  // Visualization View Mode: 2D Force-Directed vs 3D Isometric Hologram
  const [viewMode, setViewMode] = useState<"2d" | "3d">("2d");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  // 3D Perspective Angles
  const [rotateX, setRotateX] = useState(52);
  const [rotateZ, setRotateZ] = useState(-28);

  // Selected Node/Edge for HUD Details
  const [selectedNode, setSelectedNode] = useState<SimulatedNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<any | null>(null);

  // Step-by-Step Traversal Walkthrough State
  const [activeStep, setActiveStep] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // Fallback if empty
  const rawNodes = subgraph?.nodes || [];
  const rawEdges = subgraph?.edges || [];
  const paths = subgraph?.paths || [];

  // Initialize node layout with physics positions
  const [simNodes, setSimNodes] = useState<SimulatedNode[]>([]);

  useEffect(() => {
    if (!rawNodes || rawNodes.length === 0) return;

    const width = 800;
    const height = 480;
    const cx = width / 2;
    const cy = height / 2;

    const count = rawNodes.length;
    const initial: SimulatedNode[] = rawNodes.map((n, idx) => {
      // Position along radial ellipse with slight staggered depth
      const angle = (idx / Math.max(1, count)) * 2 * Math.PI - Math.PI / 2;
      const radius = count <= 2 ? 140 : count <= 5 ? 180 : 220;
      return {
        ...n,
        x: cx + Math.cos(angle) * radius + (Math.random() - 0.5) * 20,
        y: cy + Math.sin(angle) * (radius * 0.75) + (Math.random() - 0.5) * 20,
        vx: 0,
        vy: 0,
        stepIndex: idx,
      };
    });

    setSimNodes(initial);
    if (initial.length > 0) {
      setSelectedNode(initial[0]);
    }
  }, [subgraph]);

  // Automated traversal step playback
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isPlaying && simNodes.length > 1) {
      timer = setInterval(() => {
        setActiveStep((prev) => {
          const next = (prev + 1) % simNodes.length;
          setSelectedNode(simNodes[next]);
          return next;
        });
      }, 1600);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, simNodes]);

  // Pan interaction
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest(".graph-control-btn")) return;
    setIsDragging(true);
    dragStart.current = {
      x: e.clientX,
      y: e.clientY,
      panX: pan.x,
      panY: pan.y,
    };
  };

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      setPan({
        x: dragStart.current.panX + dx,
        y: dragStart.current.panY + dy,
      });
    },
    [isDragging]
  );

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setRotateX(52);
    setRotateZ(-28);
  };

  // Node position dictionary for fast edge drawing
  const nodePositionMap = useMemo(() => {
    const map = new Map<string, SimulatedNode>();
    simNodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [simNodes]);

  return (
    <div
      ref={containerRef}
      className={`relative flex flex-col bg-slate-950 border border-indigo-500/30 rounded-2xl overflow-hidden shadow-2xl select-none ${
        isModal ? "w-full h-full max-h-[85vh]" : "w-full h-[480px] my-3"
      }`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* Background Cyberpunk Grid */}
      <div
        className="absolute inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(99, 102, 241, 0.4) 1px, transparent 0)`,
          backgroundSize: "28px 28px",
        }}
      />

      {/* Top Header & Visualizer Controls Bar */}
      <div className="relative z-20 px-4 py-3 bg-slate-900/90 border-b border-slate-800 backdrop-blur-md flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <Network className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs sm:text-sm font-bold text-white tracking-wide">
                Traversed Knowledge Subgraph
              </h4>
              <Badge variant="purple" size="sm">
                Neo4j Multi-Hop
              </Badge>
            </div>
            <p className="text-[10px] text-slate-400">
              {simNodes.length} nodes &bull; {rawEdges.length} relationships &bull; {queryCategory}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5 graph-control-btn">
          {/* 2D vs 3D Isometric View Mode Toggle */}
          <div className="bg-slate-950/80 p-0.5 rounded-lg border border-slate-800 flex items-center mr-1">
            <button
              onClick={() => setViewMode("2d")}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-all ${
                viewMode === "2d"
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="2D Interactive Force-Directed Topology"
            >
              2D Force
            </button>
            <button
              onClick={() => setViewMode("3d")}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-all flex items-center gap-1 ${
                viewMode === "3d"
                  ? "bg-cyan-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="3D Holographic Isometric Topology"
            >
              <Box className="w-3 h-3" />
              3D Iso
            </button>
          </div>

          <button
            onClick={() => setZoom((z) => Math.min(2.0, z + 0.15))}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleReset}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs"
            title="Reset Pan & Orbit"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-rose-500/20 hover:text-rose-400 text-slate-400 border border-slate-700 ml-1 text-xs"
              title="Close Visualizer"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Main Canvas Viewport Area */}
      <div className="relative flex-1 overflow-hidden cursor-grab active:cursor-grabbing">
        {/* 3D Holographic Stage Container */}
        <div
          className="w-full h-full flex items-center justify-center transition-transform duration-300 ease-out"
          style={{
            transform:
              viewMode === "3d"
                ? `perspective(1000px) rotateX(${rotateX}deg) rotateZ(${rotateZ}deg) scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`
                : `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
            transformStyle: "preserve-3d",
          }}
        >
          {/* 3D Grid Underlay Plane in 3D Mode */}
          {viewMode === "3d" && (
            <div
              className="absolute w-[900px] h-[600px] rounded-3xl border border-cyan-500/30 pointer-events-none"
              style={{
                transform: "translateZ(-40px)",
                background:
                  "radial-gradient(circle at center, rgba(6, 182, 212, 0.12) 0%, rgba(15, 23, 42, 0.8) 70%)",
                boxShadow: "0 0 80px rgba(6, 182, 212, 0.15) inset",
              }}
            >
              <div className="absolute top-4 left-4 text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest">
                Knowledge Plane // Neo4j Layer 0
              </div>
            </div>
          )}

          {/* SVG Canvas Rendering Traversed Edges & Particles */}
          <svg
            className="w-[900px] h-[520px] overflow-visible pointer-events-none"
            viewBox="0 0 900 520"
          >
            <defs>
              <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#818cf8" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.9" />
              </linearGradient>

              {/* Glowing Arrowhead marker */}
              <marker
                id="arrowhead-glow"
                viewBox="0 0 10 10"
                refX="22"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#22d3ee" />
              </marker>

              {/* Active step glow marker */}
              <marker
                id="arrowhead-active"
                viewBox="0 0 10 10"
                refX="24"
                refY="5"
                markerWidth="8"
                markerHeight="8"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#ec4899" />
              </marker>
            </defs>

            {/* Traversed Directed Edges */}
            {rawEdges.map((edge, idx) => {
              const srcNode = nodePositionMap.get(edge.source);
              const tgtNode = nodePositionMap.get(edge.target);
              if (!srcNode || !tgtNode) return null;

              const isEdgeActive =
                selectedNode &&
                (selectedNode.id === srcNode.id || selectedNode.id === tgtNode.id);

              const isStepActive =
                simNodes[activeStep] &&
                (simNodes[activeStep].id === srcNode.id ||
                  simNodes[activeStep].id === tgtNode.id);

              const mx = (srcNode.x + tgtNode.x) / 2;
              const my = (srcNode.y + tgtNode.y) / 2;

              return (
                <g
                  key={edge.id || `edge-${idx}`}
                  className="pointer-events-auto cursor-pointer"
                  onClick={() => setSelectedEdge(edge)}
                >
                  {/* Subtle connection glow */}
                  <line
                    x1={srcNode.x}
                    y1={srcNode.y}
                    x2={tgtNode.x}
                    y2={tgtNode.y}
                    stroke={isStepActive ? "#ec4899" : isEdgeActive ? "#38bdf8" : "#4f46e5"}
                    strokeWidth={isStepActive ? 4 : isEdgeActive ? 3 : 1.5}
                    strokeOpacity={isStepActive ? 0.9 : isEdgeActive ? 0.8 : 0.4}
                    strokeDasharray={isStepActive ? "6 3" : undefined}
                  />

                  {/* Arrowhead line */}
                  <line
                    x1={srcNode.x}
                    y1={srcNode.y}
                    x2={tgtNode.x}
                    y2={tgtNode.y}
                    stroke="transparent"
                    markerEnd={isStepActive ? "url(#arrowhead-active)" : "url(#arrowhead-glow)"}
                  />

                  {/* Relationship Label Badge */}
                  <g transform={`translate(${mx}, ${my})`}>
                    <rect
                      x="-42"
                      y="-10"
                      width="84"
                      height="20"
                      rx="10"
                      fill="#090d16"
                      stroke={isStepActive ? "#ec4899" : isEdgeActive ? "#06b6d4" : "#334155"}
                      strokeWidth="1"
                    />
                    <text
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill={isStepActive ? "#f472b6" : isEdgeActive ? "#67e8f9" : "#94a3b8"}
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="600"
                    >
                      {edge.type.length > 13 ? `${edge.type.slice(0, 12)}…` : edge.type}
                    </text>
                  </g>
                </g>
              );
            })}
          </svg>

          {/* HTML Nodes overlay with 3D projection & Click HUD */}
          {simNodes.map((node, idx) => {
            const isSelected = selectedNode?.id === node.id;
            const isCurrentStep = simNodes[activeStep]?.id === node.id;
            const colors = getEntityColor(node.entity_type);

            return (
              <div
                key={node.id}
                onClick={() => {
                  setSelectedNode(node);
                  setActiveStep(idx);
                }}
                className={`absolute pointer-events-auto cursor-pointer transition-all duration-200 group flex flex-col items-center justify-center`}
                style={{
                  left: `${node.x}px`,
                  top: `${node.y}px`,
                  transform: `translate(-50%, -50%) ${
                    viewMode === "3d" ? "translateZ(30px)" : ""
                  } ${isCurrentStep ? "scale(1.15)" : isSelected ? "scale(1.08)" : "scale(1)"}`,
                }}
              >
                {/* 3D Vertical Laser Beam to Base Plane in 3D Mode */}
                {viewMode === "3d" && (
                  <div
                    className="absolute w-0.5 h-10 pointer-events-none"
                    style={{
                      transform: "translateY(24px) translateZ(-15px) rotateX(90deg)",
                      background: `linear-gradient(to bottom, ${colors.stroke}, transparent)`,
                    }}
                  />
                )}

                {/* Node Orb with Entity Icon / Glow */}
                <div
                  className={`relative w-12 h-12 rounded-2xl flex items-center justify-center border-2 transition-shadow ${
                    isCurrentStep
                      ? "ring-4 ring-pink-500/40 shadow-xl shadow-pink-500/50 animate-pulse"
                      : isSelected
                      ? "ring-2 ring-cyan-400/50 shadow-lg shadow-cyan-500/30"
                      : "shadow-md shadow-slate-950/80 group-hover:scale-105"
                  }`}
                  style={{
                    backgroundColor: colors.fill,
                    borderColor: isCurrentStep ? "#ec4899" : isSelected ? "#22d3ee" : colors.stroke,
                  }}
                >
                  <Sparkles
                    className="w-5 h-5"
                    style={{
                      color: isCurrentStep ? "#f472b6" : isSelected ? "#67e8f9" : colors.text,
                    }}
                  />

                  {/* Step Sequence Badge (1, 2, 3...) */}
                  <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-slate-900 border border-slate-700 text-[9px] font-mono font-bold text-slate-300 flex items-center justify-center shadow">
                    {idx + 1}
                  </span>
                </div>

                {/* Node Label Capsule */}
                <div
                  className={`mt-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-tight whitespace-nowrap border shadow-sm ${
                    isCurrentStep
                      ? "bg-pink-950/90 border-pink-500/50 text-pink-200"
                      : isSelected
                      ? "bg-slate-900 border-cyan-500/50 text-cyan-200"
                      : "bg-slate-950/90 border-slate-800 text-slate-200"
                  }`}
                >
                  {node.display_name || node.label}
                </div>

                {/* Type Indicator */}
                <span className="text-[8px] font-mono uppercase tracking-wider text-slate-400 mt-0.5">
                  {node.entity_type}
                </span>
              </div>
            );
          })}
        </div>

        {/* Floating Node Details HUD Card */}
        {selectedNode && (
          <div className="absolute bottom-14 left-4 z-30 max-w-sm p-3.5 rounded-xl bg-slate-900/95 border border-indigo-500/30 shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-bottom-2 duration-200">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center border text-xs"
                  style={{
                    backgroundColor: getEntityColor(selectedNode.entity_type).bg,
                    borderColor: getEntityColor(selectedNode.entity_type).stroke,
                    color: getEntityColor(selectedNode.entity_type).text,
                  }}
                >
                  ★
                </div>
                <div>
                  <h5 className="text-xs font-bold text-white leading-tight">
                    {selectedNode.display_name || selectedNode.label}
                  </h5>
                  <Badge variant="purple" size="sm" className="mt-0.5 text-[9px]">
                    {selectedNode.entity_type}
                  </Badge>
                </div>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-500 hover:text-slate-300 text-xs"
              >
                ✕
              </button>
            </div>

            <p className="mt-2 text-[11px] text-slate-300 leading-relaxed">
              {selectedNode.description ||
                "Verified Knowledge Graph entity extracted from enterprise documents and synchronized to Neo4j."}
            </p>

            {/* Connected Relationships Preview */}
            <div className="mt-2.5 pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-400">
              <span>Connected Edges:</span>
              <span className="font-mono text-cyan-400 font-semibold">
                {
                  rawEdges.filter(
                    (e) => e.source === selectedNode.id || e.target === selectedNode.id
                  ).length
                }{" "}
                path(s)
              </span>
            </div>
          </div>
        )}

        {/* 3D Mode Camera Angle Controls in 3D View */}
        {viewMode === "3d" && (
          <div className="absolute top-4 right-4 z-30 flex flex-col gap-1 p-2 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur text-[10px] text-slate-300 graph-control-btn">
            <span className="font-mono font-bold text-cyan-400 uppercase tracking-wider text-[9px] mb-1">
              Hologram Orbit
            </span>
            <div className="grid grid-cols-2 gap-1">
              <button
                onClick={() => setRotateX((x) => Math.min(80, x + 8))}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 font-mono"
              >
                Pitch ▲
              </button>
              <button
                onClick={() => setRotateX((x) => Math.max(10, x - 8))}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 font-mono"
              >
                Pitch ▼
              </button>
              <button
                onClick={() => setRotateZ((z) => z - 15)}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 font-mono"
              >
                Yaw ◀
              </button>
              <button
                onClick={() => setRotateZ((z) => z + 15)}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 font-mono"
              >
                Yaw ▶
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Traversal Stepper Bar (Walkthrough) */}
      <div className="relative z-20 px-4 py-2.5 bg-slate-900/90 border-t border-slate-800 flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`px-3 py-1 rounded-lg font-semibold flex items-center gap-1.5 transition-all ${
              isPlaying
                ? "bg-pink-600 text-white shadow-md shadow-pink-600/30"
                : "bg-indigo-600 hover:bg-indigo-500 text-white shadow"
            }`}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3 h-3" />
                Pause Walkthrough
              </>
            ) : (
              <>
                <Play className="w-3 h-3" />
                Play Traversal
              </>
            )}
          </button>

          <div className="flex items-center gap-1">
            <button
              onClick={() => {
                const prev = Math.max(0, activeStep - 1);
                setActiveStep(prev);
                setSelectedNode(simNodes[prev]);
              }}
              disabled={activeStep <= 0}
              className="p-1 rounded bg-slate-800 disabled:opacity-40 text-slate-300"
              title="Previous Node"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="text-[11px] font-mono text-slate-400 px-1">
              Step {activeStep + 1} / {Math.max(1, simNodes.length)}
            </span>
            <button
              onClick={() => {
                const next = Math.min(simNodes.length - 1, activeStep + 1);
                setActiveStep(next);
                setSelectedNode(simNodes[next]);
              }}
              disabled={activeStep >= simNodes.length - 1}
              className="p-1 rounded bg-slate-800 disabled:opacity-40 text-slate-300"
              title="Next Node"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Active Path Breadcrumbs */}
        <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono text-slate-400 overflow-x-auto max-w-md truncate">
          {paths[0] ? (
            <span className="text-cyan-400 truncate font-semibold">{paths[0]}</span>
          ) : (
            <span className="text-slate-500">
              Traversed {simNodes.length} graph node(s) across Neo4j topology
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
