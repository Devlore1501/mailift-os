"use client";

import { use } from "react";
import { LeadDetail } from "@/components/LeadDetail";

export default function AdminLeadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <LeadDetail id={id} callHref={`/operator/${id}`} />;
}
