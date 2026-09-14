import { SignJWT, jwtVerify } from "jose";
import bcrypt from "bcryptjs";
import type { AuthUser } from "./context.js";

export async function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, 10);
}

export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}

export async function signToken(user: AuthUser, secret: string, ttlSeconds: number): Promise<string> {
  const key = new TextEncoder().encode(secret);
  return new SignJWT({ email: user.email, fullName: user.fullName, role: user.role, clientId: user.clientId })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(user.id)
    .setIssuedAt()
    .setExpirationTime(Math.floor(Date.now() / 1000) + ttlSeconds)
    .sign(key);
}

export async function verifyToken(token: string, secret: string): Promise<AuthUser | null> {
  try {
    const key = new TextEncoder().encode(secret);
    const { payload } = await jwtVerify(token, key);
    if (!payload.sub) return null;
    return {
      id: payload.sub,
      email: String(payload.email),
      fullName: String(payload.fullName),
      role: payload.role as AuthUser["role"],
      clientId: (payload.clientId as string | null) ?? null,
    };
  } catch {
    return null;
  }
}
