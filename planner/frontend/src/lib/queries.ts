import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, apiUpload, ApiError } from "@/lib/api";
import type {
  Brand,
  BrandCreate,
  BrandSummary,
  BrandUpdate,
  CanvaSet,
  CanvaSetIn,
  PreviewUploadResult,
  ExtractedProfile,
  KlaviyoSnapshot,
  KlaviyoStatus,
  Launch,
  LaunchInput,
  NotionSettings,
  NotionSettingsUpdate,
  Occasion,
  OccasionInput,
  OccasionSuggestOut,
  Offer,
  OfferInput,
  PlanDetail,
  PlanEmail,
  PlanEmailUpdate,
  PlanGenerateRequest,
  PlanPublishResult,
  PlanSummary,
  PlanUpdate,
  Product,
  ProductInput,
  SystemStatus,
  Template,
  TemplateCategory,
  TemplatesSyncResult,
} from "@/types/api";

// -------------------- Query keys

export const keys = {
  systemStatus: ["system-status"] as const,
  brands: ["brands"] as const,
  brand: (id: number) => ["brand", id] as const,
  products: (brandId: number) => ["products", brandId] as const,
  offers: (brandId: number) => ["offers", brandId] as const,
  occasions: (brandId: number) => ["occasions", brandId] as const,
  launches: (brandId: number) => ["launches", brandId] as const,
  klaviyoStatus: (brandId: number) => ["klaviyo-status", brandId] as const,
  klaviyoInsights: (brandId: number) => ["klaviyo-insights", brandId] as const,
  notionSettings: ["notion-settings"] as const,
  templates: (category?: string, q?: string) =>
    ["templates", category ?? "", q ?? ""] as const,
  templateCategories: ["template-categories"] as const,
  canvaSet: ["canva-set"] as const,
  plans: (brandId: number) => ["plans", brandId] as const,
  plan: (planId: number) => ["plan", planId] as const,
};

// -------------------- System

export function useSystemStatus() {
  return useQuery<SystemStatus>({
    queryKey: keys.systemStatus,
    queryFn: () => apiGet<SystemStatus>("/system/status"),
    staleTime: 60_000,
  });
}

// -------------------- Brands

export function useBrands() {
  return useQuery<BrandSummary[]>({
    queryKey: keys.brands,
    queryFn: () => apiGet<BrandSummary[]>("/brands"),
  });
}

export function useBrand(brandId: number | null | undefined) {
  return useQuery<Brand>({
    queryKey: keys.brand(brandId ?? 0),
    queryFn: () => apiGet<Brand>(`/brands/${brandId}`),
    enabled: !!brandId,
  });
}

export function useCreateBrand() {
  const qc = useQueryClient();
  return useMutation<Brand, ApiError, BrandCreate>({
    mutationFn: (data) => apiPost<Brand>("/brands", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

export function useUpdateBrand(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Brand, ApiError, BrandUpdate>({
    mutationFn: (data) => apiPatch<Brand>(`/brands/${brandId}`, data),
    onSuccess: (brand) => {
      qc.setQueryData(keys.brand(brandId), brand);
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

export function useSuggestOccasions(brandId: number) {
  return useMutation<OccasionSuggestOut, ApiError, { month: string }>({
    mutationFn: (data) =>
      apiPost<OccasionSuggestOut>(`/brands/${brandId}/occasions/suggest`, data),
  });
}

export function useExtractProfile(brandId: number) {
  const qc = useQueryClient();
  return useMutation<
    ExtractedProfile,
    ApiError,
    { files: File[]; apply?: boolean }
  >({
    mutationFn: ({ files, apply }) => {
      const fd = new FormData();
      for (const f of files) fd.append("files", f);
      return apiUpload<ExtractedProfile>(
        `/brands/${brandId}/extract-profile`,
        fd,
        apply ? { apply: "true" } : undefined
      );
    },
    onSuccess: (result) => {
      if (result.applied) {
        qc.invalidateQueries({ queryKey: keys.brand(brandId) });
        qc.invalidateQueries({ queryKey: keys.brands });
        qc.invalidateQueries({ queryKey: keys.products(brandId) });
      }
    },
  });
}

export function useDeleteBrand() {
  const qc = useQueryClient();
  return useMutation<null, ApiError, number>({
    mutationFn: (brandId) => apiDelete(`/brands/${brandId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

// -------------------- Prodotti

export function useProducts(brandId: number) {
  return useQuery<Product[]>({
    queryKey: keys.products(brandId),
    queryFn: () => apiGet<Product[]>(`/brands/${brandId}/products`),
    enabled: !!brandId,
  });
}

export function useCreateProduct(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Product, ApiError, ProductInput>({
    mutationFn: (data) => apiPost<Product>(`/brands/${brandId}/products`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.products(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

export function useUpdateProduct(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Product, ApiError, { id: number; data: Partial<ProductInput> }>({
    mutationFn: ({ id, data }) => apiPatch<Product>(`/products/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.products(brandId) });
    },
  });
}

export function useDeleteProduct(brandId: number) {
  const qc = useQueryClient();
  return useMutation<null, ApiError, number>({
    mutationFn: (id) => apiDelete(`/products/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.products(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

// -------------------- Offerte

export function useOffers(brandId: number) {
  return useQuery<Offer[]>({
    queryKey: keys.offers(brandId),
    queryFn: () => apiGet<Offer[]>(`/brands/${brandId}/offers`),
    enabled: !!brandId,
  });
}

export function useCreateOffer(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Offer, ApiError, OfferInput>({
    mutationFn: (data) => apiPost<Offer>(`/brands/${brandId}/offers`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.offers(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

export function useUpdateOffer(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Offer, ApiError, { id: number; data: Partial<OfferInput> }>({
    mutationFn: ({ id, data }) => apiPatch<Offer>(`/offers/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.offers(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

export function useDeleteOffer(brandId: number) {
  const qc = useQueryClient();
  return useMutation<null, ApiError, number>({
    mutationFn: (id) => apiDelete(`/offers/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.offers(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

// -------------------- Occasioni

export function useOccasions(brandId: number) {
  return useQuery<Occasion[]>({
    queryKey: keys.occasions(brandId),
    queryFn: () => apiGet<Occasion[]>(`/brands/${brandId}/occasions`),
    enabled: !!brandId,
  });
}

export function useCreateOccasion(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Occasion, ApiError, OccasionInput>({
    mutationFn: (data) => apiPost<Occasion>(`/brands/${brandId}/occasions`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.occasions(brandId) });
    },
  });
}

export function useUpdateOccasion(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Occasion, ApiError, { id: number; data: Partial<OccasionInput> }>({
    mutationFn: ({ id, data }) => apiPatch<Occasion>(`/occasions/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.occasions(brandId) });
    },
  });
}

export function useDeleteOccasion(brandId: number) {
  const qc = useQueryClient();
  return useMutation<null, ApiError, number>({
    mutationFn: (id) => apiDelete(`/occasions/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.occasions(brandId) });
    },
  });
}

// -------------------- Lanci & Promo

export function useLaunches(brandId: number) {
  return useQuery<Launch[]>({
    queryKey: keys.launches(brandId),
    queryFn: () => apiGet<Launch[]>(`/brands/${brandId}/launches`),
    enabled: !!brandId,
  });
}

export function useCreateLaunch(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Launch, ApiError, LaunchInput>({
    mutationFn: (data) => apiPost<Launch>(`/brands/${brandId}/launches`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.launches(brandId) });
    },
  });
}

export function useUpdateLaunch(brandId: number) {
  const qc = useQueryClient();
  return useMutation<Launch, ApiError, { id: number; data: Partial<LaunchInput> }>({
    mutationFn: ({ id, data }) => apiPatch<Launch>(`/launches/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.launches(brandId) });
    },
  });
}

export function useDeleteLaunch(brandId: number) {
  const qc = useQueryClient();
  return useMutation<null, ApiError, number>({
    mutationFn: (id) => apiDelete(`/launches/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.launches(brandId) });
    },
  });
}

// -------------------- Klaviyo

export function useKlaviyoStatus(brandId: number) {
  return useQuery<KlaviyoStatus>({
    queryKey: keys.klaviyoStatus(brandId),
    queryFn: () => apiGet<KlaviyoStatus>(`/brands/${brandId}/klaviyo/status`),
    enabled: !!brandId,
  });
}

export function useKlaviyoInsights(brandId: number) {
  return useQuery<KlaviyoSnapshot>({
    queryKey: keys.klaviyoInsights(brandId),
    queryFn: () => apiGet<KlaviyoSnapshot>(`/brands/${brandId}/klaviyo/insights`),
    enabled: !!brandId,
    retry: (failureCount, error) => {
      // 404 = mai sincronizzato: non ritentare
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 2;
    },
  });
}

export function useSaveKlaviyoKey(brandId: number) {
  const qc = useQueryClient();
  return useMutation<KlaviyoStatus, ApiError, string>({
    mutationFn: (apiKey) =>
      apiPut<KlaviyoStatus>(`/brands/${brandId}/klaviyo`, { api_key: apiKey }),
    onSuccess: (status) => {
      qc.setQueryData(keys.klaviyoStatus(brandId), status);
      qc.invalidateQueries({ queryKey: keys.brands });
      qc.invalidateQueries({ queryKey: keys.brand(brandId) });
    },
  });
}

export function useDisconnectKlaviyo(brandId: number) {
  const qc = useQueryClient();
  return useMutation<null, ApiError, void>({
    mutationFn: () => apiDelete(`/brands/${brandId}/klaviyo`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.klaviyoStatus(brandId) });
      qc.invalidateQueries({ queryKey: keys.klaviyoInsights(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
      qc.invalidateQueries({ queryKey: keys.brand(brandId) });
    },
  });
}

export function useSyncKlaviyo(brandId: number) {
  const qc = useQueryClient();
  return useMutation<KlaviyoSnapshot, ApiError, void>({
    mutationFn: () => apiPost<KlaviyoSnapshot>(`/brands/${brandId}/klaviyo/sync`),
    onSuccess: (snapshot) => {
      qc.setQueryData(keys.klaviyoInsights(brandId), snapshot);
      qc.invalidateQueries({ queryKey: keys.klaviyoStatus(brandId) });
    },
  });
}

// -------------------- Impostazioni Notion

export function useNotionSettings() {
  return useQuery<NotionSettings>({
    queryKey: keys.notionSettings,
    queryFn: () => apiGet<NotionSettings>("/settings/notion"),
  });
}

export function useSaveNotionSettings() {
  const qc = useQueryClient();
  return useMutation<NotionSettings, ApiError, NotionSettingsUpdate>({
    mutationFn: (data) => apiPut<NotionSettings>("/settings/notion", data),
    onSuccess: (settings) => {
      qc.setQueryData(keys.notionSettings, settings);
      qc.invalidateQueries({ queryKey: keys.systemStatus });
    },
  });
}

// -------------------- Template Canva

export function useTemplates(category?: string, q?: string) {
  return useQuery<Template[]>({
    queryKey: keys.templates(category, q),
    queryFn: () => apiGet<Template[]>("/templates", { category, q }),
  });
}

export function useTemplateCategories() {
  return useQuery<TemplateCategory[]>({
    queryKey: keys.templateCategories,
    queryFn: () => apiGet<TemplateCategory[]>("/templates/categories"),
  });
}

export function useSyncTemplates() {
  const qc = useQueryClient();
  return useMutation<TemplatesSyncResult, ApiError, void>({
    mutationFn: () => apiPost<TemplatesSyncResult>("/templates/sync"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      qc.invalidateQueries({ queryKey: keys.templateCategories });
      qc.invalidateQueries({ queryKey: keys.notionSettings });
      qc.invalidateQueries({ queryKey: keys.canvaSet });
    },
  });
}

export function useUploadPreviews() {
  const qc = useQueryClient();
  return useMutation<PreviewUploadResult, ApiError, File[]>({
    mutationFn: (files) => {
      const fd = new FormData();
      for (const f of files) fd.append("files", f);
      return apiUpload<PreviewUploadResult>("/templates/previews", fd);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      qc.invalidateQueries({ queryKey: keys.canvaSet });
    },
  });
}

export function useCanvaSet() {
  return useQuery<CanvaSet>({
    queryKey: keys.canvaSet,
    queryFn: () => apiGet<CanvaSet>("/templates/set"),
  });
}

export function useSaveCanvaSet() {
  const qc = useQueryClient();
  return useMutation<
    CanvaSet,
    ApiError,
    CanvaSetIn
  >({
    mutationFn: (payload) => apiPut<CanvaSet>("/templates/set", payload),
    onSuccess: (set) => {
      qc.setQueryData(keys.canvaSet, set);
      qc.invalidateQueries({ queryKey: ["templates"] });
      qc.invalidateQueries({ queryKey: keys.templateCategories });
    },
  });
}

// -------------------- Piani editoriali

export function usePlans(brandId: number) {
  return useQuery<PlanSummary[]>({
    queryKey: keys.plans(brandId),
    queryFn: () => apiGet<PlanSummary[]>(`/brands/${brandId}/plans`),
    enabled: !!brandId,
    refetchInterval: (query) => {
      const data = query.state.data as PlanSummary[] | undefined;
      if (data?.some((p) => p.status === "generating")) return 2000;
      return false;
    },
  });
}

export function useGeneratePlan(brandId: number) {
  const qc = useQueryClient();
  return useMutation<PlanSummary, ApiError, PlanGenerateRequest>({
    mutationFn: (data) =>
      apiPost<PlanSummary>(`/brands/${brandId}/plans/generate`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.plans(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

export function usePlan(planId: number | null | undefined) {
  return useQuery<PlanDetail>({
    queryKey: keys.plan(planId ?? 0),
    queryFn: () => apiGet<PlanDetail>(`/plans/${planId}`),
    enabled: !!planId,
    refetchInterval: (query) => {
      const data = query.state.data as PlanDetail | undefined;
      // Polling ogni 2s finché la generazione è in corso.
      if (data?.status === "generating") return 2000;
      return false;
    },
  });
}

export function useUpdatePlan(planId: number, brandId: number) {
  const qc = useQueryClient();
  return useMutation<PlanSummary, ApiError, PlanUpdate>({
    mutationFn: (data) => apiPatch<PlanSummary>(`/plans/${planId}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.plan(planId) });
      qc.invalidateQueries({ queryKey: keys.plans(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

export function useDeletePlan(brandId: number) {
  const qc = useQueryClient();
  return useMutation<null, ApiError, number>({
    mutationFn: (planId) => apiDelete(`/plans/${planId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.plans(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}

export function useUpdatePlanEmail(planId: number) {
  const qc = useQueryClient();
  return useMutation<PlanEmail, ApiError, { emailId: number; data: PlanEmailUpdate }>({
    mutationFn: ({ emailId, data }) =>
      apiPatch<PlanEmail>(`/plans/${planId}/emails/${emailId}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.plan(planId) });
    },
  });
}

export function useRegenerateEmail(planId: number) {
  const qc = useQueryClient();
  return useMutation<PlanEmail, ApiError, { emailId: number; instructions?: string }>({
    mutationFn: ({ emailId, instructions }) =>
      apiPost<PlanEmail>(
        `/plans/${planId}/emails/${emailId}/regenerate`,
        instructions ? { instructions } : {}
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.plan(planId) });
    },
  });
}

export function usePublishPlan(planId: number, brandId: number) {
  const qc = useQueryClient();
  return useMutation<PlanPublishResult, ApiError, void>({
    mutationFn: () => apiPost<PlanPublishResult>(`/plans/${planId}/publish`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.plan(planId) });
      qc.invalidateQueries({ queryKey: keys.plans(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
    },
  });
}
