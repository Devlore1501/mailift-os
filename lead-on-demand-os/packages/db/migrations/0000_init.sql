CREATE TYPE "public"."appointment_status" AS ENUM('BOOKED', 'CONFIRMED', 'CANCELLED', 'RESCHEDULED', 'SHOW', 'NO_SHOW', 'COMPLETED');--> statement-breakpoint
CREATE TYPE "public"."client_status" AS ENUM('ACTIVE', 'PAUSED', 'OUT_OF_CREDIT', 'CANCELLED');--> statement-breakpoint
CREATE TYPE "public"."client_type" AS ENUM('RESIDENTIAL', 'BUSINESS', 'BOTH');--> statement-breakpoint
CREATE TYPE "public"."dedupe_result" AS ENUM('UNIQUE', 'DUPLICATE', 'POSSIBLE_DUPLICATE');--> statement-breakpoint
CREATE TYPE "public"."job_status" AS ENUM('PENDING', 'RUNNING', 'DONE', 'FAILED', 'DEAD');--> statement-breakpoint
CREATE TYPE "public"."lead_status" AS ENUM('NEW', 'VALIDATING', 'TO_CONTACT', 'ATTEMPT_1', 'ATTEMPT_2', 'ATTEMPT_3', 'CALLBACK', 'CONTACTED', 'QUALIFYING', 'QUALIFIED', 'NOT_QUALIFIED', 'WAITING_ASSIGNMENT', 'ASSIGNED', 'APPOINTMENT_BOOKED', 'DELIVERED', 'DELIVERY_FAILED', 'REPLACEMENT_REQUESTED', 'REPLACEMENT_APPROVED', 'REPLACEMENT_REJECTED', 'CLOSED_WON', 'CLOSED_LOST');--> statement-breakpoint
CREATE TYPE "public"."lead_type" AS ENUM('RESIDENTIAL', 'BUSINESS');--> statement-breakpoint
CREATE TYPE "public"."ledger_type" AS ENUM('PURCHASE', 'DELIVERY', 'REPLACEMENT', 'MANUAL_ADJUSTMENT');--> statement-breakpoint
CREATE TYPE "public"."offer_type" AS ENUM('DIGITAL_QUALIFIED', 'PHONE_PREQUALIFIED', 'APPOINTMENT');--> statement-breakpoint
CREATE TYPE "public"."package_status" AS ENUM('DRAFT', 'AWAITING_PAYMENT', 'ACTIVE', 'LOW_BALANCE', 'COMPLETED', 'PAUSED', 'EXPIRED', 'CANCELLED');--> statement-breakpoint
CREATE TYPE "public"."qualification_category" AS ENUM('HOT', 'QUALIFIED', 'REVIEW', 'NOT_QUALIFIED');--> statement-breakpoint
CREATE TYPE "public"."replacement_reason" AS ENUM('NUMBER_NOT_EXISTING', 'NEVER_INTERESTED', 'OUT_OF_TERRITORY', 'DUPLICATE', 'NOT_OWNER', 'FAKE_DATA', 'CRITERIA_NOT_MET', 'OTHER');--> statement-breakpoint
CREATE TYPE "public"."replacement_status" AS ENUM('REQUESTED', 'APPROVED', 'REJECTED');--> statement-breakpoint
CREATE TYPE "public"."role" AS ENUM('SUPER_ADMIN', 'MANAGER', 'OPERATOR', 'CLIENT');--> statement-breakpoint
CREATE TYPE "public"."sales_outcome" AS ENUM('CONTACTED', 'APPOINTMENT', 'SITE_VISIT_DONE', 'QUOTE_SENT', 'WON', 'LOST');--> statement-breakpoint
CREATE TYPE "public"."territory_level" AS ENUM('COUNTRY', 'REGION', 'PROVINCE', 'MUNICIPALITY', 'POSTAL_CODE');--> statement-breakpoint
CREATE TYPE "public"."webhook_event_status" AS ENUM('RECEIVED', 'PROCESSED', 'IGNORED', 'FAILED');--> statement-breakpoint
CREATE TABLE "appointments" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"lead_id" uuid NOT NULL,
	"client_id" uuid NOT NULL,
	"package_id" uuid,
	"operator_user_id" uuid,
	"kind" text DEFAULT 'SITE_VISIT' NOT NULL,
	"status" "appointment_status" DEFAULT 'BOOKED' NOT NULL,
	"starts_at" timestamp with time zone NOT NULL,
	"ends_at" timestamp with time zone,
	"timezone" text DEFAULT 'Europe/Rome' NOT NULL,
	"calendar_provider" text,
	"calendar_id" text,
	"external_id" text,
	"notes" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "audit_logs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"seq" bigserial NOT NULL,
	"user_id" uuid,
	"action" text NOT NULL,
	"entity_type" text NOT NULL,
	"entity_id" text,
	"client_id" uuid,
	"lead_id" uuid,
	"summary" text NOT NULL,
	"details" jsonb,
	"ip" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "campaigns" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"platform" text,
	"external_id" text,
	"vertical" text DEFAULT 'photovoltaic' NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "client_users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"client_id" uuid NOT NULL,
	"user_id" uuid NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "clients" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"code" text NOT NULL,
	"legal_name" text NOT NULL,
	"trade_name" text NOT NULL,
	"vat_number" text,
	"contact_name" text,
	"phone" text,
	"email" text,
	"address" text,
	"region" text,
	"website" text,
	"vertical" text DEFAULT 'photovoltaic' NOT NULL,
	"client_type" "client_type" DEFAULT 'RESIDENTIAL' NOT NULL,
	"offer_type" "offer_type" DEFAULT 'PHONE_PREQUALIFIED' NOT NULL,
	"default_lead_price" numeric(10, 2),
	"status" "client_status" DEFAULT 'ACTIVE' NOT NULL,
	"start_date" timestamp with time zone,
	"end_date" timestamp with time zone,
	"cap_daily" integer,
	"cap_weekly" integer,
	"cap_monthly" integer,
	"priority" integer DEFAULT 0 NOT NULL,
	"ghl_location_id" text,
	"ghl_pipeline_id" text,
	"ghl_pipeline_stage_id" text,
	"ghl_calendar_id" text,
	"webhook_url" text,
	"webhook_secret" text,
	"external_crm" text,
	"notification_email" text,
	"notification_phone" text,
	"account_manager_user_id" uuid,
	"replacement_sla_hours" integer DEFAULT 72 NOT NULL,
	"dedupe_window_days" integer DEFAULT 90 NOT NULL,
	"criteria" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"notes" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "clients_code_unique" UNIQUE("code")
);
--> statement-breakpoint
CREATE TABLE "counters" (
	"name" text PRIMARY KEY NOT NULL,
	"value" integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE TABLE "ghl_mappings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"client_id" uuid,
	"lod_field" text NOT NULL,
	"ghl_field" text NOT NULL,
	"kind" text DEFAULT 'custom_field' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "integrations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"client_id" uuid,
	"provider" text NOT NULL,
	"config" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "jobs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"kind" text NOT NULL,
	"payload" jsonb NOT NULL,
	"status" "job_status" DEFAULT 'PENDING' NOT NULL,
	"attempts" integer DEFAULT 0 NOT NULL,
	"max_attempts" integer DEFAULT 5 NOT NULL,
	"run_at" timestamp with time zone DEFAULT now() NOT NULL,
	"last_error" text,
	"dedupe_key" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "lead_answers" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"lead_id" uuid NOT NULL,
	"question_key" text NOT NULL,
	"value" jsonb,
	"answered_by" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "lead_assignments" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"lead_id" uuid NOT NULL,
	"client_id" uuid NOT NULL,
	"package_id" uuid NOT NULL,
	"matched_territory_id" uuid,
	"decision" jsonb,
	"manual" boolean DEFAULT false NOT NULL,
	"assigned_by" uuid,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "lead_notes" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"lead_id" uuid NOT NULL,
	"user_id" uuid,
	"body" text NOT NULL,
	"visible_to_client" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "lead_sources" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"kind" text NOT NULL,
	"api_key" text,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "lead_sources_api_key_unique" UNIQUE("api_key")
);
--> statement-breakpoint
CREATE TABLE "lead_status_history" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"seq" bigserial NOT NULL,
	"lead_id" uuid NOT NULL,
	"from_status" "lead_status",
	"to_status" "lead_status" NOT NULL,
	"reason" text,
	"user_id" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "leads" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"code" text NOT NULL,
	"vertical" text DEFAULT 'photovoltaic' NOT NULL,
	"lead_type" "lead_type" DEFAULT 'RESIDENTIAL' NOT NULL,
	"status" "lead_status" DEFAULT 'NEW' NOT NULL,
	"first_name" text,
	"last_name" text,
	"phone" text,
	"phone_normalized" text,
	"email" text,
	"email_normalized" text,
	"address" text,
	"address_lastname_key" text,
	"municipality" text,
	"postal_code" text,
	"province" text,
	"region" text,
	"country" text DEFAULT 'IT' NOT NULL,
	"source_id" uuid,
	"campaign_id" uuid,
	"source" text,
	"medium" text,
	"campaign_name" text,
	"ad_set" text,
	"ad" text,
	"creative" text,
	"landing_page" text,
	"utm_source" text,
	"utm_medium" text,
	"utm_campaign" text,
	"utm_content" text,
	"utm_term" text,
	"click_ids" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"acquired_at" timestamp with time zone DEFAULT now() NOT NULL,
	"attributed_cost" numeric(10, 2),
	"consent_recorded" boolean DEFAULT false NOT NULL,
	"consent_text" text,
	"custom_fields" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"dedupe_result" "dedupe_result",
	"duplicate_of_lead_id" uuid,
	"qualification_template_id" uuid,
	"qualification_score" integer,
	"qualification_category" "qualification_category",
	"qualification_passed" boolean,
	"qualification_notes" text,
	"qualified_at" timestamp with time zone,
	"qualified_by" uuid,
	"not_qualified_reason" text,
	"client_id" uuid,
	"package_id" uuid,
	"assigned_at" timestamp with time zone,
	"delivered_at" timestamp with time zone,
	"credit_charged" boolean DEFAULT false NOT NULL,
	"waiting_reasons" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"owner_user_id" uuid,
	"attempts" integer DEFAULT 0 NOT NULL,
	"callback_at" timestamp with time zone,
	"last_contact_at" timestamp with time zone,
	"ghl_contact_id" text,
	"ghl_opportunity_id" text,
	"ghl_synced_at" timestamp with time zone,
	"ghl_last_error" text,
	"replaced" boolean DEFAULT false NOT NULL,
	"replacement_lead_id" uuid,
	"anonymized_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "leads_code_unique" UNIQUE("code")
);
--> statement-breakpoint
CREATE TABLE "marketing_costs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"campaign_id" uuid,
	"period_start" timestamp with time zone NOT NULL,
	"period_end" timestamp with time zone NOT NULL,
	"amount" numeric(12, 2) NOT NULL,
	"note" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "notifications" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"event" text NOT NULL,
	"title" text NOT NULL,
	"body" text,
	"severity" text DEFAULT 'info' NOT NULL,
	"user_id" uuid,
	"client_id" uuid,
	"lead_id" uuid,
	"read_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "outbound_events" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"event_type" text NOT NULL,
	"client_id" uuid,
	"lead_id" uuid,
	"payload" jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "package_transactions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"seq" bigserial NOT NULL,
	"client_id" uuid NOT NULL,
	"package_id" uuid NOT NULL,
	"lead_id" uuid,
	"type" "ledger_type" NOT NULL,
	"quantity" integer NOT NULL,
	"reason" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" uuid
);
--> statement-breakpoint
CREATE TABLE "packages" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"code" text NOT NULL,
	"client_id" uuid NOT NULL,
	"product_name" text NOT NULL,
	"offer_type" "offer_type" DEFAULT 'PHONE_PREQUALIFIED' NOT NULL,
	"quantity" integer NOT NULL,
	"unit_price" numeric(10, 2) NOT NULL,
	"total_price" numeric(12, 2) NOT NULL,
	"paid" boolean DEFAULT false NOT NULL,
	"paid_at" timestamp with time zone,
	"payment_reference" text,
	"status" "package_status" DEFAULT 'DRAFT' NOT NULL,
	"warning_threshold" integer DEFAULT 5 NOT NULL,
	"alert_threshold" integer DEFAULT 3 NOT NULL,
	"starts_at" timestamp with time zone,
	"expires_at" timestamp with time zone,
	"low_balance_notified_at" timestamp with time zone,
	"completed_notified_at" timestamp with time zone,
	"notes" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "packages_code_unique" UNIQUE("code")
);
--> statement-breakpoint
CREATE TABLE "qualification_rules" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"client_id" uuid NOT NULL,
	"field" text NOT NULL,
	"op" text NOT NULL,
	"value" jsonb,
	"kind" text NOT NULL,
	"label" text NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "qualification_templates" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"vertical" text NOT NULL,
	"lead_type" "lead_type" NOT NULL,
	"template" jsonb NOT NULL,
	"criteria" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"score_config" jsonb NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "replacement_requests" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"lead_id" uuid NOT NULL,
	"client_id" uuid NOT NULL,
	"package_id" uuid NOT NULL,
	"reason" "replacement_reason" NOT NULL,
	"note" text,
	"attachments" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"status" "replacement_status" DEFAULT 'REQUESTED' NOT NULL,
	"requested_by" uuid,
	"decided_by" uuid,
	"decision_note" text,
	"decided_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "routing_rules" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"client_id" uuid NOT NULL,
	"name" text NOT NULL,
	"conditions" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"priority" integer DEFAULT 0 NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "sales_outcomes" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"lead_id" uuid NOT NULL,
	"client_id" uuid NOT NULL,
	"outcome" "sales_outcome" NOT NULL,
	"lost_reason" text,
	"contract_value" numeric(12, 2),
	"sold_at" timestamp with time zone,
	"margin" numeric(12, 2),
	"product" text,
	"reported_by" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "settings" (
	"key" text PRIMARY KEY NOT NULL,
	"value" jsonb NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "territories" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"client_id" uuid NOT NULL,
	"level" "territory_level" NOT NULL,
	"value" text NOT NULL,
	"region" text,
	"province" text,
	"exclusive" boolean DEFAULT false NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" text NOT NULL,
	"password_hash" text NOT NULL,
	"full_name" text NOT NULL,
	"role" "role" NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"last_login_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "webhook_events" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"provider" text NOT NULL,
	"external_event_id" text NOT NULL,
	"event_type" text NOT NULL,
	"payload" jsonb NOT NULL,
	"status" "webhook_event_status" DEFAULT 'RECEIVED' NOT NULL,
	"error" text,
	"lead_id" uuid,
	"received_at" timestamp with time zone DEFAULT now() NOT NULL,
	"processed_at" timestamp with time zone
);
--> statement-breakpoint
ALTER TABLE "appointments" ADD CONSTRAINT "appointments_lead_id_leads_id_fk" FOREIGN KEY ("lead_id") REFERENCES "public"."leads"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "appointments" ADD CONSTRAINT "appointments_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "appointments" ADD CONSTRAINT "appointments_package_id_packages_id_fk" FOREIGN KEY ("package_id") REFERENCES "public"."packages"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "appointments" ADD CONSTRAINT "appointments_operator_user_id_users_id_fk" FOREIGN KEY ("operator_user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "client_users" ADD CONSTRAINT "client_users_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "client_users" ADD CONSTRAINT "client_users_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "clients" ADD CONSTRAINT "clients_account_manager_user_id_users_id_fk" FOREIGN KEY ("account_manager_user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "ghl_mappings" ADD CONSTRAINT "ghl_mappings_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "integrations" ADD CONSTRAINT "integrations_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_answers" ADD CONSTRAINT "lead_answers_lead_id_leads_id_fk" FOREIGN KEY ("lead_id") REFERENCES "public"."leads"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_answers" ADD CONSTRAINT "lead_answers_answered_by_users_id_fk" FOREIGN KEY ("answered_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_assignments" ADD CONSTRAINT "lead_assignments_lead_id_leads_id_fk" FOREIGN KEY ("lead_id") REFERENCES "public"."leads"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_assignments" ADD CONSTRAINT "lead_assignments_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_assignments" ADD CONSTRAINT "lead_assignments_package_id_packages_id_fk" FOREIGN KEY ("package_id") REFERENCES "public"."packages"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_assignments" ADD CONSTRAINT "lead_assignments_matched_territory_id_territories_id_fk" FOREIGN KEY ("matched_territory_id") REFERENCES "public"."territories"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_assignments" ADD CONSTRAINT "lead_assignments_assigned_by_users_id_fk" FOREIGN KEY ("assigned_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_notes" ADD CONSTRAINT "lead_notes_lead_id_leads_id_fk" FOREIGN KEY ("lead_id") REFERENCES "public"."leads"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_notes" ADD CONSTRAINT "lead_notes_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_status_history" ADD CONSTRAINT "lead_status_history_lead_id_leads_id_fk" FOREIGN KEY ("lead_id") REFERENCES "public"."leads"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "lead_status_history" ADD CONSTRAINT "lead_status_history_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "leads" ADD CONSTRAINT "leads_source_id_lead_sources_id_fk" FOREIGN KEY ("source_id") REFERENCES "public"."lead_sources"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "leads" ADD CONSTRAINT "leads_campaign_id_campaigns_id_fk" FOREIGN KEY ("campaign_id") REFERENCES "public"."campaigns"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "leads" ADD CONSTRAINT "leads_qualified_by_users_id_fk" FOREIGN KEY ("qualified_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "leads" ADD CONSTRAINT "leads_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "leads" ADD CONSTRAINT "leads_package_id_packages_id_fk" FOREIGN KEY ("package_id") REFERENCES "public"."packages"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "leads" ADD CONSTRAINT "leads_owner_user_id_users_id_fk" FOREIGN KEY ("owner_user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "marketing_costs" ADD CONSTRAINT "marketing_costs_campaign_id_campaigns_id_fk" FOREIGN KEY ("campaign_id") REFERENCES "public"."campaigns"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "notifications" ADD CONSTRAINT "notifications_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "notifications" ADD CONSTRAINT "notifications_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "outbound_events" ADD CONSTRAINT "outbound_events_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "package_transactions" ADD CONSTRAINT "package_transactions_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "package_transactions" ADD CONSTRAINT "package_transactions_package_id_packages_id_fk" FOREIGN KEY ("package_id") REFERENCES "public"."packages"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "package_transactions" ADD CONSTRAINT "package_transactions_created_by_users_id_fk" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "packages" ADD CONSTRAINT "packages_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "qualification_rules" ADD CONSTRAINT "qualification_rules_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "replacement_requests" ADD CONSTRAINT "replacement_requests_lead_id_leads_id_fk" FOREIGN KEY ("lead_id") REFERENCES "public"."leads"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "replacement_requests" ADD CONSTRAINT "replacement_requests_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "replacement_requests" ADD CONSTRAINT "replacement_requests_package_id_packages_id_fk" FOREIGN KEY ("package_id") REFERENCES "public"."packages"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "replacement_requests" ADD CONSTRAINT "replacement_requests_requested_by_users_id_fk" FOREIGN KEY ("requested_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "replacement_requests" ADD CONSTRAINT "replacement_requests_decided_by_users_id_fk" FOREIGN KEY ("decided_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "routing_rules" ADD CONSTRAINT "routing_rules_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "sales_outcomes" ADD CONSTRAINT "sales_outcomes_lead_id_leads_id_fk" FOREIGN KEY ("lead_id") REFERENCES "public"."leads"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "sales_outcomes" ADD CONSTRAINT "sales_outcomes_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "sales_outcomes" ADD CONSTRAINT "sales_outcomes_reported_by_users_id_fk" FOREIGN KEY ("reported_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "territories" ADD CONSTRAINT "territories_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "appointments_lead_idx" ON "appointments" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "appointments_client_idx" ON "appointments" USING btree ("client_id");--> statement-breakpoint
CREATE UNIQUE INDEX "appointments_external_idx" ON "appointments" USING btree ("calendar_provider","external_id");--> statement-breakpoint
CREATE INDEX "audit_entity_idx" ON "audit_logs" USING btree ("entity_type","entity_id");--> statement-breakpoint
CREATE INDEX "audit_lead_idx" ON "audit_logs" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "audit_created_idx" ON "audit_logs" USING btree ("created_at");--> statement-breakpoint
CREATE UNIQUE INDEX "client_users_unique" ON "client_users" USING btree ("client_id","user_id");--> statement-breakpoint
CREATE INDEX "ghl_mappings_client_idx" ON "ghl_mappings" USING btree ("client_id");--> statement-breakpoint
CREATE INDEX "jobs_status_run_idx" ON "jobs" USING btree ("status","run_at");--> statement-breakpoint
CREATE UNIQUE INDEX "jobs_dedupe_idx" ON "jobs" USING btree ("dedupe_key");--> statement-breakpoint
CREATE UNIQUE INDEX "lead_answers_unique" ON "lead_answers" USING btree ("lead_id","question_key");--> statement-breakpoint
CREATE INDEX "lead_assignments_lead_idx" ON "lead_assignments" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "lead_assignments_client_idx" ON "lead_assignments" USING btree ("client_id");--> statement-breakpoint
CREATE INDEX "lead_notes_lead_idx" ON "lead_notes" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "lead_status_history_lead_idx" ON "lead_status_history" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "leads_status_idx" ON "leads" USING btree ("status");--> statement-breakpoint
CREATE INDEX "leads_client_idx" ON "leads" USING btree ("client_id");--> statement-breakpoint
CREATE INDEX "leads_phone_idx" ON "leads" USING btree ("phone_normalized");--> statement-breakpoint
CREATE INDEX "leads_email_idx" ON "leads" USING btree ("email_normalized");--> statement-breakpoint
CREATE INDEX "leads_province_idx" ON "leads" USING btree ("province");--> statement-breakpoint
CREATE INDEX "leads_created_idx" ON "leads" USING btree ("created_at");--> statement-breakpoint
CREATE INDEX "notifications_user_idx" ON "notifications" USING btree ("user_id","read_at");--> statement-breakpoint
CREATE INDEX "outbound_events_created_idx" ON "outbound_events" USING btree ("created_at");--> statement-breakpoint
CREATE INDEX "pkg_tx_package_idx" ON "package_transactions" USING btree ("package_id");--> statement-breakpoint
CREATE INDEX "pkg_tx_lead_idx" ON "package_transactions" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "packages_client_idx" ON "packages" USING btree ("client_id");--> statement-breakpoint
CREATE INDEX "replacement_lead_idx" ON "replacement_requests" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "replacement_client_idx" ON "replacement_requests" USING btree ("client_id");--> statement-breakpoint
CREATE INDEX "sales_outcomes_lead_idx" ON "sales_outcomes" USING btree ("lead_id");--> statement-breakpoint
CREATE INDEX "territories_client_idx" ON "territories" USING btree ("client_id");--> statement-breakpoint
CREATE INDEX "territories_value_idx" ON "territories" USING btree ("level","value");--> statement-breakpoint
CREATE UNIQUE INDEX "users_email_idx" ON "users" USING btree ("email");--> statement-breakpoint
CREATE UNIQUE INDEX "webhook_events_unique" ON "webhook_events" USING btree ("provider","external_event_id");