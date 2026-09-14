import type { ClientStatus, ClientType, LeadType, PackageStatus } from "./enums.js";
import { isRoutable } from "./ledger.js";
import { levelRank, territoryMatchesLead, type LeadLocation, type TerritoryRef } from "./territory.js";

export interface RoutingLead {
  id: string;
  vertical: string;
  leadType: LeadType;
  location: LeadLocation;
  qualificationPassed: boolean;
}

export interface RoutingPackage {
  id: string;
  status: PackageStatus;
  balance: number;
  createdAt: Date;
}

export interface RoutingCandidate {
  clientId: string;
  clientName: string;
  clientStatus: ClientStatus;
  clientType: ClientType;
  vertical: string;
  packages: RoutingPackage[];
  territories: TerritoryRef[];
  caps: { daily?: number | null; weekly?: number | null; monthly?: number | null };
  deliveredCounts: { day: number; week: number; month: number };
  // Esito dei criteri specifici del cliente sul lead (calcolato dal chiamante con evaluateCriteria).
  clientCriteriaPassed?: boolean;
  lastAssignedAt?: Date | null;
  priority?: number; // più alto = preferito a parità
}

export type RoutingReasonCode =
  | "CLIENT_NOT_ACTIVE"
  | "VERTICAL_MISMATCH"
  | "TYPE_MISMATCH"
  | "NO_TERRITORY_MATCH"
  | "NO_CREDIT"
  | "CAP_DAILY_REACHED"
  | "CAP_WEEKLY_REACHED"
  | "CAP_MONTHLY_REACHED"
  | "CLIENT_CRITERIA_FAILED"
  | "EXCLUSIVE_HOLDER_UNAVAILABLE"
  | "EXCLUSIVITY_OF_OTHER_CLIENT";

export interface CandidateEvaluation {
  clientId: string;
  clientName: string;
  eligible: boolean;
  reasons: RoutingReasonCode[];
  matchedTerritory: TerritoryRef | null;
  packageId: string | null;
}

export type RoutingDecision =
  | {
      outcome: "ASSIGNED";
      clientId: string;
      clientName: string;
      packageId: string;
      matchedTerritory: TerritoryRef;
      evaluations: CandidateEvaluation[];
    }
  | {
      outcome: "WAITING_ASSIGNMENT";
      summary: RoutingReasonCode[];
      evaluations: CandidateEvaluation[];
    }
  | { outcome: "NOT_QUALIFIED"; evaluations: [] };

function typeCompatible(clientType: ClientType, leadType: LeadType): boolean {
  if (clientType === "BOTH") return true;
  return clientType === leadType;
}

export function pickPackage(packages: readonly RoutingPackage[]): RoutingPackage | null {
  // FIFO: il pacchetto attivo più vecchio si consuma per primo.
  const routable = packages.filter((p) => isRoutable(p.status, p.balance));
  routable.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
  return routable[0] ?? null;
}

export function bestTerritoryMatch(territories: readonly TerritoryRef[], loc: LeadLocation): TerritoryRef | null {
  let best: TerritoryRef | null = null;
  for (const t of territories) {
    if (!territoryMatchesLead(t, loc)) continue;
    if (!best || levelRank(t.level) > levelRank(best.level)) best = t;
  }
  return best;
}

export function evaluateCandidate(lead: RoutingLead, c: RoutingCandidate): CandidateEvaluation {
  const reasons: RoutingReasonCode[] = [];
  if (c.clientStatus !== "ACTIVE") reasons.push("CLIENT_NOT_ACTIVE");
  if (c.vertical !== lead.vertical) reasons.push("VERTICAL_MISMATCH");
  if (!typeCompatible(c.clientType, lead.leadType)) reasons.push("TYPE_MISMATCH");
  const matched = bestTerritoryMatch(c.territories, lead.location);
  if (!matched) reasons.push("NO_TERRITORY_MATCH");
  const pkg = pickPackage(c.packages);
  if (!pkg) reasons.push("NO_CREDIT");
  if (c.caps.daily != null && c.deliveredCounts.day >= c.caps.daily) reasons.push("CAP_DAILY_REACHED");
  if (c.caps.weekly != null && c.deliveredCounts.week >= c.caps.weekly) reasons.push("CAP_WEEKLY_REACHED");
  if (c.caps.monthly != null && c.deliveredCounts.month >= c.caps.monthly) reasons.push("CAP_MONTHLY_REACHED");
  if (c.clientCriteriaPassed === false) reasons.push("CLIENT_CRITERIA_FAILED");
  return {
    clientId: c.clientId,
    clientName: c.clientName,
    eligible: reasons.length === 0,
    reasons,
    matchedTerritory: matched,
    packageId: pkg?.id ?? null,
  };
}

// Routing Engine (PRD sez. 10-13). Deterministico e senza effetti collaterali:
// riceve una fotografia dei candidati e restituisce una decisione motivata.
export function evaluateRouting(lead: RoutingLead, candidates: readonly RoutingCandidate[]): RoutingDecision {
  if (!lead.qualificationPassed) return { outcome: "NOT_QUALIFIED", evaluations: [] };

  const evaluations = candidates.map((c) => evaluateCandidate(lead, c));

  // Esclusività: se un territorio esclusivo copre il lead, solo quel cliente può riceverlo.
  const exclusiveHolders = evaluations.filter((e) => e.matchedTerritory?.exclusive);
  let pool = evaluations;
  if (exclusiveHolders.length > 0) {
    // Il più specifico vince tra eventuali esclusive annidate (CAP > comune > provincia).
    const top = exclusiveHolders.reduce((a, b) =>
      levelRank(b.matchedTerritory!.level) > levelRank(a.matchedTerritory!.level) ? b : a,
    );
    for (const e of evaluations) {
      if (e.clientId !== top.clientId && e.matchedTerritory) {
        e.eligible = false;
        e.reasons.push("EXCLUSIVITY_OF_OTHER_CLIENT");
      }
    }
    if (!top.eligible) top.reasons.push("EXCLUSIVE_HOLDER_UNAVAILABLE");
    pool = [top];
  }

  const eligible = pool.filter((e) => e.eligible && e.matchedTerritory && e.packageId);
  if (eligible.length === 0) {
    const summary = Array.from(new Set(evaluations.flatMap((e) => e.reasons)));
    return { outcome: "WAITING_ASSIGNMENT", summary, evaluations };
  }

  const byId = new Map(candidates.map((c) => [c.clientId, c] as const));
  eligible.sort((a, b) => {
    // 1) territorio più specifico
    const lr = levelRank(b.matchedTerritory!.level) - levelRank(a.matchedTerritory!.level);
    if (lr !== 0) return lr;
    // 2) priorità esplicita
    const pa = byId.get(a.clientId)?.priority ?? 0;
    const pb = byId.get(b.clientId)?.priority ?? 0;
    if (pb !== pa) return pb - pa;
    // 3) round robin: chi ha ricevuto meno questo mese, poi chi aspetta da più tempo
    const ma = byId.get(a.clientId)?.deliveredCounts.month ?? 0;
    const mb = byId.get(b.clientId)?.deliveredCounts.month ?? 0;
    if (ma !== mb) return ma - mb;
    const la = byId.get(a.clientId)?.lastAssignedAt?.getTime() ?? 0;
    const lb = byId.get(b.clientId)?.lastAssignedAt?.getTime() ?? 0;
    return la - lb;
  });

  const winner = eligible[0]!;
  return {
    outcome: "ASSIGNED",
    clientId: winner.clientId,
    clientName: winner.clientName,
    packageId: winner.packageId!,
    matchedTerritory: winner.matchedTerritory!,
    evaluations,
  };
}

export const ROUTING_REASON_LABELS: Record<RoutingReasonCode, string> = {
  CLIENT_NOT_ACTIVE: "Cliente non attivo",
  VERTICAL_MISMATCH: "Verticale diverso",
  TYPE_MISMATCH: "Tipologia lead non compatibile",
  NO_TERRITORY_MATCH: "Territorio scoperto",
  NO_CREDIT: "Cliente senza credito",
  CAP_DAILY_REACHED: "Cap giornaliero raggiunto",
  CAP_WEEKLY_REACHED: "Cap settimanale raggiunto",
  CAP_MONTHLY_REACHED: "Cap mensile raggiunto",
  CLIENT_CRITERIA_FAILED: "Criteri del cliente non soddisfatti",
  EXCLUSIVE_HOLDER_UNAVAILABLE: "Titolare dell'esclusiva non disponibile",
  EXCLUSIVITY_OF_OTHER_CLIENT: "Territorio in esclusiva a un altro cliente",
};
