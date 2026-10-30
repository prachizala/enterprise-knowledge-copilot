import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Bot, Sparkles, ArrowRight } from "lucide-react";

export function WelcomeSection() {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-2">
      <div>
        <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Good evening</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
          Enterprise Knowledge Copilot
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Search and understand your organization&apos;s knowledge.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Link href="/copilot">
          <Button variant="primary" size="md">
            <Bot className="w-4 h-4 mr-2" />
            <span>Ask the Copilot</span>
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </Link>
      </div>
    </div>
  );
}
