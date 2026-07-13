import { Loader2, Trash2, FileText } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useKbFiles, useDeleteFile, useClearKb, useKnowledgeBases } from "@/hooks/useApi";
import { useAppStore } from "@/store/appStore";

export function KbManagerDialog({
  open,
  onOpenChange,
  kbName,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  kbName: string;
}) {
  const { data: files, isLoading } = useKbFiles(open ? kbName : null);
  const { data: kbs } = useKnowledgeBases();
  const deleteFile = useDeleteFile();
  const clearKb = useClearKb();
  const { activeKb, setActiveKb } = useAppStore();

  const kb = kbs?.find((k) => k.name === kbName);

  const handleClear = async () => {
    await clearKb.mutateAsync(kbName);
    if (activeKb === kbName) setActiveKb(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Manage “{kbName}”</DialogTitle>
          <DialogDescription>{kb?.description || "Knowledge base contents."}</DialogDescription>
        </DialogHeader>

        <div className="max-h-80 space-y-2 overflow-auto scrollbar-thin">
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading files…
            </div>
          )}
          {files?.length === 0 && !isLoading && (
            <p className="text-sm text-muted-foreground">
              This knowledge base is empty.
            </p>
          )}
          {files?.map((f) => (
            <div
              key={f.file_path}
              className="flex items-center gap-2 rounded-md border border-border p-2"
            >
              <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{f.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {f.chunks} chunk{f.chunks > 1 ? "s" : ""} · {f.preview}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="text-muted-foreground hover:text-destructive"
                disabled={deleteFile.isPending}
                onClick={() =>
                  deleteFile.mutate({ kbName, filePath: f.file_path })
                }
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>

        <div className="flex justify-between border-t border-border pt-3">
          <Button
            variant="destructive"
            onClick={handleClear}
            disabled={clearKb.isPending}
          >
            {clearKb.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Delete knowledge base
          </Button>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
