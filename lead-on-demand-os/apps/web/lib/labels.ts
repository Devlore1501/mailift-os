export const LEAD_STATUS_LABELS: Record<string, string> = {
  NEW: "Nuovo",
  VALIDATING: "In validazione",
  TO_CONTACT: "Da contattare",
  ATTEMPT_1: "Tentativo 1",
  ATTEMPT_2: "Tentativo 2",
  ATTEMPT_3: "Tentativo 3",
  CALLBACK: "Richiamata",
  CONTACTED: "Contattato",
  QUALIFYING: "In qualifica",
  QUALIFIED: "Qualificato",
  NOT_QUALIFIED: "Non qualificato",
  WAITING_ASSIGNMENT: "In attesa di buyer",
  ASSIGNED: "Assegnato",
  APPOINTMENT_BOOKED: "Appuntamento fissato",
  DELIVERED: "Consegnato",
  DELIVERY_FAILED: "Invio GHL fallito",
  REPLACEMENT_REQUESTED: "Sostituzione richiesta",
  REPLACEMENT_APPROVED: "Sostituito",
  REPLACEMENT_REJECTED: "Sostituzione rifiutata",
  CLOSED_WON: "Venduto",
  CLOSED_LOST: "Perso",
};

export const LEAD_STATUS_COLORS: Record<string, string> = {
  NEW: "bg-slate-100 text-slate-700",
  VALIDATING: "bg-slate-100 text-slate-700",
  TO_CONTACT: "bg-sky-100 text-sky-800",
  ATTEMPT_1: "bg-sky-100 text-sky-800",
  ATTEMPT_2: "bg-sky-100 text-sky-800",
  ATTEMPT_3: "bg-sky-100 text-sky-800",
  CALLBACK: "bg-violet-100 text-violet-800",
  CONTACTED: "bg-indigo-100 text-indigo-800",
  QUALIFYING: "bg-indigo-100 text-indigo-800",
  QUALIFIED: "bg-emerald-100 text-emerald-800",
  NOT_QUALIFIED: "bg-slate-200 text-slate-600",
  WAITING_ASSIGNMENT: "bg-amber-100 text-amber-800",
  ASSIGNED: "bg-emerald-100 text-emerald-800",
  APPOINTMENT_BOOKED: "bg-teal-100 text-teal-800",
  DELIVERED: "bg-emerald-200 text-emerald-900",
  DELIVERY_FAILED: "bg-red-100 text-red-800",
  REPLACEMENT_REQUESTED: "bg-orange-100 text-orange-800",
  REPLACEMENT_APPROVED: "bg-orange-200 text-orange-900",
  REPLACEMENT_REJECTED: "bg-slate-200 text-slate-700",
  CLOSED_WON: "bg-green-200 text-green-900",
  CLOSED_LOST: "bg-slate-300 text-slate-800",
};

export const PACKAGE_STATUS_LABELS: Record<string, string> = {
  DRAFT: "Bozza",
  AWAITING_PAYMENT: "In attesa di pagamento",
  ACTIVE: "Attivo",
  LOW_BALANCE: "In esaurimento",
  COMPLETED: "Completato",
  PAUSED: "In pausa",
  EXPIRED: "Scaduto",
  CANCELLED: "Annullato",
};

export const CLIENT_STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Attivo",
  PAUSED: "In pausa",
  OUT_OF_CREDIT: "Senza credito",
  CANCELLED: "Cessato",
};

export const CLIENT_TYPE_LABELS: Record<string, string> = { RESIDENTIAL: "Residenziale", BUSINESS: "Aziende", BOTH: "Entrambi" };
export const OFFER_TYPE_LABELS: Record<string, string> = { DIGITAL_QUALIFIED: "Lead qualificato digitalmente", PHONE_PREQUALIFIED: "Lead + prequalifica telefonica", APPOINTMENT: "Lead + appuntamento" };
export const LEAD_TYPE_LABELS: Record<string, string> = { RESIDENTIAL: "Residenziale", BUSINESS: "Aziendale" };
export const QUAL_CATEGORY_LABELS: Record<string, string> = { HOT: "Hot", QUALIFIED: "Qualificato", REVIEW: "Da rivedere", NOT_QUALIFIED: "Non qualificato" };
export const QUAL_CATEGORY_COLORS: Record<string, string> = { HOT: "bg-red-100 text-red-800", QUALIFIED: "bg-emerald-100 text-emerald-800", REVIEW: "bg-amber-100 text-amber-800", NOT_QUALIFIED: "bg-slate-200 text-slate-700" };
export const REPLACEMENT_REASON_LABELS: Record<string, string> = {
  NUMBER_NOT_EXISTING: "Numero inesistente",
  NEVER_INTERESTED: "Persona mai interessata",
  OUT_OF_TERRITORY: "Fuori territorio",
  DUPLICATE: "Duplicato",
  NOT_OWNER: "Non proprietario",
  FAKE_DATA: "Dati falsi",
  CRITERIA_NOT_MET: "Criteri concordati non rispettati",
  OTHER: "Altro",
};
export const REPLACEMENT_STATUS_LABELS: Record<string, string> = { REQUESTED: "In attesa", APPROVED: "Approvata", REJECTED: "Rifiutata" };
export const APPOINTMENT_STATUS_LABELS: Record<string, string> = { BOOKED: "Fissato", CONFIRMED: "Confermato", CANCELLED: "Annullato", RESCHEDULED: "Spostato", SHOW: "Show", NO_SHOW: "No-show", COMPLETED: "Completato" };
export const APPOINTMENT_KIND_LABELS: Record<string, string> = { CALL: "Telefonata", VIDEO: "Video call", SITE_VISIT: "Sopralluogo", CONSULTATION: "Consulenza" };
export const OUTCOME_LABELS: Record<string, string> = { CONTACTED: "Contattato", APPOINTMENT: "Appuntamento", SITE_VISIT_DONE: "Sopralluogo eseguito", QUOTE_SENT: "Preventivo inviato", WON: "Venduto", LOST: "Perso" };
export const ROLE_LABELS: Record<string, string> = { SUPER_ADMIN: "Super Admin", MANAGER: "Manager", OPERATOR: "Operatore", CLIENT: "Cliente" };
export const TERRITORY_LEVEL_LABELS: Record<string, string> = { COUNTRY: "Nazione", REGION: "Regione", PROVINCE: "Provincia", MUNICIPALITY: "Comune", POSTAL_CODE: "CAP" };
export const ROUTING_REASON_LABELS: Record<string, string> = {
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
export const NOTIFICATION_LABELS: Record<string, string> = {
  NEW_LEAD: "Nuovo lead",
  LEAD_QUALIFIED: "Lead qualificato",
  LEAD_WITHOUT_BUYER: "Lead senza buyer",
  PACKAGE_LOW_BALANCE: "Pacchetto in esaurimento",
  PACKAGE_COMPLETED: "Pacchetto terminato",
  REPLACEMENT_REQUESTED: "Sostituzione richiesta",
  REPLACEMENT_RATE_ANOMALY: "Replacement rate anomalo",
  CLIENT_INACTIVE: "Cliente senza attività",
  APPOINTMENT_BOOKED: "Appuntamento fissato",
  NO_SHOW: "No-show",
  SALE_WON: "Vendita registrata",
  DELIVERY_FAILED: "Invio GHL fallito",
};
