import React from "react";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export interface StatCardProps {
  label: string;
  value: string;
  change: string;
  trend?: "up" | "down" | "neutral";
  description?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function StatCard({
  label,
  value,
  change,
  trend = "up",
  description,
  icon,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-800/80 bg-slate-900/50 backdrop-blur-sm p-5 shadow-lg flex flex-col justify-between transition-all duration-200 hover:border-slate-700/80",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {label}
        </span>
        {icon && (
          <div className="p-2 rounded-xl bg-slate-800/70 border border-slate-700/50 text-indigo-400">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-3">
        <div className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
          {value}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between pt-3 border-t border-slate-800/60 text-xs">
        <div className="flex items-center gap-1 font-medium">
          {trend === "up" && (
            <span className="flex items-center gap-1 text-emerald-400">
              <TrendingUp className="w-3.5 h-3.5" />
              {change}
            </span>
          )}
          {trend === "down" && (
            <span className="flex items-center gap-1 text-rose-400">
              <TrendingDown className="w-3.5 h-3.5" />
              {change}
            </span>
          )}
          {trend === "neutral" && (
            <span className="flex items-center gap-1 text-slate-400">
              <Minus className="w-3.5 h-3.5" />
              {change}
            </span>
          )}
        </div>
        {description && (
          <span className="text-[11px] text-slate-500 truncate max-w-[140px]">
            {description}
          </span>
        )}
      </div>
    </div>
  );
}
