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
  SupplierOverrideCreate,
  SupplierOverridePayload,
  UploadResponse,
  VerifyRejectItem,
  VerifyResultsResponse,
} from "@/types/api";

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
