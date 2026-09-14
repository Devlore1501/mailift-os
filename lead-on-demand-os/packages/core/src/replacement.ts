export const DEFAULT_REPLACEMENT_SLA_HOURS = 72;

export interface SlaCheck {
  allowed: boolean;
  deadline: Date;
  message: string | null;
}

// PRD sez. 24: la richiesta è ammessa entro la finestra SLA dalla consegna.
export function checkReplacementSla(deliveredAt: Date, slaHours: number, now: Date = new Date()): SlaCheck {
  const deadline = new Date(deliveredAt.getTime() + slaHours * 60 * 60 * 1000);
  const allowed = now.getTime() <= deadline.getTime();
  return {
    allowed,
    deadline,
    message: allowed ? null : "Periodo disponibile per richiedere la sostituzione terminato.",
  };
}
