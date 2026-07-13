import { useEffect, useRef, useState } from "react";
import { Send, Square, Sparkles, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MarkdownMessage } from "./MarkdownMessage";
import { Citations } from "./Citations";
import { useChat } from "@/hooks/useChat";
import { useSession, useUpdateSession, useKnowledgeBases } from "@/hooks/useApi";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/lib/utils";

export function ChatView() {
  const { activeSessionId, activeKb, provider, model, topK } = useAppStore();
  const { data: session } = useSession(activeSessionId);
  const { data: kbs } = useKnowledgeBases();
  const { streaming, send, stop } = useChat(activeSessionId);
  const updateSession = useUpdateSession();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const messages = session?.messages ?? [];
  const activeKbMeta = kbs?.find((k) => k.name === activeKb);
  const examples = activeKbMeta?.examples ?? [];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages.length, streaming.text, streaming.active]);

  const submit = async (text: string) => {
    const query = text.trim();
    if (!query || !activeSessionId || !activeKb || streaming.active) return;
    setInput("");
    // Title the session from its first user message.
    if (messages.length === 0 && session) {
      updateSession.mutate({
        id: session.id,
        body: { title: query.slice(0, 60) },
      });
    }
    await send({
      query,
      kb_name: activeKb || undefined,
      top_k: topK,
      provider: provider || undefined,
      model: model || undefined,
    });
  };

  const canSend =
    !!activeSessionId && !!activeKb && !!input.trim() && !streaming.active;

  if (!activeSessionId) {
    return (
      <EmptyState
        title="Start a conversation"
        subtitle="Create a new chat and pick a knowledge base to begin asking grounded questions."
      />
    );
  }

  return (
    <div className="flex h-full flex-1 flex-col">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-auto scrollbar-thin">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6">
          {messages.length === 0 && !streaming.active && (
            <>
              <EmptyState
                title={activeKb ? `Ask about “${activeKb}”` : "Select a knowledge base"}
                subtitle={
                  activeKb
                    ? activeKbMeta?.description ||
                      "Your questions are answered using only the indexed documents, with citations."
                    : "Choose or create a knowledge base in the sidebar to get started."
                }
              />
              {activeKb && examples.length > 0 && (
                <div className="mx-auto w-full max-w-2xl">
                  <p className="mb-2 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Try one of these
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {examples.map((ex, i) => (
                      <button
                        key={i}
                        onClick={() => submit(ex)}
                        className="group flex items-start gap-2 rounded-xl border border-border bg-card px-3 py-2.5 text-left text-sm transition-colors hover:border-primary/60 hover:bg-accent"
                      >
                        <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary/70 group-hover:text-primary" />
                        <span>{ex}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role}>
              <MarkdownMessage content={m.content} />
              {m.role === "assistant" && <Citations sources={m.sources} />}
            </MessageBubble>
          ))}

          {streaming.active || streaming.text ? (
            <MessageBubble role="assistant">
              {streaming.text ? (
                <MarkdownMessage content={streaming.text} />
              ) : (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Retrieving &amp; generating…
                </div>
              )}
              {!streaming.active && <Citations sources={streaming.sources} />}
            </MessageBubble>
          ) : null}

          {streaming.error && (
            <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" /> {streaming.error}
            </div>
          )}
        </div>
      </div>

      {/* Composer */}
      <div className="border-t border-border bg-background/80 px-4 py-3 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          {!activeKb && (
            <p className="mb-2 text-xs text-muted-foreground">
              Select a knowledge base in the sidebar to enable chat.
            </p>
          )}
          <div className="flex items-end gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(input);
                }
              }}
              placeholder={activeKb ? "Ask a question…" : "Select a knowledge base first"}
              disabled={!activeKb}
              rows={1}
              className="max-h-40 min-h-[44px] flex-1"
            />
            {streaming.active ? (
              <Button variant="destructive" size="icon" className="h-11 w-11" onClick={stop}>
                <Square className="h-4 w-4" />
              </Button>
            ) : (
              <Button size="icon" className="h-11 w-11" onClick={() => submit(input)} disabled={!canSend}>
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  role,
  children,
}: {
  role: "user" | "assistant";
  children: React.ReactNode;
}) {
  const isUser = role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "rounded-2xl px-4 py-3",
          isUser
            ? "max-w-[80%] bg-primary text-primary-foreground"
            : "w-full border border-border bg-card"
        )}
      >
        {children}
      </div>
    </div>
  );
}

function EmptyState({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-20 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
        <Sparkles className="h-6 w-6 text-primary" />
      </div>
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="max-w-sm text-sm text-muted-foreground">{subtitle}</p>
    </div>
  );
}
