/**
 * NextAuth TypeScript Module Augmentation
 * Extend default types to include custom properties
 */

import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  /**
   * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` React Context
   */
  interface Session {
    user: {
      id: string;
      email: string;
      name: string;
      given_name: string;
      family_name: string;
      roles: string[];
      permissions: string[];
    };
    accessToken: string;
    idToken: string;
  }

  interface User {
    id: string;
    email: string;
    name: string;
    given_name: string;
    family_name: string;
    roles: string[];
    permissions: string[];
  }
}

declare module "next-auth/jwt" {
  /** Returned by the `jwt` callback and `getToken`, when using JWT sessions */
  interface JWT {
    accessToken?: string;
    idToken?: string;
    refreshToken?: string;
    sub: string;
    email: string;
    name: string;
    given_name: string;
    family_name: string;
    roles: string[];
    permissions: string[];
  }
}

