export class AppError extends Error {
  constructor(
    public readonly statusCode: number,
    message: string,
    public readonly code: string = "APP_ERROR",
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "AppError";
  }
}

export const notFound = (what = "Risorsa") => new AppError(404, `${what} non trovata`, "NOT_FOUND");
export const forbidden = (msg = "Operazione non consentita") => new AppError(403, msg, "FORBIDDEN");
export const badRequest = (msg: string, details?: unknown) => new AppError(400, msg, "BAD_REQUEST", details);
export const conflict = (msg: string, details?: unknown) => new AppError(409, msg, "CONFLICT", details);
export const unauthorized = (msg = "Autenticazione richiesta") => new AppError(401, msg, "UNAUTHORIZED");
