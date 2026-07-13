import { useCallback, useRef, useState } from "react";
import { UploadCloud, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function FileDropzone({
  files,
  onChange,
  accept = ".pdf,.txt,.md,.markdown,.py,.js,.ts,.json,.yaml,.yml,.toml,.cfg,.ini,.sh,.go,.rs,.java,.c,.cpp,.h",
}: {
  files: File[];
  onChange: (files: File[]) => void;
  accept?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const addFiles = useCallback(
    (incoming: FileList | null) => {
      if (!incoming) return;
      const merged = [...files];
      Array.from(incoming).forEach((f) => {
        if (!merged.some((m) => m.name === f.name && m.size === f.size)) {
          merged.push(f);
        }
      });
      onChange(merged);
    },
    [files, onChange]
  );

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border p-6 text-center transition-colors hover:border-primary/50",
          dragOver && "border-primary bg-primary/5"
        )}
      >
        <UploadCloud className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Drag &amp; drop files here, or click to browse
        </p>
        <p className="text-xs text-muted-foreground/70">
          PDF, TXT, Markdown, and code files
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>
      {files.length > 0 && (
        <ul className="mt-3 max-h-40 space-y-1 overflow-auto scrollbar-thin">
          {files.map((f, i) => (
            <li
              key={`${f.name}-${i}`}
              className="flex items-center justify-between rounded-md bg-muted/50 px-2 py-1 text-xs"
            >
              <span className="truncate">{f.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onChange(files.filter((_, idx) => idx !== i));
                }}
                className="ml-2 text-muted-foreground hover:text-destructive"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
