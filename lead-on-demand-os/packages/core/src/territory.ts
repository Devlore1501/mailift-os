import type { TerritoryLevel } from "./enums.js";

export interface TerritoryRef {
  id?: string;
  clientId: string;
  level: TerritoryLevel;
  value: string; // "IT", "VENETO", "VI", "36100", "Vicenza" (normalizzato dal chiamante)
  exclusive: boolean;
  // Gerarchia opzionale, usata per rilevare conflitti tra livelli diversi.
  region?: string | null;
  province?: string | null;
}

export interface LeadLocation {
  country?: string | null;
  region?: string | null;
  province?: string | null;
  municipality?: string | null;
  postalCode?: string | null;
}

const LEVEL_RANK: Record<TerritoryLevel, number> = {
  COUNTRY: 1,
  REGION: 2,
  PROVINCE: 3,
  MUNICIPALITY: 4,
  POSTAL_CODE: 5,
};

export function levelRank(level: TerritoryLevel): number {
  return LEVEL_RANK[level];
}

function norm(v: string | null | undefined): string {
  return (v ?? "").trim().toUpperCase();
}

export function territoryMatchesLead(t: TerritoryRef, loc: LeadLocation): boolean {
  const v = norm(t.value);
  if (!v) return false;
  switch (t.level) {
    case "COUNTRY":
      return norm(loc.country ?? "IT") === v;
    case "REGION":
      return norm(loc.region) === v;
    case "PROVINCE":
      return norm(loc.province) === v;
    case "MUNICIPALITY":
      return norm(loc.municipality) === v;
    case "POSTAL_CODE":
      return norm(loc.postalCode) === v;
  }
}

// Due territori si sovrappongono se sono identici, oppure se uno contiene l'altro
// secondo la gerarchia dichiarata (regione/provincia sul record figlio).
export function territoriesOverlap(a: TerritoryRef, b: TerritoryRef): boolean {
  if (a.level === b.level) return norm(a.value) === norm(b.value);
  const [outer, inner] = levelRank(a.level) < levelRank(b.level) ? [a, b] : [b, a];
  switch (outer.level) {
    case "COUNTRY":
      return true;
    case "REGION":
      return norm(inner.region) === norm(outer.value);
    case "PROVINCE":
      return norm(inner.province) === norm(outer.value);
    default:
      return false;
  }
}

export interface TerritoryConflict {
  conflictingTerritory: TerritoryRef;
  message: string;
}

// PRD sez. 11: un territorio esclusivo non può coesistere con un altro cliente sullo stesso territorio.
export function detectTerritoryConflict(
  candidate: TerritoryRef,
  existing: readonly TerritoryRef[],
  clientNames: Record<string, string> = {},
): TerritoryConflict | null {
  for (const t of existing) {
    if (t.clientId === candidate.clientId) continue;
    if (t.id && candidate.id && t.id === candidate.id) continue;
    if (!territoriesOverlap(candidate, t)) continue;
    if (t.exclusive) {
      const owner = clientNames[t.clientId] ?? t.clientId;
      return {
        conflictingTerritory: t,
        message: `Impossibile assegnare ${candidate.value} a ${clientNames[candidate.clientId] ?? candidate.clientId}. Il territorio è attualmente assegnato in esclusiva a ${owner}.`,
      };
    }
    if (candidate.exclusive) {
      const other = clientNames[t.clientId] ?? t.clientId;
      return {
        conflictingTerritory: t,
        message: `Impossibile assegnare ${candidate.value} in esclusiva: il territorio è già servito da ${other}. Rimuovere prima quel territorio o configurarlo come condiviso.`,
      };
    }
  }
  return null;
}
