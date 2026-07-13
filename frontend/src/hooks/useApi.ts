import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import * as api from "@/api/client";
import type { Session } from "@/api/types";

// --- Knowledge bases -------------------------------------------------------

export function useKnowledgeBases() {
  return useQuery({
    queryKey: ["kbs"],
    queryFn: api.listKnowledgeBases,
  });
}

export function useKbFiles(kbName: string | null) {
  return useQuery({
    queryKey: ["kb-files", kbName],
    queryFn: () => api.listFiles(kbName as string),
    enabled: !!kbName,
  });
}

export function useCreateKb() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      name: string;
      files: File[];
      provider?: string;
      model?: string;
    }) => api.createKnowledgeBase(vars.name, vars.files, vars.provider, vars.model),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kbs"] }),
  });
}

export function useAddFiles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      kbName: string;
      files: File[];
      provider?: string;
      model?: string;
    }) => api.addFilesToKnowledgeBase(vars.kbName, vars.files, vars.provider, vars.model),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["kbs"] });
      qc.invalidateQueries({ queryKey: ["kb-files", vars.kbName] });
    },
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { kbName: string; filePath: string }) =>
      api.deleteFile(vars.kbName, vars.filePath),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["kbs"] });
      qc.invalidateQueries({ queryKey: ["kb-files", vars.kbName] });
    },
  });
}

export function useClearKb() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (kbName: string) => api.clearKnowledgeBase(kbName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kbs"] }),
  });
}

// --- Providers -------------------------------------------------------------

export function useProviders() {
  return useQuery({
    queryKey: ["providers"],
    queryFn: api.listProviders,
  });
}

// --- Sessions --------------------------------------------------------------

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: api.listSessions,
  });
}

export function useSession(id: string | null) {
  return useQuery({
    queryKey: ["session", id],
    queryFn: () => api.getSession(id as string),
    enabled: !!id,
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Session>) => api.createSession(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
  });
}

export function useUpdateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; body: Partial<Session> }) =>
      api.updateSession(vars.id, vars.body),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["sessions"] });
      qc.invalidateQueries({ queryKey: ["session", vars.id] });
    },
  });
}

export function useDeleteSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteSession(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
  });
}
