import type { LeadStatus } from "./enums.js";

// Transizioni ammesse della pipeline interna (PRD sez. 9).
// Ogni cambio di stato passa da qui: se la transizione non è in mappa, viene rifiutata.
const TRANSITIONS: Record<LeadStatus, readonly LeadStatus[]> = {
  NEW: ["VALIDATING", "NOT_QUALIFIED"],
  VALIDATING: ["TO_CONTACT", "NOT_QUALIFIED", "QUALIFIED", "WAITING_ASSIGNMENT"],
  TO_CONTACT: ["ATTEMPT_1", "CONTACTED", "CALLBACK", "NOT_QUALIFIED"],
  ATTEMPT_1: ["ATTEMPT_2", "CONTACTED", "CALLBACK", "NOT_QUALIFIED"],
  ATTEMPT_2: ["ATTEMPT_3", "CONTACTED", "CALLBACK", "NOT_QUALIFIED"],
  ATTEMPT_3: ["CONTACTED", "CALLBACK", "NOT_QUALIFIED"],
  CALLBACK: ["ATTEMPT_1", "ATTEMPT_2", "ATTEMPT_3", "CONTACTED", "NOT_QUALIFIED"],
  CONTACTED: ["QUALIFYING", "CALLBACK", "NOT_QUALIFIED"],
  QUALIFYING: ["QUALIFIED", "NOT_QUALIFIED", "CALLBACK"],
  QUALIFIED: ["WAITING_ASSIGNMENT", "ASSIGNED", "NOT_QUALIFIED"],
  NOT_QUALIFIED: ["TO_CONTACT", "QUALIFYING"],
  WAITING_ASSIGNMENT: ["ASSIGNED", "NOT_QUALIFIED"],
  ASSIGNED: ["APPOINTMENT_BOOKED", "DELIVERED", "DELIVERY_FAILED", "WAITING_ASSIGNMENT"],
  APPOINTMENT_BOOKED: ["DELIVERED", "DELIVERY_FAILED"],
  DELIVERY_FAILED: ["DELIVERED", "ASSIGNED", "REPLACEMENT_REQUESTED"],
  DELIVERED: ["APPOINTMENT_BOOKED", "DELIVERY_FAILED", "REPLACEMENT_REQUESTED", "CLOSED_WON", "CLOSED_LOST"],
  REPLACEMENT_REQUESTED: ["REPLACEMENT_APPROVED", "REPLACEMENT_REJECTED"],
  REPLACEMENT_APPROVED: [],
  REPLACEMENT_REJECTED: ["CLOSED_WON", "CLOSED_LOST", "REPLACEMENT_REQUESTED"],
  CLOSED_WON: [],
  CLOSED_LOST: ["REPLACEMENT_REQUESTED"],
};

export function allowedTransitions(from: LeadStatus): readonly LeadStatus[] {
  return TRANSITIONS[from];
}

export function canTransition(from: LeadStatus, to: LeadStatus): boolean {
  return TRANSITIONS[from].includes(to);
}

export class InvalidTransitionError extends Error {
  constructor(
    public readonly from: LeadStatus,
    public readonly to: LeadStatus,
  ) {
    super(`Transizione non ammessa: ${from} -> ${to}`);
    this.name = "InvalidTransitionError";
  }
}

export function assertTransition(from: LeadStatus, to: LeadStatus): void {
  if (!canTransition(from, to)) throw new InvalidTransitionError(from, to);
}

// Stati in cui il lead è "in lavorazione" dal team Lead on Demand.
export const OPERATOR_QUEUE_STATUSES: readonly LeadStatus[] = [
  "TO_CONTACT",
  "ATTEMPT_1",
  "ATTEMPT_2",
  "ATTEMPT_3",
  "CALLBACK",
  "CONTACTED",
  "QUALIFYING",
];

// Stati che contano come "consegnato" per il cliente.
export const DELIVERED_STATUSES: readonly LeadStatus[] = [
  "DELIVERED",
  "APPOINTMENT_BOOKED",
  "REPLACEMENT_REQUESTED",
  "REPLACEMENT_APPROVED",
  "REPLACEMENT_REJECTED",
  "CLOSED_WON",
  "CLOSED_LOST",
];

export function nextAttemptStatus(current: LeadStatus): LeadStatus {
  switch (current) {
    case "TO_CONTACT":
    case "CALLBACK":
      return "ATTEMPT_1";
    case "ATTEMPT_1":
      return "ATTEMPT_2";
    case "ATTEMPT_2":
    case "ATTEMPT_3":
      return "ATTEMPT_3";
    default:
      return "ATTEMPT_1";
  }
}
