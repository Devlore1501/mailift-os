import { sql } from "drizzle-orm";
import type { Ctx } from "../lib/context.js";

export interface DashboardFilter {
  from?: Date;
  to?: Date;
  clientId?: string;
  province?: string;
  region?: string;
  campaignId?: string;
  sourceId?: string;
  ownerUserId?: string;
  leadType?: string;
}

function leadWhere(f: DashboardFilter) {
  const parts = [sql`1=1`];
  if (f.clientId) parts.push(sql`l.client_id = ${f.clientId}`);
  if (f.province) parts.push(sql`l.province = ${f.province.toUpperCase()}`);
  if (f.region) parts.push(sql`l.region = ${f.region.toUpperCase()}`);
  if (f.campaignId) parts.push(sql`l.campaign_id = ${f.campaignId}`);
  if (f.sourceId) parts.push(sql`l.source_id = ${f.sourceId}`);
  if (f.ownerUserId) parts.push(sql`l.owner_user_id = ${f.ownerUserId}`);
  if (f.leadType) parts.push(sql`l.lead_type = ${f.leadType}`);
  return sql.join(parts, sql` and `);
}

function rows<T>(r: unknown): T[] {
  const x = r as { rows?: T[] };
  return (x.rows ?? (r as T[])) as T[];
}

// KPI della Home Admin (PRD sez. 4). Un'unica query aggregata sui lead più alcune di contorno.
export async function adminDashboard(ctx: Ctx, f: DashboardFilter) {
  const now = ctx.now();
  const from = f.from ?? new Date(now.getFullYear(), now.getMonth(), 1);
  const to = f.to ?? now;
  const todayStart = new Date(now);
  todayStart.setHours(0, 0, 0, 0);
  const w = leadWhere(f);
  const leadStats = rows<Record<string, number>>(
    await ctx.db.execute(sql`
      select
        count(*) filter (where l.created_at >= ${todayStart})::int as leads_today,
        count(*) filter (where l.created_at >= ${from} and l.created_at <= ${to})::int as leads_period,
        count(*) filter (where l.status in ('TO_CONTACT','ATTEMPT_1','ATTEMPT_2','ATTEMPT_3','CALLBACK'))::int as to_contact,
        count(*) filter (where l.qualification_passed = true and l.qualified_at >= ${from} and l.qualified_at <= ${to})::int as qualified,
        count(*) filter (where l.qualification_passed = false and l.qualified_at >= ${from} and l.qualified_at <= ${to})::int as not_qualified,
        count(*) filter (where l.credit_charged = true and l.delivered_at >= ${from} and l.delivered_at <= ${to})::int as delivered,
        count(*) filter (where l.status = 'WAITING_ASSIGNMENT')::int as waiting_assignment,
        count(*) filter (where l.status = 'QUALIFYING')::int as in_review,
        count(*) filter (where l.status = 'DELIVERY_FAILED')::int as delivery_failed,
        count(*) filter (where l.dedupe_result = 'DUPLICATE' and l.created_at >= ${from} and l.created_at <= ${to})::int as duplicates,
        coalesce(sum(l.attributed_cost) filter (where l.created_at >= ${from} and l.created_at <= ${to}), 0)::float as acquisition_cost
      from leads l where ${w}
    `),
  )[0]!;
  const replStats = rows<Record<string, number>>(
    await ctx.db.execute(sql`
      select
        count(*) filter (where r.status = 'REQUESTED')::int as requested_open,
        count(*) filter (where r.created_at >= ${from} and r.created_at <= ${to})::int as requested_period,
        count(*) filter (where r.status = 'APPROVED' and r.decided_at >= ${from} and r.decided_at <= ${to})::int as approved
      from replacement_requests r ${f.clientId ? sql`where r.client_id = ${f.clientId}` : sql``}
    `),
  )[0]!;
  const apptStats = rows<Record<string, number>>(
    await ctx.db.execute(sql`
      select
        count(*) filter (where a.created_at >= ${from} and a.created_at <= ${to})::int as booked,
        count(*) filter (where a.status = 'SHOW' and a.updated_at >= ${from} and a.updated_at <= ${to})::int as show,
        count(*) filter (where a.status = 'NO_SHOW' and a.updated_at >= ${from} and a.updated_at <= ${to})::int as no_show
      from appointments a ${f.clientId ? sql`where a.client_id = ${f.clientId}` : sql``}
    `),
  )[0]!;
  const pkgStats = rows<Record<string, number>>(
    await ctx.db.execute(sql`
      select
        (select count(*) from clients c where c.status = 'ACTIVE' ${f.clientId ? sql`and c.id = ${f.clientId}` : sql``})::int as active_clients,
        count(*) filter (where p.status in ('ACTIVE','LOW_BALANCE'))::int as active_packages,
        coalesce(sum((select sum(q.quantity) from package_transactions q where q.package_id = p.id)) filter (where p.status in ('ACTIVE','LOW_BALANCE')), 0)::int as remaining_to_deliver,
        coalesce(sum(p.total_price) filter (where p.paid = true and p.paid_at >= ${from} and p.paid_at <= ${to}), 0)::float as revenue_sold,
        coalesce((select sum(p2.unit_price) from package_transactions q2 join packages p2 on p2.id = q2.package_id where q2.type = 'DELIVERY' and q2.created_at >= ${from} and q2.created_at <= ${to} ${f.clientId ? sql`and p2.client_id = ${f.clientId}` : sql``}), 0)::float
          - coalesce((select sum(p3.unit_price) from package_transactions q3 join packages p3 on p3.id = q3.package_id where q3.type = 'REPLACEMENT' and q3.created_at >= ${from} and q3.created_at <= ${to} ${f.clientId ? sql`and p3.client_id = ${f.clientId}` : sql``}), 0)::float as revenue_recognized
      from packages p ${f.clientId ? sql`where p.client_id = ${f.clientId}` : sql``}
    `),
  )[0]!;
  const delivered = Number(leadStats.delivered ?? 0);
  const revenueRecognized = Number(pkgStats.revenue_recognized ?? 0);
  const acquisitionCost = Number(leadStats.acquisition_cost ?? 0);
  const grossMargin = revenueRecognized - acquisitionCost;
  return {
    period: { from, to },
    leads: {
      today: Number(leadStats.leads_today),
      period: Number(leadStats.leads_period),
      toContact: Number(leadStats.to_contact),
      qualified: Number(leadStats.qualified),
      notQualified: Number(leadStats.not_qualified),
      delivered,
      inReview: Number(leadStats.in_review),
      waitingAssignment: Number(leadStats.waiting_assignment),
      deliveryFailed: Number(leadStats.delivery_failed),
      duplicates: Number(leadStats.duplicates),
    },
    replacements: { open: Number(replStats.requested_open), requested: Number(replStats.requested_period), approved: Number(replStats.approved) },
    appointments: { booked: Number(apptStats.booked), show: Number(apptStats.show), noShow: Number(apptStats.no_show) },
    clients: { active: Number(pkgStats.active_clients), activePackages: Number(pkgStats.active_packages), remainingToDeliver: Number(pkgStats.remaining_to_deliver) },
    economics: {
      revenueSold: Number(pkgStats.revenue_sold),
      revenueRecognized,
      acquisitionCost,
      grossMargin,
      marginPerLead: delivered ? grossMargin / delivered : 0,
    },
  };
}

// Analytics per cliente (PRD sez. 27-28): funnel e valore generato.
export async function clientAnalytics(ctx: Ctx, clientId: string, f: { from?: Date; to?: Date } = {}) {
  const now = ctx.now();
  const from = f.from ?? new Date(now.getFullYear(), now.getMonth() - 5, 1);
  const to = f.to ?? now;
  const funnel = rows<Record<string, number>>(
    await ctx.db.execute(sql`
      select
        count(*) filter (where l.credit_charged = true)::int as received,
        count(*) filter (where l.replaced = true)::int as replaced,
        count(distinct o.lead_id) filter (where o.outcome in ('CONTACTED','APPOINTMENT','SITE_VISIT_DONE','QUOTE_SENT','WON','LOST'))::int as contacted,
        (select count(*) from appointments a where a.client_id = ${clientId} and a.lead_id = any(array(select id from leads where client_id = ${clientId} and delivered_at >= ${from} and delivered_at <= ${to})))::int as appointments,
        (select count(*) from appointments a where a.client_id = ${clientId} and a.status = 'SHOW' and a.lead_id = any(array(select id from leads where client_id = ${clientId} and delivered_at >= ${from} and delivered_at <= ${to})))::int as show,
        count(distinct o.lead_id) filter (where o.outcome in ('QUOTE_SENT','WON'))::int as quotes,
        count(distinct o.lead_id) filter (where o.outcome = 'WON')::int as won,
        coalesce(sum(o.contract_value) filter (where o.outcome = 'WON'), 0)::float as sales_value,
        count(*) filter (where l.credit_charged = true and l.status not in ('CLOSED_WON','CLOSED_LOST') and not exists (select 1 from sales_outcomes so where so.lead_id = l.id))::int as missing_outcome
      from leads l
      left join sales_outcomes o on o.lead_id = l.id
      where l.client_id = ${clientId} and l.delivered_at >= ${from} and l.delivered_at <= ${to}
    `),
  )[0]!;
  const cost = rows<Record<string, number>>(
    await ctx.db.execute(sql`
      select coalesce(sum(p.unit_price), 0)::float as lead_cost
      from package_transactions q join packages p on p.id = q.package_id
      where p.client_id = ${clientId} and q.type = 'DELIVERY' and q.created_at >= ${from} and q.created_at <= ${to}
    `),
  )[0]!;
  const received = Number(funnel.received);
  const won = Number(funnel.won);
  const leadCost = Number(cost.lead_cost);
  const salesValue = Number(funnel.sales_value);
  return {
    period: { from, to },
    received,
    replaced: Number(funnel.replaced),
    contacted: Number(funnel.contacted),
    appointments: Number(funnel.appointments),
    show: Number(funnel.show),
    quotes: Number(funnel.quotes),
    won,
    salesValue,
    leadCost,
    costPerCustomer: won ? leadCost / won : null,
    revenueOverCost: leadCost ? salesValue / leadCost : null,
    missingOutcome: Number(funnel.missing_outcome),
  };
}

// Economics per campagna (PRD sez. 30).
export async function campaignEconomics(ctx: Ctx, f: { from?: Date; to?: Date } = {}) {
  const now = ctx.now();
  const from = f.from ?? new Date(now.getFullYear(), now.getMonth(), 1);
  const to = f.to ?? now;
  return rows<Record<string, unknown>>(
    await ctx.db.execute(sql`
      select c.id, c.name, c.platform,
        coalesce((select sum(m.amount) from marketing_costs m where m.campaign_id = c.id and m.period_start <= ${to} and m.period_end >= ${from}), 0)::float as spend,
        count(l.id)::int as leads_raw,
        count(l.id) filter (where l.qualification_passed = true)::int as leads_qualified,
        count(l.id) filter (where l.credit_charged = true)::int as leads_sold,
        count(l.id) filter (where l.replaced = true)::int as replacements,
        coalesce(sum(p.unit_price) filter (where l.credit_charged = true and l.replaced = false), 0)::float as revenue
      from campaigns c
      left join leads l on l.campaign_id = c.id and l.created_at >= ${from} and l.created_at <= ${to}
      left join packages p on p.id = l.package_id
      group by c.id, c.name, c.platform
      order by revenue desc
    `),
  ).map((r) => {
    const spend = Number(r.spend);
    const raw = Number(r.leads_raw);
    const qualified = Number(r.leads_qualified);
    const revenue = Number(r.revenue);
    return { ...r, spend, leadsRaw: raw, leadsQualified: qualified, leadsSold: Number(r.leads_sold), replacements: Number(r.replacements), revenue, cplRaw: raw ? spend / raw : null, cplQualified: qualified ? spend / qualified : null, grossProfit: revenue - spend };
  });
}
