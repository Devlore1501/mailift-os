import type { DedupeResult } from "./enums.js";
import { addressLastnameKey, normalizeEmail, normalizePhone } from "./normalize.js";

export interface DedupeCandidate {
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  lastName?: string | null;
}

export interface ExistingLeadRef {
  id: string;
  phoneNormalized: string | null;
  emailNormalized: string | null;
  addressLastnameKey: string | null;
  createdAt: Date;
}

export interface DedupeOutcome {
  result: DedupeResult;
  matchedLeadId: string | null;
  matchedOn: Array<"phone" | "email" | "address_lastname">;
}

export const DEFAULT_DEDUPE_WINDOW_DAYS = 90;

// Regole (PRD sez. 14): telefono o email uguali nella finestra => DUPLICATE;
// solo indirizzo+cognome => POSSIBLE_DUPLICATE.
export function evaluateDuplicate(
  candidate: DedupeCandidate,
  existing: readonly ExistingLeadRef[],
  windowDays: number = DEFAULT_DEDUPE_WINDOW_DAYS,
  now: Date = new Date(),
): DedupeOutcome {
  const phone = normalizePhone(candidate.phone);
  const email = normalizeEmail(candidate.email);
  const addrKey = addressLastnameKey(candidate.address, candidate.lastName);
  const cutoff = now.getTime() - windowDays * 24 * 60 * 60 * 1000;

  let possible: ExistingLeadRef | null = null;
  for (const lead of existing) {
    if (lead.createdAt.getTime() < cutoff) continue;
    const matchedOn: DedupeOutcome["matchedOn"] = [];
    if (phone && lead.phoneNormalized === phone) matchedOn.push("phone");
    if (email && lead.emailNormalized === email) matchedOn.push("email");
    if (addrKey && lead.addressLastnameKey === addrKey) matchedOn.push("address_lastname");
    if (matchedOn.includes("phone") || matchedOn.includes("email")) {
      return { result: "DUPLICATE", matchedLeadId: lead.id, matchedOn };
    }
    if (matchedOn.length > 0 && !possible) possible = lead;
  }
  if (possible) {
    return { result: "POSSIBLE_DUPLICATE", matchedLeadId: possible.id, matchedOn: ["address_lastname"] };
  }
  return { result: "UNIQUE", matchedLeadId: null, matchedOn: [] };
}
