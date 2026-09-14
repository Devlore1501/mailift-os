"use client";

import { AppointmentsList } from "@/components/AppointmentsList";

export default function OperatorAppointments() {
  return <AppointmentsList path="/appointments" leadBase="/operator" statusPath={(id) => `/appointments/${id}/status`} allowed={["CONFIRMED", "CANCELLED", "RESCHEDULED", "SHOW", "NO_SHOW", "COMPLETED"]} />;
}
