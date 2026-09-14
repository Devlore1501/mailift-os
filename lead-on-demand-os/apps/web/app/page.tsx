"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { homeFor, useAuth } from "@/lib/auth";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (loading) return;
    router.replace(user ? homeFor(user.role) : "/login");
  }, [user, loading, router]);
  return <div className="p-8 text-sm text-slate-500">Caricamento…</div>;
}
