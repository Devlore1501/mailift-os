import type { LedgerType, PackageStatus } from "./enums.js";

export interface LedgerEntry {
  type: LedgerType;
  quantity: number;
}

// Il saldo è sempre la somma delle transazioni: nessun campo "residui" modificabile a mano.
export function computeBalance(entries: readonly LedgerEntry[]): number {
  return entries.reduce((acc, e) => acc + e.quantity, 0);
}

export function signedQuantity(type: LedgerType, quantity: number): number {
  const abs = Math.abs(quantity);
  switch (type) {
    case "PURCHASE":
    case "REPLACEMENT":
      return abs;
    case "DELIVERY":
      return -abs;
    case "MANUAL_ADJUSTMENT":
      return quantity;
  }
}

export interface BalanceThresholds {
  warningAt: number; // default 5
  alertAt: number; // default 3
}

export const DEFAULT_THRESHOLDS: BalanceThresholds = { warningAt: 5, alertAt: 3 };

// Stato derivato dal saldo per un pacchetto attivo. Gli stati "amministrativi"
// (DRAFT, AWAITING_PAYMENT, PAUSED, EXPIRED, CANCELLED) non vengono toccati.
export function derivePackageStatus(
  current: PackageStatus,
  balance: number,
  thresholds: BalanceThresholds = DEFAULT_THRESHOLDS,
): PackageStatus {
  const managed: PackageStatus[] = ["ACTIVE", "LOW_BALANCE", "COMPLETED"];
  if (!managed.includes(current)) return current;
  if (balance <= 0) return "COMPLETED";
  if (balance <= thresholds.warningAt) return "LOW_BALANCE";
  return "ACTIVE";
}

export function isRoutable(status: PackageStatus, balance: number): boolean {
  return (status === "ACTIVE" || status === "LOW_BALANCE") && balance > 0;
}
