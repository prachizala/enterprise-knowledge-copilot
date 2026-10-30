"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { GraphNode as ApiGraphNode, GraphEdge as ApiGraphEdge } from "@/lib/api";
import { ZoomIn, ZoomOut, Maximize2, Layers, Compass, Sparkles } from "lucide-react";

export interface PositionedNode extends ApiGraphNode {
  x: number;
  y: number;
}

export interface GraphCanvasProps {
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
  selectedNode: ApiGraphNode | null;
  selectedEdge: ApiGraphEdge | null;
  onSelectNode: (node: ApiGraphNode) => void;
  onSelectEdge: (edge: ApiGraphEdge) => void;
  filteredType?: string;
  isLoading?: boolean;
}

export const ENTITY_COLORS: Record<string, { fill: string; stroke: string; text: string; bg: string }> = {
  ORGANIZATION: { fill: "#312e81", stroke: "#6366f1", text: "#c7d2fe", bg: "rgba(99, 102, 241, 0.2)" },
  PERSON: { fill: "#0c4a6e", stroke: "#0284c7", text: "#bae6fd", bg: "rgba(2, 132, 199, 0.2)" },
  PROJECT: { fill: "#064e3b", stroke: "#10b981", text: "#a7f3d0", bg: "rgba(16, 185, 129, 0.2)" },
  PRODUCT: { fill: "#134e4a", stroke: "#14b8a6", text: "#99f6e4", bg: "rgba(20, 184, 166, 0.2)" },
  POLICY: { fill: "#581c87", stroke: "#a855f7", text: "#e9d5ff", bg: "rgba(168, 85, 247, 0.2)" },
  TECHNOLOGY: { fill: "#78350f", stroke: "#f59e0b", text: "#fde68a", bg: "rgba(245, 158, 11, 0.2)" },
  DEPARTMENT: { fill: "#164e63", stroke: "#06b6d4", text: "#a5f3fc", bg: "rgba(6, 182, 212, 0.2)" },
  LOCATION: { fill: "#881337", stroke: "#f43f5e", text: "#fecdd3", bg: "rgba(244, 63, 94, 0.2)" },
  CONTRACT: { fill: "#7c2d12", stroke: "#ea580c", text: "#fed7aa", bg: "rgba(234, 88, 12, 0.2)" },
  ROLE: { fill: "#831843", stroke: "#db2777", text: "#fbcfe8", bg: "rgba(219, 39, 119, 0.2)" },
  DEFAULT: { fill: "#1e293b", stroke: "#64748b", text: "#cbd5e1", bg: "rgba(100, 116, 139, 0.2)" },
};

export function getEntityColor(type: string) {
  const upper = (type || "").toUpperCase();
  return ENTITY_COLORS[upper] || ENTITY_COLORS.DEFAULT;
}

export function GraphCanvas({
  nodes,
  edges,
  selectedNode,
  selectedEdge,
  onSelectNode,
  onSelectEdge,
  filteredType = "All",
  isLoading = false,
}: GraphCanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  // Compute node positions (radial / force layout)
  const positionedNodes = useMemo(() => {
    if (nodes.length === 0) return [];

    const width = 900;
    const height = 520;
    const cx = width / 2;
    const cy = height / 2;

    const result: PositionedNode[] = [];
    const nodeCount = nodes.length;

    // Check if there is a primary focus node
    const centerNodeId = selectedNode?.id || nodes[0]?.id;
    const centerIndex = nodes.findIndex((n) => n.id === centerNodeId);

    // Identify connected neighbors to center node
    const neighborIds = new Set<string>();
    edges.forEach((e) => {
      if (e.source === centerNodeId) neighborIds.add(e.target);
      if (e.target === centerNodeId) neighborIds.add(e.source);
    });

    const tier1: ApiGraphNode[] = [];
    const tier2: ApiGraphNode[] = [];

    nodes.forEach((n, idx) => {
      if (n.id === centerNodeId) return;
      if (neighborIds.has(n.id)) {
        tier1.push(n);
      } else {
        tier2.push(n);
      }
    });

    // Place center node
    if (centerIndex !== -1) {
      result.push({
        ...nodes[centerIndex],
        x: cx,
        y: cy,
      });
    }

    // Place Tier 1 (1-hop neighbors in circle)
    const r1 = Math.min(180, 50 + tier1.length * 15);
    tier1.forEach((n, idx) => {
      const angle = (2 * Math.PI * idx) / Math.max(tier1.length, 1) - Math.PI / 2;
      result.push({
        ...n,
        x: cx + r1 * Math.cos(angle),
        y: cy + r1 * Math.sin(angle),
      });
    });

    // Place Tier 2 (other nodes in outer circle)
    const r2 = Math.min(270, r1 + 80 + tier2.length * 8);
    tier2.forEach((n, idx) => {
      const angle = (2 * Math.PI * idx) / Math.max(tier2.length, 1) - Math.PI / 4;
      result.push({
        ...n,
        x: cx + r2 * Math.cos(angle),
        y: cy + r2 * Math.sin(angle),
      });
    });

    // Simple spring relaxation to resolve overlaps
    for (let iter = 0; iter < 15; iter++) {
      for (let i = 0; i < result.length; i++) {
        for (let j = i + 1; j < result.length; j++) {
          const dx = result[j].x - result[i].x;
          const dy = result[j].y - result[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const minDist = 65;
          if (dist < minDist) {
            const overlap = (minDist - dist) / 2;
            const fx = (dx / dist) * overlap;
            const fy = (dy / dist) * overlap;
            if (result[i].id !== centerNodeId) {
              result[i].x -= fx;
              result[i].y -= fy;
            }
            if (result[j].id !== centerNodeId) {
              result[j].x += fx;
              result[j].y += fy;
            }
          }
        }
      }
    }

    return result;
  }, [nodes, edges, selectedNode]);

  const nodeMap = useMemo(() => {
    return new Map<string, PositionedNode>(positionedNodes.map((n) => [n.id, n]));
  }, [positionedNodes]);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.15, 2.2));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.15, 0.4));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    dragStart.current = {
      x: e.clientX,
      y: e.clientY,
      panX: pan.x,
      panY: pan.y,
    };
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    setPan({
      x: dragStart.current.panX + dx,
      y: dragStart.current.panY + dy,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div className="relative w-full h-[560px] rounded-2xl border border-slate-800 bg-slate-950/80 overflow-hidden shadow-2xl flex items-center justify-center">
      {/* Background Dot Grid */}
      <div
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(#6366f1 1.2px, transparent 1.2px)",
          backgroundSize: "24px 24px",
        }}
      />

      {isLoading && (
        <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm z-30 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
            <span className="text-xs text-slate-300 font-medium">Loading knowledge graph...</span>
          </div>
        </div>
      )}

      {/* SVG Canvas Area */}
      <svg
        viewBox="0 0 900 520"
        className={`w-full h-full select-none ${isDragging ? "cursor-grabbing" : "cursor-grab"}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <defs>
          <marker
            id="edge-arrow-default"
            viewBox="0 0 10 10"
            refX="25"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#475569" />
          </marker>
          <marker
            id="edge-arrow-selected"
            viewBox="0 0 10 10"
            refX="25"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M 0 1 L 9 5 L 0 9 z" fill="#818cf8" />
          </marker>
        </defs>

        <g
          transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}
          style={{ transformOrigin: "450px 260px", transition: isDragging ? "none" : "transform 0.15s ease-out" }}
        >
          {/* 1. Draw Edges */}
          {edges.map((edge) => {
            const sourceNode = nodeMap.get(edge.source);
            const targetNode = nodeMap.get(edge.target);
            if (!sourceNode || !targetNode) return null;

            const isSelected = selectedEdge?.id === edge.id;
            const isConnectedToSelectedNode =
              selectedNode &&
              (selectedNode.id === edge.source || selectedNode.id === edge.target);

            const midX = (sourceNode.x + targetNode.x) / 2;
            const midY = (sourceNode.y + targetNode.y) / 2;

            const strokeColor = isSelected
              ? "#a855f7"
              : isConnectedToSelectedNode
              ? "#818cf8"
              : "#334155";
            const strokeWidth = isSelected ? "3" : isConnectedToSelectedNode ? "2" : "1.2";

            return (
              <g
                key={edge.id}
                className="cursor-pointer group"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectEdge(edge);
                }}
              >
                {/* Invisible hover hitbox for easier clicking */}
                <line
                  x1={sourceNode.x}
                  y1={sourceNode.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke="transparent"
                  strokeWidth="14"
                />
                <line
                  x1={sourceNode.x}
                  y1={sourceNode.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeDasharray={isConnectedToSelectedNode || isSelected ? "none" : "4 2"}
                  markerEnd={
                    isSelected || isConnectedToSelectedNode
                      ? "url(#edge-arrow-selected)"
                      : "url(#edge-arrow-default)"
                  }
                  className="transition-colors group-hover:stroke-indigo-400"
                />
                {/* Edge Type Label Pill */}
                <g transform={`translate(${midX}, ${midY})`}>
                  <rect
                    x="-32"
                    y="-9"
                    width="64"
                    height="18"
                    rx="4"
                    fill={isSelected ? "#3b0764" : isConnectedToSelectedNode ? "#1e1b4b" : "#0f172a"}
                    stroke={isSelected ? "#c084fc" : isConnectedToSelectedNode ? "#6366f1" : "#1e293b"}
                    strokeWidth="1"
                    className="group-hover:stroke-indigo-400 transition-colors"
                  />
                  <text
                    y="3"
                    textAnchor="middle"
                    fill={isSelected ? "#f5d0fe" : isConnectedToSelectedNode ? "#c7d2fe" : "#94a3b8"}
                    fontSize="8.5"
                    fontFamily="monospace"
                    fontWeight="600"
                    className="pointer-events-none"
                  >
                    {edge.type.length > 11 ? `${edge.type.slice(0, 10)}…` : edge.type}
                  </text>
                </g>
              </g>
            );
          })}

          {/* 2. Draw Nodes */}
          {positionedNodes.map((node) => {
            const isSelected = selectedNode?.id === node.id;
            const isDimmed =
              filteredType !== "All" &&
              (node.entity_type || "").toUpperCase() !== filteredType.toUpperCase();
            const styling = getEntityColor(node.entity_type);
            const displayName = node.display_name || node.label || node.canonical_name;

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectNode(node);
                }}
                className="cursor-pointer transition-all group"
                opacity={isDimmed ? 0.25 : 1}
              >
                {/* Outer Selection Glow Ring */}
                {isSelected && (
                  <circle
                    r="34"
                    fill="none"
                    stroke="#818cf8"
                    strokeWidth="2.5"
                    strokeDasharray="4 2"
                    className="animate-spin"
                    style={{ animationDuration: "14s" }}
                  />
                )}

                {/* Node Circle */}
                <circle
                  r="24"
                  fill={styling.fill}
                  stroke={isSelected ? "#c7d2fe" : styling.stroke}
                  strokeWidth={isSelected ? "3" : "1.5"}
                  className="group-hover:scale-110 transition-transform"
                />

                {/* Node Type Pill Abbreviation */}
                <text
                  y="3"
                  textAnchor="middle"
                  fill={styling.text}
                  fontSize="9"
                  fontWeight="bold"
                  className="pointer-events-none tracking-wider"
                >
                  {(node.entity_type || "ENT").slice(0, 4).toUpperCase()}
                </text>

                {/* Node Title Underneath */}
                <text
                  y="38"
                  textAnchor="middle"
                  fill="#f1f5f9"
                  fontSize="11"
                  fontWeight="600"
                  className="pointer-events-none drop-shadow"
                >
                  {displayName.length > 18 ? `${displayName.slice(0, 16)}…` : displayName}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Canvas Toolbar Controls */}
      <div className="absolute bottom-4 right-4 flex items-center gap-1.5 p-1 rounded-xl bg-slate-900/90 border border-slate-800 shadow-xl backdrop-blur-md z-20">
        <button
          onClick={handleZoomIn}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleReset}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Reset View"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Top Overlay Legend */}
      <div className="absolute top-4 left-4 flex items-center gap-2 text-xs text-slate-400 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-800 backdrop-blur-md z-20">
        <Layers className="w-3.5 h-3.5 text-indigo-400" />
        <span className="font-mono text-[11px] text-slate-300">
          {nodes.length} Nodes • {edges.length} Relationships • Neo4j Active
        </span>
      </div>
    </div>
  );
}
