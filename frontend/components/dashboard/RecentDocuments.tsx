import React from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { FileText, ArrowRight, Clock } from "lucide-react";
import { RECENT_DOCUMENTS } from "@/lib/demo-data";

export function RecentDocuments() {
  const displayDocs = RECENT_DOCUMENTS.slice(0, 4);

  return (
    <Card className="h-full flex flex-col justify-between">
      <div>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <CardTitle>Recent Documents</CardTitle>
                <CardDescription>
                  Enterprise files indexed for hybrid retrieval
                </CardDescription>
              </div>
            </div>
            <Link href="/documents">
              <Button variant="ghost" size="sm" className="text-xs">
                View all <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </Link>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800/80 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 pr-4">Document</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Department</th>
                  <th className="py-2.5 px-3">Updated</th>
                  <th className="py-2.5 pl-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {displayDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-slate-800/30 transition-colors group"
                  >
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition-colors shrink-0" />
                        <span className="font-medium text-slate-200 truncate max-w-[160px] sm:max-w-[200px]">
                          {doc.name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-300">
                        {doc.type}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-400">{doc.department}</td>
                    <td className="py-3 px-3 text-slate-400 whitespace-nowrap">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {doc.updated}
                      </span>
                    </td>
                    <td className="py-3 pl-3 text-right">
                      <Badge variant="success" size="sm">
                        {doc.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </div>

      <div className="p-6 pt-0 mt-2">
        <Link href="/documents" className="w-full">
          <Button variant="outline" size="sm" className="w-full justify-between">
            <span>View all documents</span>
            <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>
    </Card>
  );
}
