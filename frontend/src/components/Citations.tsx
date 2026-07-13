import { useState } from "react";
import { FileText, ChevronDown, ChevronRight } from "lucide-react";
import type { Source } from "@/api/types";
import { cn } from "@/lib/utils";

function snippet(text: string, limit = 220): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length <= limit ? flat : flat.slice(0, limit).trimEnd() + "…";
}

export function Citations({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-3 border-t border-border pt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" />
        )}
        {sources.length} source{sources.length > 1 ? "s" : ""}
      </button>
      {open && (
        <ul className="mt-2 space-y-2">
          {sources.map((s) => (
            <li
              key={s.index}
              className="rounded-md border border-border bg-muted/40 p-2 text-xs"
            >
              <div className="flex items-center gap-1.5 font-medium">
                <span className="inline-flex h-4 min-w-4 items-center justify-center rounded bg-primary/15 px-1 text-[10px] text-primary">
                  {s.index}
                </span>
                <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="truncate">{s.source}</span>
                {typeof s.score === "number" && (
                  <span className="ml-auto text-[10px] text-muted-foreground">
                    score {s.score.toFixed(3)}
                  </span>
                )}
              </div>
              <p className="mt-1 text-muted-foreground">{snippet(s.content)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function CitationBadges({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;
  return (
    <div className={cn("mt-2 flex flex-wrap gap-1")}>
      {sources.map((s) => (
        <span
          key={s.index}
          title={`${s.source}: ${snippet(s.content, 120)}`}
          className="inline-flex items-center gap-1 rounded border border-border bg-muted/50 px-1.5 py-0.5 text-[10px] text-muted-foreground"
        >
          [{s.index}] {s.source}
        </span>
      ))}
    </div>
  );
}
