"use client";

import { AppointmentsList } from "@/components/AppointmentsList";

export default function PortalAppointments() {
  return <AppointmentsList path="/portal/appointments" leadBase="/portal/leads" statusPath={(id) => `/portal/appointments/${id}/status`} allowed={["CONFIRMED", "CANCELLED", "SHOW", "NO_SHOW", "COMPLETED"]} />;
}
