import React from "react";
import { WelcomeSection } from "@/components/dashboard/WelcomeSection";
import { StatCard } from "@/components/ui/StatCard";
import { CopilotCard } from "@/components/dashboard/CopilotCard";
import { GraphPreview } from "@/components/dashboard/GraphPreview";
import { RecentDocuments } from "@/components/dashboard/RecentDocuments";
import { RecentQueries } from "@/components/dashboard/RecentQueries";
import { DASHBOARD_STATS } from "@/lib/demo-data";
import { FileText, Network, Share2, MessageSquare } from "lucide-react";

export default function DashboardPage() {
  const statIcons = {
    docs: <FileText className="w-4 h-4" />,
    entities: <Network className="w-4 h-4" />,
    relationships: <Share2 className="w-4 h-4" />,
    queries: <MessageSquare className="w-4 h-4" />,
  };

  return (
    <div className="space-y-6 pb-8">
      {/* 1. Welcome Section */}
      <WelcomeSection />

      {/* 2. Statistics Cards (4 KPI Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {DASHBOARD_STATS.map((stat) => (
          <StatCard
            key={stat.id}
            label={stat.label}
            value={stat.value}
            change={stat.change}
            trend={stat.trend}
            description={stat.description}
            icon={statIcons[stat.id as keyof typeof statIcons]}
          />
        ))}
      </div>

      {/* 3. Primary AI Copilot Card */}
      <CopilotCard />

      {/* 4. Two-Column Grid: Knowledge Graph Preview + Recent Queries */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GraphPreview />
        <RecentQueries />
      </div>

      {/* 5. Recent Documents Table */}
      <RecentDocuments />
    </div>
  );
}
