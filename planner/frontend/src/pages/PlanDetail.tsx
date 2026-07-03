import { useNavigate, useParams, Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  Loader2,
  RefreshCw,
  Send,
  Undo2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmailCard } from "@/components/domain/EmailCard";
import { PlanStatusBadge } from "@/components/domain/PlanStatusBadge";
import {
  useDeletePlan,
  useGeneratePlan,
  usePlan,
  usePublishPlan,
  useUpdatePlan,
} from "@/lib/queries";
import { formatMonth } from "@/lib/utils";
import type { PlanDetail as PlanDetailType } from "@/types/api";

function GeneratingScreen({ plan }: { plan: PlanDetailType }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center gap-3 rounded-lg border border-border bg-card px-6 py-10 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div>
          <h2 className="text-lg font-semibold">
            Generazione del piano in corso…
          </h2>
          <p className="text-sm text-muted-foreground">
            Claude sta creando il calendario di {plan.num_emails} email per{" "}
            <span className="capitalize">{formatMonth(plan.month_start)}</span>.
            Può richiedere qualche minuto.
          </p>
        </div>
      </div>
      <div className="space-y-4">
        {Array.from({ length: plan.num_emails || 3 }).map((_, i) => (
          <div key={i} className="space-y-3 rounded-lg border border-border p-5">
            <div className="flex items-center gap-3">
              <Skeleton className="h-7 w-7 rounded-full" />
              <Skeleton className="h-4 w-48" />
            </div>
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-20 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

function BalanceIndicator({ plan }: { plan: PlanDetailType }) {
  const total = plan.emails.length;
  const edu = plan.emails.filter((e) =>
    ["nurturing", "storytelling"].includes(e.objective)
  ).length;
  const prod = plan.emails.filter((e) => e.objective === "vendita").length;
  const promo = plan.emails.filter((e) => e.objective === "promo").length;
  const pct = (v: number) => (total > 0 ? (v / total) * 100 : 0);

  return (
    <div className="w-full max-w-md space-y-1.5">
      <div className="flex items-center justify-between gap-3 whitespace-nowrap text-xs">
        <span className="font-semibold uppercase tracking-wide text-muted-foreground">
          Regola 70 / 20 / 10
        </span>
        <span className="tabular-nums">
          <span className="font-semibold text-primary">{edu} edu</span>
          <span className="text-muted-foreground"> · </span>
          <span className="font-semibold text-emerald-600">{prod} prodotto</span>
          <span className="text-muted-foreground"> · </span>
          <span className="font-semibold text-amber-600">{promo} promo</span>
        </span>
      </div>
      <div
        className="flex h-2 w-full overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={`${edu} educative, ${prod} prodotto, ${promo} promozionali su ${total}`}
      >
        <div className="bg-primary" style={{ width: `${pct(edu)}%` }} />
        <div className="bg-emerald-500" style={{ width: `${pct(prod)}%` }} />
        <div className="bg-amber-500" style={{ width: `${pct(promo)}%` }} />
      </div>
      <div className="text-xs text-muted-foreground">
        Formati:{" "}
        <span className="font-medium text-fuchsia-700">
          {plan.emails.filter((e) => e.format !== "testuale").length} grafiche
        </span>
        {" · "}
        <span className="font-medium">
          {plan.emails.filter((e) => e.format === "testuale").length} testuali
        </span>
      </div>
    </div>
  );
}

export function PlanDetail() {
  const { brandId: brandIdParam, planId: planIdParam } = useParams();
  const brandId = Number(brandIdParam);
  const planId = Number(planIdParam);
  const navigate = useNavigate();

  const { data: plan, isLoading, isError, error } = usePlan(planId);
  const updatePlan = useUpdatePlan(planId, brandId);
  const publishPlan = usePublishPlan(planId, brandId);
  const deletePlan = useDeletePlan(brandId);
  const generatePlan = useGeneratePlan(brandId);

  function handleRetry() {
    if (!plan) return;
    const { month_start, num_emails, notes } = plan;
    deletePlan.mutate(planId, {
      onSuccess: () => {
        generatePlan.mutate(
          {
            month_start,
            num_emails: num_emails || 12,
            notes: notes ?? undefined,
          },
          {
            onSuccess: (newPlan) => {
              toast.success("Nuova generazione avviata");
              navigate(`/brands/${brandId}/plans/${newPlan.id}`, {
                replace: true,
              });
            },
            onError: (err) => toast.error(`Errore: ${err.message}`),
          }
        );
      },
      onError: (err) => toast.error(`Errore: ${err.message}`),
    });
  }

  function handleApprove() {
    updatePlan.mutate(
      { status: "approved" },
      {
        onSuccess: () => toast.success("Piano approvato"),
        onError: (err) => toast.error(`Errore: ${err.message}`),
      }
    );
  }

  function handleBackToDraft() {
    updatePlan.mutate(
      { status: "draft" },
      {
        onSuccess: () => toast.success("Piano riportato in bozza"),
        onError: (err) => toast.error(`Errore: ${err.message}`),
      }
    );
  }

  function handlePublish() {
    publishPlan.mutate(undefined, {
      onSuccess: (result) => {
        toast.success("Piano pubblicato su Notion", {
          action: {
            label: "Apri Notion",
            onClick: () => window.open(result.notion_url, "_blank"),
          },
        });
      },
      onError: (err) => {
        if (err.status === 502) {
          toast.error(
            `Pubblicazione fallita: Notion non configurato o non raggiungibile. ${err.message}`
          );
        } else if (err.status === 409) {
          toast.error("Il piano deve essere approvato prima della pubblicazione");
        } else {
          toast.error(`Errore: ${err.message}`);
        }
      },
    });
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !plan) {
    return (
      <div className="mx-auto max-w-4xl">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Piano non trovato</AlertTitle>
          <AlertDescription>
            {error?.message ?? "Impossibile caricare il piano."}{" "}
            <Link
              to={`/brands/${brandId}/plans`}
              className="font-medium underline"
            >
              Torna ai piani
            </Link>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const readOnly = plan.status === "published";
  const sortedEmails = [...plan.emails].sort((a, b) => a.position - b.position);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="space-y-4">
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link to={`/brands/${brandId}/plans`}>
            <ArrowLeft className="h-4 w-4" />
            Tutti i piani
          </Link>
        </Button>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="font-display text-2xl font-semibold tracking-tight">
                <span className="capitalize">{formatMonth(plan.month_start)}</span>
              </h1>
              <PlanStatusBadge status={plan.status} />
            </div>
            {plan.notes && (
              <p className="text-sm text-muted-foreground">
                Note: {plan.notes}
              </p>
            )}
          </div>

          {(plan.status === "draft" ||
            plan.status === "approved" ||
            plan.status === "published") && (
            <div className="flex items-center gap-2">
              {plan.status === "draft" && (
                <Button onClick={handleApprove} disabled={updatePlan.isPending}>
                  <CheckCircle2 className="h-4 w-4" />
                  Approva piano
                </Button>
              )}
              {plan.status === "approved" && (
                <Button
                  variant="outline"
                  onClick={handleBackToDraft}
                  disabled={updatePlan.isPending}
                >
                  <Undo2 className="h-4 w-4" />
                  Riporta in bozza
                </Button>
              )}
              {plan.status !== "published" && (
                <Button
                  onClick={handlePublish}
                  disabled={plan.status !== "approved" || publishPlan.isPending}
                  title={
                    plan.status !== "approved"
                      ? "Approva il piano prima di pubblicarlo"
                      : undefined
                  }
                >
                  {publishPlan.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                  Pubblica su Notion
                </Button>
              )}
              {plan.status === "published" && plan.notion_url && (
                <Button variant="outline" asChild>
                  <a href={plan.notion_url} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-4 w-4" />
                    Apri su Notion
                  </a>
                </Button>
              )}
            </div>
          )}
        </div>

        {plan.status !== "generating" &&
          plan.status !== "error" &&
          plan.emails.length > 0 && <BalanceIndicator plan={plan} />}
      </div>

      {/* Stato generating */}
      {plan.status === "generating" && <GeneratingScreen plan={plan} />}

      {/* Stato error */}
      {plan.status === "error" && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Generazione fallita</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>{plan.error ?? "Errore sconosciuto durante la generazione."}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              disabled={deletePlan.isPending || generatePlan.isPending}
            >
              {deletePlan.isPending || generatePlan.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              Riprova generazione
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Email */}
      {plan.status !== "generating" && plan.status !== "error" && (
        <div className="space-y-4">
          {sortedEmails.map((email) => (
            <EmailCard
              key={email.id}
              email={email}
              planId={planId}
              readOnly={readOnly}
            />
          ))}
        </div>
      )}
    </div>
  );
}
