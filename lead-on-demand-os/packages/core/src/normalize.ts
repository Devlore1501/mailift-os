// Normalizzazione telefono in formato E.164 con default Italia.
// Accetta "+39 340 123 4567", "0039340...", "340 1234567", "3401234567".
export function normalizePhone(raw: string | null | undefined, defaultCountry = "39"): string | null {
  if (!raw) return null;
  let digits = raw.replace(/[^\d+]/g, "");
  if (digits.startsWith("00")) digits = "+" + digits.slice(2);
  if (digits.startsWith("+")) {
    digits = digits.slice(1);
  } else {
    // Numero nazionale: rimuove uno zero iniziale (fissi IT lo tengono: gestito sotto)
    if (digits.startsWith(defaultCountry) && digits.length >= 11) {
      // già con prefisso senza +
    } else {
      digits = defaultCountry + digits;
    }
  }
  digits = digits.replace(/\D/g, "");
  if (digits.length < 8 || digits.length > 15) return null;
  return "+" + digits;
}

export function normalizeEmail(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const e = raw.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return null;
  return e;
}

export function normalizeText(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const t = raw
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
  return t || null;
}

// Chiave indirizzo + cognome per il controllo duplicati "morbido".
export function addressLastnameKey(address: string | null | undefined, lastName: string | null | undefined): string | null {
  const a = normalizeText(address);
  const l = normalizeText(lastName);
  if (!a || !l) return null;
  return `${l}|${a}`;
}

export function normalizeProvince(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const t = raw.trim().toUpperCase();
  return t || null;
}
