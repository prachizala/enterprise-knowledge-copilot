"use client";

import React from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Network, ArrowRight, Layers, ArrowDown } from "lucide-react";

export function GraphPreview() {
  return (
    <Card className="flex flex-col justify-between h-full">
      <div>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <CardTitle>Knowledge Graph</CardTitle>
                <CardDescription>
                  18,420 Entities • 42,830 Relationships
                </CardDescription>
              </div>
            </div>
            <span className="px-2 py-0.5 text-[11px] font-medium rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              Neo4j Preview
            </span>
          </div>
        </CardHeader>

        <CardContent className="pt-2">
          {/* Visual Schematic Diagram placeholder */}
          <div className="relative w-full rounded-xl bg-slate-950/70 border border-slate-800/80 p-6 flex flex-col items-center justify-center overflow-hidden">
            {/* Grid dot background */}
            <div
              className="absolute inset-0 opacity-15"
              style={{
                backgroundImage: "radial-gradient(#818cf8 1px, transparent 1px)",
                backgroundSize: "18px 18px",
              }}
            />

            <div className="relative z-10 w-full max-w-sm flex flex-col items-center">
              {/* Top Node: Project */}
              <div className="px-5 py-2 rounded-xl bg-indigo-950/90 border border-indigo-500/50 text-indigo-200 text-xs font-semibold shadow-md flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                <span>Project</span>
              </div>

              {/* Connecting lines SVG */}
              <div className="w-full flex items-center justify-center my-2">
                <svg className="w-48 h-10 overflow-visible">
                  {/* Vertical stem from Project */}
                  <line
                    x1="96"
                    y1="0"
                    x2="96"
                    y2="16"
                    stroke="#6366f1"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                  />
                  {/* Horizontal distributor */}
                  <line
                    x1="24"
                    y1="16"
                    x2="168"
                    y2="16"
                    stroke="#6366f1"
                    strokeWidth="1.5"
                  />
                  {/* Down arrows to Person, Product, Policy */}
                  <line
                    x1="24"
                    y1="16"
                    x2="24"
                    y2="36"
                    stroke="#38bdf8"
                    strokeWidth="1.5"
                    markerEnd="url(#arrow)"
                  />
                  <line
                    x1="96"
                    y1="16"
                    x2="96"
                    y2="36"
                    stroke="#10b981"
                    strokeWidth="1.5"
                    markerEnd="url(#arrow)"
                  />
                  <line
                    x1="168"
                    y1="16"
                    x2="168"
                    y2="36"
                    stroke="#a855f7"
                    strokeWidth="1.5"
                    markerEnd="url(#arrow)"
                  />
                  <defs>
                    <marker
                      id="arrow"
                      viewBox="0 0 6 6"
                      refX="3"
                      refY="3"
                      markerWidth="4"
                      markerHeight="4"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 6 3 L 0 6 z" fill="#94a3b8" />
                    </marker>
                  </defs>
                </svg>
              </div>

              {/* Bottom Nodes: Person, Product, Policy */}
              <div className="grid grid-cols-3 gap-2 w-full text-center">
                <div className="px-2.5 py-1.5 rounded-lg bg-sky-950/80 border border-sky-500/40 text-sky-200 text-[11px] font-medium">
                  Person
                </div>
                <div className="px-2.5 py-1.5 rounded-lg bg-emerald-950/80 border border-emerald-500/40 text-emerald-200 text-[11px] font-medium">
                  Product
                </div>
                <div className="px-2.5 py-1.5 rounded-lg bg-purple-950/80 border border-purple-500/40 text-purple-200 text-[11px] font-medium">
                  Policy
                </div>
              </div>

              <p className="mt-4 text-[11px] text-slate-400 text-center leading-relaxed">
                Multi-hop semantic ontology connecting enterprise personnel, product dependencies, and regulatory compliance.
              </p>
            </div>
          </div>
        </CardContent>
      </div>

      <div className="p-6 pt-0 mt-2">
        <Link href="/knowledge-graph" className="w-full">
          <Button variant="outline" size="sm" className="w-full justify-between">
            <span>Explore Knowledge Graph</span>
            <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>
    </Card>
  );
}
