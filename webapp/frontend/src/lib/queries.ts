import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiUpload } from "@/lib/api";
import type {
  ClassifyJobResult,
  ConfigResponse,
  CreateJobResult,
  CreateRequest,
  HealthResponse,
  JobInfo,
  JobStartResponse,
  ParseResponse,
  PreviewResponse,
  RunHistoryDetail,
  RunHistoryItem,
  AuthState,
  SdiDocumentsResponse,
  SupplierOverrideCreate,
  SupplierOverridePayload,
  UploadResponse,
  VerifyRejectItem,
  VerifyResultsResponse,
} from "@/types/api";

// -------------------- Auth
export function useAuth() {
  return useQuery<AuthState>({
    queryKey: ["auth"],
    queryFn: () => apiGet<AuthState>("/auth/me"),
    staleTime: Infinity,
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation<AuthState, Error, string>({
    mutationFn: (password) => apiPost<AuthState>("/auth/login", { password }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation<AuthState, Error, void>({
    mutationFn: () => apiPost<AuthState>("/auth/logout"),
    onSuccess: () => {
      qc.clear();
      qc.setQueryData(["auth"], { authenticated: false, auth_enabled: true });
    },
  });
}

// -------------------- System
export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthResponse>("/health"),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useConfig() {
  return useQuery<ConfigResponse>({
    queryKey: ["config"],
    queryFn: () => apiGet<ConfigResponse>("/config"),
    staleTime: Infinity,
  });
}

// -------------------- Upload / parse / classify
export function useUploadStatement() {
  return useMutation<UploadResponse, Error, File>({
    mutationFn: (file) =>
      apiUpload<UploadResponse>("/statements/upload", file),
  });
}

export function useParseStatement() {
  return useMutation<ParseResponse, Error, string>({
    mutationFn: (statementId) =>
      apiPost<ParseResponse>(`/statements/${statementId}/parse`),
  });
}

export function useClassifyStatement() {
  return useMutation<JobStartResponse, Error, string>({
    mutationFn: (statementId) =>
      apiPost<JobStartResponse>(`/statements/${statementId}/classify`),
  });
}

// -------------------- Jobs
interface UseJobOptions {
  enabled?: boolean;
  interval?: number;
}
export function useJob(jobId: string | null | undefined, opts: UseJobOptions = {}) {
  const { enabled = true, interval = 750 } = opts;
  return useQuery<JobInfo>({
    queryKey: ["job", jobId],
    queryFn: () => apiGet<JobInfo>(`/jobs/${jobId}`),
    enabled: !!jobId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data as JobInfo | undefined;
      if (!data) return interval;
      if (data.status === "done" || data.status === "error") return false;
      return interval;
    },
  });
}

// -------------------- Verify
export function useVerifySuppliers() {
  return useMutation<JobStartResponse, Error, string>({
    mutationFn: (statementId) =>
      apiPost<JobStartResponse>(
        `/statements/${statementId}/verify-suppliers`
      ),
  });
}

export function useVerifyResults(
  statementId: string | null | undefined,
  options: { refetchInterval?: number | false; enabled?: boolean } = {}
) {
  const { refetchInterval = 2000, enabled = true } = options;
  return useQuery<VerifyResultsResponse>({
    queryKey: ["verify-results", statementId],
    queryFn: () =>
      apiGet<VerifyResultsResponse>(
        `/statements/${statementId}/verify-suppliers/results`
      ),
    enabled: !!statementId && enabled,
    refetchInterval,
  });
}

export function useVerifyRejects() {
  return useQuery<VerifyRejectItem[]>({
    queryKey: ["verify-rejects"],
    queryFn: () => apiGet<VerifyRejectItem[]>("/suppliers/verify-rejects"),
  });
}

// -------------------- Preview
export function usePreview() {
  return useMutation<PreviewResponse, Error, string>({
    mutationFn: (statementId) =>
      apiPost<PreviewResponse>(`/statements/${statementId}/preview`),
  });
}

export function usePreviewQuery(
  statementId: string | null | undefined,
  options?: Partial<UseQueryOptions<PreviewResponse>>
) {
  return useQuery<PreviewResponse>({
    queryKey: ["preview", statementId],
    queryFn: () =>
      apiPost<PreviewResponse>(`/statements/${statementId}/preview`),
    enabled: !!statementId,
    staleTime: 30_000,
    ...options,
  });
}

// -------------------- Create
export function useCreateAutofatture() {
  return useMutation<JobStartResponse, Error, CreateRequest>({
    mutationFn: (req) => apiPost<JobStartResponse>("/autofatture/create", req),
  });
}

// -------------------- SDI
export function useSdiDocuments(params: { date?: string; ids?: number[] }) {
  const ids = params.ids?.join(",");
  return useQuery<SdiDocumentsResponse>({
    queryKey: ["sdi-documents", params.date ?? null, ids ?? null],
    queryFn: () =>
      apiGet<SdiDocumentsResponse>("/sdi/documents", { date: params.date, ids }),
    enabled: !params.ids || params.ids.length > 0,
  });
}

export function useSdiVerify() {
  return useMutation<JobStartResponse, Error, number[]>({
    mutationFn: (doc_ids) => apiPost<JobStartResponse>("/sdi/verify", { doc_ids }),
  });
}

export function useSdiSend() {
  return useMutation<JobStartResponse, Error, { doc_ids: number[]; confirm: string }>({
    mutationFn: (req) => apiPost<JobStartResponse>("/sdi/send", req),
  });
}

// -------------------- History
export function useHistory() {
  return useQuery<RunHistoryItem[]>({
    queryKey: ["history"],
    queryFn: () => apiGet<RunHistoryItem[]>("/history"),
  });
}

export function useHistoryDetail(id: string | number | null | undefined) {
  return useQuery<RunHistoryDetail>({
    queryKey: ["history", String(id)],
    queryFn: () => apiGet<RunHistoryDetail>(`/history/${id}`),
    enabled: !!id,
  });
}

// -------------------- Overrides
export function useOverrides() {
  return useQuery<SupplierOverridePayload[]>({
    queryKey: ["overrides"],
    queryFn: () => apiGet<SupplierOverridePayload[]>("/suppliers/overrides"),
  });
}

export function useSaveOverride() {
  const qc = useQueryClient();
  return useMutation<SupplierOverridePayload, Error, SupplierOverrideCreate>({
    mutationFn: (data) =>
      apiPost<SupplierOverridePayload>("/suppliers/overrides", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["overrides"] });
    },
  });
}

export function useDeleteOverride() {
  const qc = useQueryClient();
  return useMutation<{ deleted: boolean }, Error, number>({
    mutationFn: (id) =>
      apiDelete<{ deleted: boolean }>(`/suppliers/overrides/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["overrides"] });
    },
  });
}

// Re-export helpful types for convenience
export type { CreateJobResult, ClassifyJobResult };
