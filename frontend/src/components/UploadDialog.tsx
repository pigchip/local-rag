import { useState } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { FileDropzone } from "./FileDropzone";
import { useAddFiles } from "@/hooks/useApi";
import { useAppStore } from "@/store/appStore";

export function UploadDialog({
  open,
  onOpenChange,
  kbName,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  kbName: string;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const addFiles = useAddFiles();
  const { provider, model } = useAppStore();

  const submit = async () => {
    if (files.length === 0) return;
    await addFiles.mutateAsync({
      kbName,
      files,
      provider: provider || undefined,
      model: model || undefined,
    });
    setFiles([]);
    onOpenChange(false);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          setFiles([]);
          addFiles.reset();
        }
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add files to “{kbName}”</DialogTitle>
          <DialogDescription>
            Upload individual or batch files into this knowledge base.
          </DialogDescription>
        </DialogHeader>

        <FileDropzone files={files} onChange={setFiles} />

        {addFiles.isError && (
          <p className="text-sm text-destructive">
            {(addFiles.error as Error).message}
          </p>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={addFiles.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={files.length === 0 || addFiles.isPending}
          >
            {addFiles.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Upload &amp; index
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
