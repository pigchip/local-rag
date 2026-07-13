export interface KnowledgeBase {
  name: string;
  description: string;
  examples: string[];
  file_count: number;
  chunk_count: number;
}

export interface IndexedFile {
  file_path: string;
  name: string;
  chunks: number;
  preview: string;
}

export interface Provider {
  id: string;
  label: string;
  available: boolean;
  models: string[];
  default_model: string;
}

export interface Source {
  index: number;
  source: string;
  file_path: string;
  score: number | null;
  content: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  kb_name: string | null;
  provider: string | null;
  model: string | null;
  created_at: string;
  updated_at: string;
  message_count?: number;
  messages?: Message[];
}

export type StreamEvent =
  | { type: "sources"; sources: Source[] }
  | { type: "token"; text: string }
  | { type: "done"; message: Message }
  | { type: "error"; error: string; message?: Message };
