import type { Role } from "@lod/core";
import type { Database } from "@lod/db";
import type { Config } from "../config.js";
import type { GhlClient } from "../services/ghlClient.js";

export interface AuthUser {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  clientId: string | null; // valorizzato solo per il ruolo CLIENT
}

export interface Ctx {
  db: Database;
  config: Config;
  ghl: GhlClient;
  user: AuthUser | null;
  ip?: string;
  now: () => Date;
}

export const SYSTEM_USER: AuthUser = {
  id: "00000000-0000-0000-0000-000000000000",
  email: "system@leadondemand.local",
  fullName: "Sistema",
  role: "SUPER_ADMIN",
  clientId: null,
};
