import { useState } from "react";
import {
  Plus,
  MessageSquare,
  Trash2,
  Database,
  Settings2,
  FolderPlus,
  Upload,
  Library,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ProviderPicker } from "./ProviderPicker";
import {
  useSessions,
  useKnowledgeBases,
  useCreateSession,
  useDeleteSession,
} from "@/hooks/useApi";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/lib/utils";

export function Sidebar({
  onCreateKb,
  onUpload,
  onManageKb,
}: {
  onCreateKb: () => void;
  onUpload: () => void;
  onManageKb: () => void;
}) {
  const { data: sessions } = useSessions();
  const { data: kbs } = useKnowledgeBases();
  const createSession = useCreateSession();
  const deleteSession = useDeleteSession();
  const {
    activeSessionId,
    setActiveSession,
    activeKb,
    setActiveKb,
    provider,
    model,
  } = useAppStore();
  const [showSettings, setShowSettings] = useState(false);

  const newChat = async () => {
    const s = await createSession.mutateAsync({
      title: "New chat",
      kb_name: activeKb,
      provider,
      model,
    });
    setActiveSession(s.id);
  };

  const activeKbMeta = kbs?.find((k) => k.name === activeKb);

  return (
    <aside className="flex h-full w-72 flex-col border-r border-border bg-card/40">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/15">
          <Library className="h-4 w-4 text-primary" />
        </div>
        <div>
          <h1 className="text-sm font-semibold leading-tight">Local RAG</h1>
          <p className="text-[11px] text-muted-foreground">Retrieval-augmented chat</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto h-8 w-8"
          onClick={() => setShowSettings((s) => !s)}
        >
          <Settings2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Knowledge base switcher */}
      <div className="space-y-2 px-3 pb-2">
        <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
          <Database className="h-3.5 w-3.5" /> Knowledge base
        </label>
        <Select
          value={activeKb ?? undefined}
          onValueChange={(v) => setActiveKb(v)}
        >
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Select a knowledge base" />
          </SelectTrigger>
          <SelectContent>
            {kbs?.length === 0 && (
              <div className="px-2 py-1.5 text-xs text-muted-foreground">
                No knowledge bases yet
              </div>
            )}
            {kbs?.map((kb) => (
              <SelectItem key={kb.name} value={kb.name}>
                {kb.name} · {kb.file_count} file{kb.file_count === 1 ? "" : "s"}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {activeKbMeta?.description && (
          <p className="line-clamp-2 text-[11px] leading-snug text-muted-foreground">
            {activeKbMeta.description}
          </p>
        )}
        <div className="flex gap-1">
          <Button variant="outline" size="sm" className="h-7 flex-1 text-xs" onClick={onCreateKb}>
            <FolderPlus className="h-3.5 w-3.5" /> New
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 flex-1 text-xs"
            onClick={onUpload}
            disabled={!activeKb}
          >
            <Upload className="h-3.5 w-3.5" /> Upload
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 flex-1 text-xs"
            onClick={onManageKb}
            disabled={!activeKb}
          >
            <Settings2 className="h-3.5 w-3.5" /> Manage
          </Button>
        </div>
      </div>

      {showSettings && (
        <div className="border-y border-border bg-muted/30 px-3 py-3">
          <ProviderPicker />
        </div>
      )}

      {/* New chat */}
      <div className="px-3 py-2">
        <Button className="w-full" onClick={newChat} disabled={createSession.isPending}>
          <Plus className="h-4 w-4" /> New chat
        </Button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-auto scrollbar-thin px-2 pb-3">
        <p className="px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          History
        </p>
        <ul className="space-y-0.5">
          {sessions?.map((s) => (
            <li key={s.id}>
              <div
                className={cn(
                  "group flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors hover:bg-accent",
                  activeSessionId === s.id && "bg-accent"
                )}
                onClick={() => setActiveSession(s.id)}
              >
                <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1 truncate">{s.title}</span>
                <button
                  className="opacity-0 transition-opacity group-hover:opacity-100"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession.mutate(s.id);
                    if (activeSessionId === s.id) setActiveSession(null);
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                </button>
              </div>
            </li>
          ))}
          {sessions?.length === 0 && (
            <li className="px-2 py-2 text-xs text-muted-foreground">
              No chats yet. Start a new chat.
            </li>
          )}
        </ul>
      </div>
    </aside>
  );
}
