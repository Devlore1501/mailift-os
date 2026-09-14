import { NextResponse, type NextRequest } from "next/server";

// Protezione leggera lato edge: senza cookie di sessione si torna al login.
// La sicurezza reale sta nell'API (token JWT + RBAC): qui evitiamo solo pagine vuote.
export function middleware(req: NextRequest) {
  const hasAuth = req.cookies.get("lod_auth")?.value === "1";
  const { pathname } = req.nextUrl;
  if (!hasAuth && (pathname.startsWith("/admin") || pathname.startsWith("/operator") || pathname.startsWith("/portal"))) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/admin/:path*", "/operator/:path*", "/portal/:path*"] };
