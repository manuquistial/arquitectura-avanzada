/**
 * NextAuth API Route Handler
 * Azure AD B2C Provider Configuration
 * 
 * @see https://next-auth.js.org/configuration/providers/azure-ad-b2c
 */

import NextAuth, { NextAuthOptions } from "next-auth";
import AzureADB2CProvider from "next-auth/providers/azure-ad-b2c";

const tenantName = process.env.AZURE_AD_B2C_TENANT_NAME || "carpetaciudadana";
const tenantId = process.env.AZURE_AD_B2C_TENANT_ID || "";
const userFlow = process.env.AZURE_AD_B2C_PRIMARY_USER_FLOW || "B2C_1_signupsignin1";
const clientId = process.env.AZURE_AD_B2C_CLIENT_ID || "";
const clientSecret = process.env.AZURE_AD_B2C_CLIENT_SECRET || "";

export const authOptions: NextAuthOptions = {
  providers: [
    AzureADB2CProvider({
      tenantId,
      clientId,
      clientSecret,
      primaryUserFlow: userFlow,
      authorization: {
        params: {
          scope: "openid profile email offline_access",
        },
      },
    }),
  ],
  
  callbacks: {
    /**
     * JWT Callback - Called when JWT is created or updated
     * Store user info from Azure AD B2C in the token
     */
    async jwt({ token, account, profile }) {
      // Initial sign in
      if (account && profile) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
        token.refreshToken = account.refresh_token;
        
        // Azure AD B2C specific claims
        token.sub = profile.sub; // User ID from B2C
        token.email = profile.email;
        token.name = profile.name;
        token.given_name = (profile as any).given_name;
        token.family_name = (profile as any).family_name;
        
        // Custom claims (if configured in B2C)
        token.roles = (profile as any).extension_Role || [];
        token.permissions = (profile as any).extension_Permissions || [];
      }
      
      return token;
    },

    /**
     * Session Callback - Send properties to client
     * Include user info in the session object
     */
    async session({ session, token }) {
      // Attach token data to session
      session.user = {
        id: token.sub as string,
        email: token.email as string,
        name: token.name as string,
        given_name: token.given_name as string,
        family_name: token.family_name as string,
        roles: token.roles as string[],
        permissions: token.permissions as string[],
      };
      
      // Include access token for API calls
      session.accessToken = token.accessToken as string;
      session.idToken = token.idToken as string;
      
      return session;
    },

    /**
     * Redirect Callback - Control where to redirect after sign in/out
     */
    async redirect({ url, baseUrl }) {
      // Allows relative callback URLs
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      
      // Allows callback URLs on the same origin
      else if (new URL(url).origin === baseUrl) return url;
      
      return baseUrl;
    },
  },

  pages: {
    signIn: "/login", // Custom sign in page
    signOut: "/", // Redirect after sign out
    error: "/auth/error", // Error page
  },

  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60, // 24 hours
  },

  secret: process.env.NEXTAUTH_SECRET,

  debug: process.env.NODE_ENV === "development",
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };

