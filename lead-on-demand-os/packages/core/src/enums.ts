// Enumerazioni condivise tra core, db, api e web.
// Sono `as const` per avere sia il tipo che il valore runtime.

export const ROLES = ["SUPER_ADMIN", "MANAGER", "OPERATOR", "CLIENT"] as const;
export type Role = (typeof ROLES)[number];

export const CLIENT_STATUSES = ["ACTIVE", "PAUSED", "OUT_OF_CREDIT", "CANCELLED"] as const;
export type ClientStatus = (typeof CLIENT_STATUSES)[number];

export const CLIENT_TYPES = ["RESIDENTIAL", "BUSINESS", "BOTH"] as const;
export type ClientType = (typeof CLIENT_TYPES)[number];

export const OFFER_TYPES = ["DIGITAL_QUALIFIED", "PHONE_PREQUALIFIED", "APPOINTMENT"] as const;
export type OfferType = (typeof OFFER_TYPES)[number];

export const PACKAGE_STATUSES = [
  "DRAFT",
  "AWAITING_PAYMENT",
  "ACTIVE",
  "LOW_BALANCE",
  "COMPLETED",
  "PAUSED",
  "EXPIRED",
  "CANCELLED",
] as const;
export type PackageStatus = (typeof PACKAGE_STATUSES)[number];

export const LEDGER_TYPES = ["PURCHASE", "DELIVERY", "REPLACEMENT", "MANUAL_ADJUSTMENT"] as const;
export type LedgerType = (typeof LEDGER_TYPES)[number];

export const LEAD_STATUSES = [
  "NEW",
  "VALIDATING",
  "TO_CONTACT",
  "ATTEMPT_1",
  "ATTEMPT_2",
  "ATTEMPT_3",
  "CALLBACK",
  "CONTACTED",
  "QUALIFYING",
  "QUALIFIED",
  "NOT_QUALIFIED",
  "WAITING_ASSIGNMENT",
  "ASSIGNED",
  "APPOINTMENT_BOOKED",
  "DELIVERED",
  "DELIVERY_FAILED",
  "REPLACEMENT_REQUESTED",
  "REPLACEMENT_APPROVED",
  "REPLACEMENT_REJECTED",
  "CLOSED_WON",
  "CLOSED_LOST",
] as const;
export type LeadStatus = (typeof LEAD_STATUSES)[number];

export const LEAD_TYPES = ["RESIDENTIAL", "BUSINESS"] as const;
export type LeadType = (typeof LEAD_TYPES)[number];

export const DEDUPE_RESULTS = ["UNIQUE", "DUPLICATE", "POSSIBLE_DUPLICATE"] as const;
export type DedupeResult = (typeof DEDUPE_RESULTS)[number];

export const QUALIFICATION_CATEGORIES = ["HOT", "QUALIFIED", "REVIEW", "NOT_QUALIFIED"] as const;
export type QualificationCategory = (typeof QUALIFICATION_CATEGORIES)[number];

export const APPOINTMENT_STATUSES = [
  "BOOKED",
  "CONFIRMED",
  "CANCELLED",
  "RESCHEDULED",
  "SHOW",
  "NO_SHOW",
  "COMPLETED",
] as const;
export type AppointmentStatus = (typeof APPOINTMENT_STATUSES)[number];

export const REPLACEMENT_STATUSES = ["REQUESTED", "APPROVED", "REJECTED"] as const;
export type ReplacementStatus = (typeof REPLACEMENT_STATUSES)[number];

export const REPLACEMENT_REASONS = [
  "NUMBER_NOT_EXISTING",
  "NEVER_INTERESTED",
  "OUT_OF_TERRITORY",
  "DUPLICATE",
  "NOT_OWNER",
  "FAKE_DATA",
  "CRITERIA_NOT_MET",
  "OTHER",
] as const;
export type ReplacementReason = (typeof REPLACEMENT_REASONS)[number];

export const SALES_OUTCOMES = [
  "CONTACTED",
  "APPOINTMENT",
  "SITE_VISIT_DONE",
  "QUOTE_SENT",
  "WON",
  "LOST",
] as const;
export type SalesOutcome = (typeof SALES_OUTCOMES)[number];

export const TERRITORY_LEVELS = ["COUNTRY", "REGION", "PROVINCE", "MUNICIPALITY", "POSTAL_CODE"] as const;
export type TerritoryLevel = (typeof TERRITORY_LEVELS)[number];

export const JOB_STATUSES = ["PENDING", "RUNNING", "DONE", "FAILED", "DEAD"] as const;
export type JobStatus = (typeof JOB_STATUSES)[number];

export const WEBHOOK_EVENT_STATUSES = ["RECEIVED", "PROCESSED", "IGNORED", "FAILED"] as const;

export const OUTBOUND_EVENTS = [
  "lead.created",
  "lead.qualified",
  "lead.assigned",
  "lead.delivered",
  "lead.rejected",
  "lead.replacement_requested",
  "lead.replaced",
  "package.low_balance",
  "package.completed",
  "appointment.booked",
  "appointment.show",
  "appointment.no_show",
  "sale.won",
  "sale.lost",
] as const;
export type OutboundEvent = (typeof OUTBOUND_EVENTS)[number];

export const NOTIFICATION_EVENTS = [
  "NEW_LEAD",
  "LEAD_QUALIFIED",
  "LEAD_WITHOUT_BUYER",
  "PACKAGE_LOW_BALANCE",
  "PACKAGE_COMPLETED",
  "REPLACEMENT_REQUESTED",
  "REPLACEMENT_RATE_ANOMALY",
  "CLIENT_INACTIVE",
  "APPOINTMENT_BOOKED",
  "NO_SHOW",
  "SALE_WON",
  "DELIVERY_FAILED",
] as const;
export type NotificationEvent = (typeof NOTIFICATION_EVENTS)[number];
