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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileDropzone } from "./FileDropzone";
import { useCreateKb } from "@/hooks/useApi";
import { useAppStore } from "@/store/appStore";

export function CreateKbDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [name, setName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const createKb = useCreateKb();
  const { provider, model, setActiveKb } = useAppStore();

  const reset = () => {
    setName("");
    setFiles([]);
    createKb.reset();
  };

  const submit = async () => {
    if (!name.trim() || files.length === 0) return;
    const kb = await createKb.mutateAsync({
      name: name.trim(),
      files,
      provider: provider || undefined,
      model: model || undefined,
    });
    setActiveKb(kb.name);
    reset();
    onOpenChange(false);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create knowledge base</DialogTitle>
          <DialogDescription>
            Upload one or more documents. A short description is generated
            automatically to help you tell knowledge bases apart.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="kb-name">Name</Label>
          <Input
            id="kb-name"
            placeholder="e.g. Product Docs"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <FileDropzone files={files} onChange={setFiles} />

        {createKb.isError && (
          <p className="text-sm text-destructive">
            {(createKb.error as Error).message}
          </p>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={createKb.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={!name.trim() || files.length === 0 || createKb.isPending}
          >
            {createKb.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Create &amp; index
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
