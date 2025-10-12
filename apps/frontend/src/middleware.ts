/**
 * Next.js Middleware for Route Protection
 * Protects authenticated routes using NextAuth
 * 
 * @see https://next-auth.js.org/configuration/nextjs#middleware
 */

import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default withAuth(
  function middleware(req) {
    const token = req.nextauth.token;
    const path = req.nextUrl.pathname;

    // Admin routes - require 'admin' role
    if (path.startsWith("/admin")) {
      if (!token?.roles?.includes("admin")) {
        return NextResponse.redirect(new URL("/unauthorized", req.url));
      }
    }

    // Operator routes - require 'operator' or 'admin' role
    if (path.startsWith("/operator")) {
      const hasOperatorRole = 
        token?.roles?.includes("operator") || 
        token?.roles?.includes("admin");
      
      if (!hasOperatorRole) {
        return NextResponse.redirect(new URL("/unauthorized", req.url));
      }
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token }) => !!token,
    },
    pages: {
      signIn: "/login",
      error: "/auth/error",
    },
  }
);

// Protected routes configuration
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - /api/auth/* (NextAuth API routes)
     * - /_next/* (Next.js internals)
     * - /static/* (static files)
     * - /favicon.ico, /robots.txt (public files)
     * - / (public home)
     * - /login (login page)
     * - /auth/* (auth pages)
     */
    "/((?!api/auth|_next|static|favicon.ico|robots.txt|login|auth|$).*)",
  ],
};

