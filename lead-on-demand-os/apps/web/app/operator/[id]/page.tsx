"use client";

import { use } from "react";
import { CallScreen } from "@/components/CallScreen";

export default function OperatorCallPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <CallScreen id={id} backHref="/operator" />;
}
