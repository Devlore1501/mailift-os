"use client";

import { AppointmentsList } from "@/components/AppointmentsList";

export default function AdminAppointments() {
  return <AppointmentsList path="/appointments" leadBase="/admin/leads" statusPath={(id) => `/appointments/${id}/status`} allowed={["CONFIRMED", "CANCELLED", "RESCHEDULED", "SHOW", "NO_SHOW", "COMPLETED"]} />;
}
