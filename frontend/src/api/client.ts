import type {
  IndexedFile,
  KnowledgeBase,
  Provider,
  Session,
  StreamEvent,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// --- Knowledge bases -------------------------------------------------------

export function listKnowledgeBases() {
  return request<{ knowledge_bases: KnowledgeBase[] }>("/api/kb").then(
    (r) => r.knowledge_bases
  );
}

export function createKnowledgeBase(
  name: string,
  files: File[],
  provider?: string,
  model?: string
) {
  const form = new FormData();
  form.append("name", name);
  if (provider) form.append("provider", provider);
  if (model) form.append("model", model);
  files.forEach((f) => form.append("files", f));
  return request<KnowledgeBase & { chunks_written: number }>("/api/kb", {
    method: "POST",
    headers: {},
    body: form,
  });
}

export function addFilesToKnowledgeBase(
  kbName: string,
  files: File[],
  provider?: string,
  model?: string
) {
  const form = new FormData();
  if (provider) form.append("provider", provider);
  if (model) form.append("model", model);
  files.forEach((f) => form.append("files", f));
  return request<KnowledgeBase & { chunks_written: number }>(
    `/api/kb/${encodeURIComponent(kbName)}/files`,
    { method: "POST", headers: {}, body: form }
  );
}

export function listFiles(kbName: string) {
  return request<{ files: IndexedFile[] }>(
    `/api/kb/${encodeURIComponent(kbName)}/files`
  ).then((r) => r.files);
}

export function deleteFile(kbName: string, filePath: string) {
  return request<{ removed_chunks: number }>(
    `/api/kb/${encodeURIComponent(kbName)}/files?file_path=${encodeURIComponent(filePath)}`,
    { method: "DELETE" }
  );
}

export function clearKnowledgeBase(kbName: string) {
  return request<{ cleared: string }>(`/api/kb/${encodeURIComponent(kbName)}`, {
    method: "DELETE",
  });
}

// --- Providers -------------------------------------------------------------

export function listProviders() {
  return request<{ default_provider: string; providers: Provider[] }>(
    "/api/providers"
  );
}

// --- Sessions --------------------------------------------------------------

export function listSessions() {
  return request<{ sessions: Session[] }>("/api/sessions").then(
    (r) => r.sessions
  );
}

export function createSession(body: Partial<Session>) {
  return request<Session>("/api/sessions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getSession(id: string) {
  return request<Session>(`/api/sessions/${id}`);
}

export function updateSession(id: string, body: Partial<Session>) {
  return request<Session>(`/api/sessions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteSession(id: string) {
  return request<{ deleted: string }>(`/api/sessions/${id}`, {
    method: "DELETE",
  });
}

// --- Chat streaming (SSE over fetch) ---------------------------------------

export interface ChatParams {
  query: string;
  kb_name?: string;
  top_k?: number;
  provider?: string;
  model?: string;
}

export async function streamMessage(
  sessionId: string,
  params: ChatParams,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      const data = line.slice("data:".length).trim();
      if (!data) continue;
      try {
        onEvent(JSON.parse(data) as StreamEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}
