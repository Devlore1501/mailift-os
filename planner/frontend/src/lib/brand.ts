const STORAGE_KEY = "mailift-planner:last-brand-id";

export function getLastBrandId(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const id = Number(raw);
    return Number.isFinite(id) && id > 0 ? id : null;
  } catch {
    return null;
  }
}

export function setLastBrandId(id: number | null): void {
  try {
    if (id == null) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, String(id));
  } catch {
    // localStorage non disponibile: ignora
  }
}
