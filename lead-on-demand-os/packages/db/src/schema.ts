import { sql } from "drizzle-orm";
import {
  bigserial,
  boolean,
  index,
  integer,
  jsonb,
  numeric,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import {
  APPOINTMENT_STATUSES,
  CLIENT_STATUSES,
  CLIENT_TYPES,
  DEDUPE_RESULTS,
  JOB_STATUSES,
  LEAD_STATUSES,
  LEAD_TYPES,
  LEDGER_TYPES,
  OFFER_TYPES,
  PACKAGE_STATUSES,
  QUALIFICATION_CATEGORIES,
  REPLACEMENT_REASONS,
  REPLACEMENT_STATUSES,
  ROLES,
  SALES_OUTCOMES,
  TERRITORY_LEVELS,
  WEBHOOK_EVENT_STATUSES,
} from "@lod/core";

// Convenzione: ogni record legato a un cliente porta client_id (tenant del portale).
// Le query del portale cliente vengono sempre filtrate lato server su quel campo.

export const roleEnum = pgEnum("role", ROLES);
export const clientStatusEnum = pgEnum("client_status", CLIENT_STATUSES);
export const clientTypeEnum = pgEnum("client_type", CLIENT_TYPES);
export const offerTypeEnum = pgEnum("offer_type", OFFER_TYPES);
export const packageStatusEnum = pgEnum("package_status", PACKAGE_STATUSES);
export const ledgerTypeEnum = pgEnum("ledger_type", LEDGER_TYPES);
export const leadStatusEnum = pgEnum("lead_status", LEAD_STATUSES);
export const leadTypeEnum = pgEnum("lead_type", LEAD_TYPES);
export const dedupeResultEnum = pgEnum("dedupe_result", DEDUPE_RESULTS);
export const qualificationCategoryEnum = pgEnum("qualification_category", QUALIFICATION_CATEGORIES);
export const appointmentStatusEnum = pgEnum("appointment_status", APPOINTMENT_STATUSES);
export const replacementStatusEnum = pgEnum("replacement_status", REPLACEMENT_STATUSES);
export const replacementReasonEnum = pgEnum("replacement_reason", REPLACEMENT_REASONS);
export const salesOutcomeEnum = pgEnum("sales_outcome", SALES_OUTCOMES);
export const territoryLevelEnum = pgEnum("territory_level", TERRITORY_LEVELS);
export const jobStatusEnum = pgEnum("job_status", JOB_STATUSES);
export const webhookEventStatusEnum = pgEnum("webhook_event_status", WEBHOOK_EVENT_STATUSES);

const id = () => uuid("id").primaryKey().defaultRandom();
const createdAt = () => timestamp("created_at", { withTimezone: true }).notNull().defaultNow();
const updatedAt = () => timestamp("updated_at", { withTimezone: true }).notNull().defaultNow();

export const users = pgTable(
  "users",
  {
    id: id(),
    email: text("email").notNull(),
    passwordHash: text("password_hash").notNull(),
    fullName: text("full_name").notNull(),
    role: roleEnum("role").notNull(),
    active: boolean("active").notNull().default(true),
    lastLoginAt: timestamp("last_login_at", { withTimezone: true }),
    createdAt: createdAt(),
    updatedAt: updatedAt(),
  },
  (t) => [uniqueIndex("users_email_idx").on(t.email)],
);

export const clients = pgTable("clients", {
  id: id(),
  code: text("code").notNull().unique(), // es. CLI-0001
  legalName: text("legal_name").notNull(),
  tradeName: text("trade_name").notNull(),
  vatNumber: text("vat_number"),
  contactName: text("contact_name"),
  phone: text("phone"),
  email: text("email"),
  address: text("address"),
  region: text("region"),
  website: text("website"),
  vertical: text("vertical").notNull().default("photovoltaic"),
  clientType: clientTypeEnum("client_type").notNull().default("RESIDENTIAL"),
  offerType: offerTypeEnum("offer_type").notNull().default("PHONE_PREQUALIFIED"),
  defaultLeadPrice: numeric("default_lead_price", { precision: 10, scale: 2 }),
  status: clientStatusEnum("status").notNull().default("ACTIVE"),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  // Lead cap (PRD sez. 12)
  capDaily: integer("cap_daily"),
  capWeekly: integer("cap_weekly"),
  capMonthly: integer("cap_monthly"),
  priority: integer("priority").notNull().default(0),
  // Configurazione operativa
  ghlLocationId: text("ghl_location_id"),
  ghlPipelineId: text("ghl_pipeline_id"),
  ghlPipelineStageId: text("ghl_pipeline_stage_id"),
  ghlCalendarId: text("ghl_calendar_id"),
  webhookUrl: text("webhook_url"),
  webhookSecret: text("webhook_secret"),
  externalCrm: text("external_crm"),
  notificationEmail: text("notification_email"),
  notificationPhone: text("notification_phone"),
  accountManagerUserId: uuid("account_manager_user_id").references(() => users.id),
  replacementSlaHours: integer("replacement_sla_hours").notNull().default(72),
  dedupeWindowDays: integer("dedupe_window_days").notNull().default(90),
  // Criteri specifici del cliente sopra al template del verticale (JSON Criterion[])
  criteria: jsonb("criteria").notNull().default(sql`'[]'::jsonb`),
  notes: text("notes"),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
});

export const clientUsers = pgTable(
  "client_users",
  {
    id: id(),
    clientId: uuid("client_id").notNull().references(() => clients.id),
    userId: uuid("user_id").notNull().references(() => users.id),
    createdAt: createdAt(),
  },
  (t) => [uniqueIndex("client_users_unique").on(t.clientId, t.userId)],
);

export const packages = pgTable(
  "packages",
  {
    id: id(),
    code: text("code").notNull().unique(), // es. PV-2026-00031
    clientId: uuid("client_id").notNull().references(() => clients.id),
    productName: text("product_name").notNull(),
    offerType: offerTypeEnum("offer_type").notNull().default("PHONE_PREQUALIFIED"),
    quantity: integer("quantity").notNull(),
    unitPrice: numeric("unit_price", { precision: 10, scale: 2 }).notNull(),
    totalPrice: numeric("total_price", { precision: 12, scale: 2 }).notNull(),
    paid: boolean("paid").notNull().default(false),
    paidAt: timestamp("paid_at", { withTimezone: true }),
    paymentReference: text("payment_reference"),
    status: packageStatusEnum("status").notNull().default("DRAFT"),
    warningThreshold: integer("warning_threshold").notNull().default(5),
    alertThreshold: integer("alert_threshold").notNull().default(3),
    startsAt: timestamp("starts_at", { withTimezone: true }),
    expiresAt: timestamp("expires_at", { withTimezone: true }),
    lowBalanceNotifiedAt: timestamp("low_balance_notified_at", { withTimezone: true }),
    completedNotifiedAt: timestamp("completed_notified_at", { withTimezone: true }),
    notes: text("notes"),
    createdAt: createdAt(),
    updatedAt: updatedAt(),
  },
  (t) => [index("packages_client_idx").on(t.clientId)],
);

// LEAD_CREDIT_TRANSACTIONS (PRD sez. 7): ledger immutabile, solo INSERT.
export const packageTransactions = pgTable(
  "package_transactions",
  {
    id: id(),
    seq: bigserial("seq", { mode: "number" }).notNull(),
    clientId: uuid("client_id").notNull().references(() => clients.id),
    packageId: uuid("package_id").notNull().references(() => packages.id),
    leadId: uuid("lead_id"),
    type: ledgerTypeEnum("type").notNull(),
    quantity: integer("quantity").notNull(), // già con segno
    reason: text("reason"),
    createdAt: createdAt(),
    createdBy: uuid("created_by").references(() => users.id),
  },
  (t) => [index("pkg_tx_package_idx").on(t.packageId), index("pkg_tx_lead_idx").on(t.leadId)],
);

export const campaigns = pgTable("campaigns", {
  id: id(),
  name: text("name").notNull(),
  platform: text("platform"), // meta, google, other
  externalId: text("external_id"),
  vertical: text("vertical").notNull().default("photovoltaic"),
  active: boolean("active").notNull().default(true),
  createdAt: createdAt(),
});

export const marketingCosts = pgTable("marketing_costs", {
  id: id(),
  campaignId: uuid("campaign_id").references(() => campaigns.id),
  periodStart: timestamp("period_start", { withTimezone: true }).notNull(),
  periodEnd: timestamp("period_end", { withTimezone: true }).notNull(),
  amount: numeric("amount", { precision: 12, scale: 2 }).notNull(),
  note: text("note"),
  createdAt: createdAt(),
});

export const leadSources = pgTable("lead_sources", {
  id: id(),
  name: text("name").notNull(),
  kind: text("kind").notNull(), // landing, meta_form, google, api, manual
  apiKey: text("api_key").unique(),
  active: boolean("active").notNull().default(true),
  createdAt: createdAt(),
});

export const leads = pgTable(
  "leads",
  {
    id: id(),
    code: text("code").notNull().unique(), // es. LD-000123
    vertical: text("vertical").notNull().default("photovoltaic"),
    leadType: leadTypeEnum("lead_type").notNull().default("RESIDENTIAL"),
    status: leadStatusEnum("status").notNull().default("NEW"),
    // Dati personali
    firstName: text("first_name"),
    lastName: text("last_name"),
    phone: text("phone"),
    phoneNormalized: text("phone_normalized"),
    email: text("email"),
    emailNormalized: text("email_normalized"),
    address: text("address"),
    addressLastnameKey: text("address_lastname_key"),
    municipality: text("municipality"),
    postalCode: text("postal_code"),
    province: text("province"),
    region: text("region"),
    country: text("country").notNull().default("IT"),
    // Tracking marketing
    sourceId: uuid("source_id").references(() => leadSources.id),
    campaignId: uuid("campaign_id").references(() => campaigns.id),
    source: text("source"),
    medium: text("medium"),
    campaignName: text("campaign_name"),
    adSet: text("ad_set"),
    ad: text("ad"),
    creative: text("creative"),
    landingPage: text("landing_page"),
    utmSource: text("utm_source"),
    utmMedium: text("utm_medium"),
    utmCampaign: text("utm_campaign"),
    utmContent: text("utm_content"),
    utmTerm: text("utm_term"),
    clickIds: jsonb("click_ids").notNull().default(sql`'{}'::jsonb`),
    acquiredAt: timestamp("acquired_at", { withTimezone: true }).notNull().defaultNow(),
    attributedCost: numeric("attributed_cost", { precision: 10, scale: 2 }),
    consentRecorded: boolean("consent_recorded").notNull().default(false),
    consentText: text("consent_text"),
    // Campi specifici del verticale: template + custom fields (PRD sez. 60)
    customFields: jsonb("custom_fields").notNull().default(sql`'{}'::jsonb`),
    // Duplicati
    dedupeResult: dedupeResultEnum("dedupe_result"),
    duplicateOfLeadId: uuid("duplicate_of_lead_id"),
    // Qualifica
    qualificationTemplateId: uuid("qualification_template_id"),
    qualificationScore: integer("qualification_score"),
    qualificationCategory: qualificationCategoryEnum("qualification_category"),
    qualificationPassed: boolean("qualification_passed"),
    qualificationNotes: text("qualification_notes"),
    qualifiedAt: timestamp("qualified_at", { withTimezone: true }),
    qualifiedBy: uuid("qualified_by").references(() => users.id),
    notQualifiedReason: text("not_qualified_reason"),
    // Assegnazione e consegna (denormalizzati per query veloci; la verità è in lead_assignments)
    clientId: uuid("client_id").references(() => clients.id),
    packageId: uuid("package_id").references(() => packages.id),
    assignedAt: timestamp("assigned_at", { withTimezone: true }),
    deliveredAt: timestamp("delivered_at", { withTimezone: true }),
    creditCharged: boolean("credit_charged").notNull().default(false),
    waitingReasons: jsonb("waiting_reasons").notNull().default(sql`'[]'::jsonb`),
    // Operatore
    ownerUserId: uuid("owner_user_id").references(() => users.id),
    attempts: integer("attempts").notNull().default(0),
    callbackAt: timestamp("callback_at", { withTimezone: true }),
    lastContactAt: timestamp("last_contact_at", { withTimezone: true }),
    // GHL
    ghlContactId: text("ghl_contact_id"),
    ghlOpportunityId: text("ghl_opportunity_id"),
    ghlSyncedAt: timestamp("ghl_synced_at", { withTimezone: true }),
    ghlLastError: text("ghl_last_error"),
    // Esito replacement
    replaced: boolean("replaced").notNull().default(false),
    replacementLeadId: uuid("replacement_lead_id"),
    // Privacy
    anonymizedAt: timestamp("anonymized_at", { withTimezone: true }),
    createdAt: createdAt(),
    updatedAt: updatedAt(),
  },
  (t) => [
    index("leads_status_idx").on(t.status),
    index("leads_client_idx").on(t.clientId),
    index("leads_phone_idx").on(t.phoneNormalized),
    index("leads_email_idx").on(t.emailNormalized),
    index("leads_province_idx").on(t.province),
    index("leads_created_idx").on(t.createdAt),
  ],
);

export const leadAnswers = pgTable(
  "lead_answers",
  {
    id: id(),
    leadId: uuid("lead_id").notNull().references(() => leads.id),
    questionKey: text("question_key").notNull(),
    value: jsonb("value"),
    answeredBy: uuid("answered_by").references(() => users.id),
    createdAt: createdAt(),
    updatedAt: updatedAt(),
  },
  (t) => [uniqueIndex("lead_answers_unique").on(t.leadId, t.questionKey)],
);

export const leadStatusHistory = pgTable(
  "lead_status_history",
  {
    id: id(),
    seq: bigserial("seq", { mode: "number" }).notNull(),
    leadId: uuid("lead_id").notNull().references(() => leads.id),
    fromStatus: leadStatusEnum("from_status"),
    toStatus: leadStatusEnum("to_status").notNull(),
    reason: text("reason"),
    userId: uuid("user_id").references(() => users.id),
    createdAt: createdAt(),
  },
  (t) => [index("lead_status_history_lead_idx").on(t.leadId)],
);

export const leadNotes = pgTable(
  "lead_notes",
  {
    id: id(),
    leadId: uuid("lead_id").notNull().references(() => leads.id),
    userId: uuid("user_id").references(() => users.id),
    body: text("body").notNull(),
    visibleToClient: boolean("visible_to_client").notNull().default(false),
    createdAt: createdAt(),
  },
  (t) => [index("lead_notes_lead_idx").on(t.leadId)],
);

export const qualificationTemplates = pgTable("qualification_templates", {
  id: id(),
  name: text("name").notNull(),
  vertical: text("vertical").notNull(),
  leadType: leadTypeEnum("lead_type").notNull(),
  template: jsonb("template").notNull(), // QualificationTemplate
  criteria: jsonb("criteria").notNull().default(sql`'[]'::jsonb`), // Criterion[]
  scoreConfig: jsonb("score_config").notNull(), // ScoreConfig
  active: boolean("active").notNull().default(true),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
});

// Regole di qualifica aggiuntive per cliente (sopra al template): stesse strutture Criterion.
export const qualificationRules = pgTable("qualification_rules", {
  id: id(),
  clientId: uuid("client_id").notNull().references(() => clients.id),
  field: text("field").notNull(),
  op: text("op").notNull(),
  value: jsonb("value"),
  kind: text("kind").notNull(), // MANDATORY | PREFERRED | EXCLUSION
  label: text("label").notNull(),
  active: boolean("active").notNull().default(true),
  createdAt: createdAt(),
});

export const territories = pgTable(
  "territories",
  {
    id: id(),
    clientId: uuid("client_id").notNull().references(() => clients.id),
    level: territoryLevelEnum("level").notNull(),
    value: text("value").notNull(),
    region: text("region"),
    province: text("province"),
    exclusive: boolean("exclusive").notNull().default(false),
    active: boolean("active").notNull().default(true),
    createdAt: createdAt(),
  },
  (t) => [index("territories_client_idx").on(t.clientId), index("territories_value_idx").on(t.level, t.value)],
);

// Regole di routing aggiuntive/override (PRD sez. 10). L'MVP usa territori + criteri + cap;
// questa tabella tiene condizioni custom serializzate come Criterion[] con priorità.
export const routingRules = pgTable("routing_rules", {
  id: id(),
  clientId: uuid("client_id").notNull().references(() => clients.id),
  name: text("name").notNull(),
  conditions: jsonb("conditions").notNull().default(sql`'[]'::jsonb`),
  priority: integer("priority").notNull().default(0),
  active: boolean("active").notNull().default(true),
  createdAt: createdAt(),
});

export const leadAssignments = pgTable(
  "lead_assignments",
  {
    id: id(),
    leadId: uuid("lead_id").notNull().references(() => leads.id),
    clientId: uuid("client_id").notNull().references(() => clients.id),
    packageId: uuid("package_id").notNull().references(() => packages.id),
    matchedTerritoryId: uuid("matched_territory_id").references(() => territories.id),
    decision: jsonb("decision"), // RoutingDecision serializzata
    manual: boolean("manual").notNull().default(false),
    assignedBy: uuid("assigned_by").references(() => users.id),
    active: boolean("active").notNull().default(true),
    createdAt: createdAt(),
  },
  (t) => [index("lead_assignments_lead_idx").on(t.leadId), index("lead_assignments_client_idx").on(t.clientId)],
);

export const appointments = pgTable(
  "appointments",
  {
    id: id(),
    leadId: uuid("lead_id").notNull().references(() => leads.id),
    clientId: uuid("client_id").notNull().references(() => clients.id),
    packageId: uuid("package_id").references(() => packages.id),
    operatorUserId: uuid("operator_user_id").references(() => users.id),
    kind: text("kind").notNull().default("SITE_VISIT"), // CALL | VIDEO | SITE_VISIT | CONSULTATION
    status: appointmentStatusEnum("status").notNull().default("BOOKED"),
    startsAt: timestamp("starts_at", { withTimezone: true }).notNull(),
    endsAt: timestamp("ends_at", { withTimezone: true }),
    timezone: text("timezone").notNull().default("Europe/Rome"),
    calendarProvider: text("calendar_provider"),
    calendarId: text("calendar_id"),
    externalId: text("external_id"),
    notes: text("notes"),
    createdAt: createdAt(),
    updatedAt: updatedAt(),
  },
  (t) => [index("appointments_lead_idx").on(t.leadId), index("appointments_client_idx").on(t.clientId), uniqueIndex("appointments_external_idx").on(t.calendarProvider, t.externalId)],
);

export const replacementRequests = pgTable(
  "replacement_requests",
  {
    id: id(),
    leadId: uuid("lead_id").notNull().references(() => leads.id),
    clientId: uuid("client_id").notNull().references(() => clients.id),
    packageId: uuid("package_id").notNull().references(() => packages.id),
    reason: replacementReasonEnum("reason").notNull(),
    note: text("note"),
    attachments: jsonb("attachments").notNull().default(sql`'[]'::jsonb`),
    status: replacementStatusEnum("status").notNull().default("REQUESTED"),
    requestedBy: uuid("requested_by").references(() => users.id),
    decidedBy: uuid("decided_by").references(() => users.id),
    decisionNote: text("decision_note"),
    decidedAt: timestamp("decided_at", { withTimezone: true }),
    createdAt: createdAt(),
  },
  (t) => [index("replacement_lead_idx").on(t.leadId), index("replacement_client_idx").on(t.clientId)],
);

export const salesOutcomes = pgTable(
  "sales_outcomes",
  {
    id: id(),
    leadId: uuid("lead_id").notNull().references(() => leads.id),
    clientId: uuid("client_id").notNull().references(() => clients.id),
    outcome: salesOutcomeEnum("outcome").notNull(),
    lostReason: text("lost_reason"),
    contractValue: numeric("contract_value", { precision: 12, scale: 2 }),
    soldAt: timestamp("sold_at", { withTimezone: true }),
    margin: numeric("margin", { precision: 12, scale: 2 }),
    product: text("product"),
    reportedBy: uuid("reported_by").references(() => users.id),
    createdAt: createdAt(),
  },
  (t) => [index("sales_outcomes_lead_idx").on(t.leadId)],
);

export const integrations = pgTable("integrations", {
  id: id(),
  clientId: uuid("client_id").references(() => clients.id), // null = integrazione globale Lead on Demand
  provider: text("provider").notNull(), // ghl
  config: jsonb("config").notNull().default(sql`'{}'::jsonb`), // {locationId, apiKeySecretRef, pipelineId, ...}
  active: boolean("active").notNull().default(true),
  createdAt: createdAt(),
  updatedAt: updatedAt(),
});

export const ghlMappings = pgTable(
  "ghl_mappings",
  {
    id: id(),
    clientId: uuid("client_id").references(() => clients.id), // null = mapping di default
    lodField: text("lod_field").notNull(), // es. monthly_bill, qualification_status
    ghlField: text("ghl_field").notNull(), // es. custom_field_xxx oppure "tag:hot"
    kind: text("kind").notNull().default("custom_field"), // custom_field | standard | tag
    createdAt: createdAt(),
  },
  (t) => [index("ghl_mappings_client_idx").on(t.clientId)],
);

// Eventi esterni ricevuti (PRD sez. 54): idempotenti su provider + external_event_id.
export const webhookEvents = pgTable(
  "webhook_events",
  {
    id: id(),
    provider: text("provider").notNull(),
    externalEventId: text("external_event_id").notNull(),
    eventType: text("event_type").notNull(),
    payload: jsonb("payload").notNull(),
    status: webhookEventStatusEnum("status").notNull().default("RECEIVED"),
    error: text("error"),
    leadId: uuid("lead_id"),
    receivedAt: timestamp("received_at", { withTimezone: true }).notNull().defaultNow(),
    processedAt: timestamp("processed_at", { withTimezone: true }),
  },
  (t) => [uniqueIndex("webhook_events_unique").on(t.provider, t.externalEventId)],
);

// Coda persistente per job asincroni con retry (consegna GHL, webhook in uscita, notifiche).
export const jobs = pgTable(
  "jobs",
  {
    id: id(),
    kind: text("kind").notNull(), // ghl.deliver | webhook.dispatch | notification.send
    payload: jsonb("payload").notNull(),
    status: jobStatusEnum("status").notNull().default("PENDING"),
    attempts: integer("attempts").notNull().default(0),
    maxAttempts: integer("max_attempts").notNull().default(5),
    runAt: timestamp("run_at", { withTimezone: true }).notNull().defaultNow(),
    lastError: text("last_error"),
    dedupeKey: text("dedupe_key"),
    createdAt: createdAt(),
    updatedAt: updatedAt(),
  },
  (t) => [index("jobs_status_run_idx").on(t.status, t.runAt), uniqueIndex("jobs_dedupe_idx").on(t.dedupeKey)],
);

export const outboundEvents = pgTable(
  "outbound_events",
  {
    id: id(),
    eventType: text("event_type").notNull(),
    clientId: uuid("client_id").references(() => clients.id),
    leadId: uuid("lead_id"),
    payload: jsonb("payload").notNull(),
    createdAt: createdAt(),
  },
  (t) => [index("outbound_events_created_idx").on(t.createdAt)],
);

export const notifications = pgTable(
  "notifications",
  {
    id: id(),
    event: text("event").notNull(),
    title: text("title").notNull(),
    body: text("body"),
    severity: text("severity").notNull().default("info"), // info | warning | critical
    userId: uuid("user_id").references(() => users.id), // null = per tutti gli admin/manager
    clientId: uuid("client_id").references(() => clients.id),
    leadId: uuid("lead_id"),
    readAt: timestamp("read_at", { withTimezone: true }),
    createdAt: createdAt(),
  },
  (t) => [index("notifications_user_idx").on(t.userId, t.readAt)],
);

export const auditLogs = pgTable(
  "audit_logs",
  {
    id: id(),
    seq: bigserial("seq", { mode: "number" }).notNull(),
    userId: uuid("user_id").references(() => users.id),
    action: text("action").notNull(), // lead.qualified, package.credit, ...
    entityType: text("entity_type").notNull(),
    entityId: text("entity_id"),
    clientId: uuid("client_id"),
    leadId: uuid("lead_id"),
    summary: text("summary").notNull(),
    details: jsonb("details"),
    ip: text("ip"),
    createdAt: createdAt(),
  },
  (t) => [index("audit_entity_idx").on(t.entityType, t.entityId), index("audit_lead_idx").on(t.leadId), index("audit_created_idx").on(t.createdAt)],
);

export const settings = pgTable("settings", {
  key: text("key").primaryKey(),
  value: jsonb("value").notNull(),
  updatedAt: updatedAt(),
});

export const counters = pgTable("counters", {
  name: text("name").primaryKey(),
  value: integer("value").notNull().default(0),
});
