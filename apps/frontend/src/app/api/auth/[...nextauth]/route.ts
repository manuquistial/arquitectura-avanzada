/**
 * NextAuth API Route Handler
 * Authentication Configuration (Azure AD B2C removed)
 * 
 * @see https://next-auth.js.org/configuration/providers
 */

import NextAuth, { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const authOptions: NextAuthOptions = {
  providers: [
    // Azure AD B2C Provider - REMOVED
    
    // Traditional Login Provider
    CredentialsProvider({
      id: "credentials",
      name: "Credenciales",
      credentials: {
        email: { label: "Email", type: "email", placeholder: "tu@email.com" },
        password: { label: "Contraseña", type: "password" }
      },
      async authorize(credentials) {
        console.log('🔐 NextAuth authorize called with:', { 
          email: credentials?.email,
          hasPassword: !!credentials?.password 
        });
        
        if (!credentials?.email || !credentials?.password) {
          console.log('❌ Missing credentials');
          return null;
        }

        try {
          // Llamar al servicio de autenticación backend
          const authServiceUrl = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';
          console.log('🌐 Auth service URL:', authServiceUrl);
          
          if (!authServiceUrl) {
            console.warn('❌ NEXT_PUBLIC_AUTH_SERVICE_URL not configured, using default');
            return null;
          }
          
          const loginUrl = `${authServiceUrl}/api/auth/login`;
          console.log('📡 Calling login endpoint:', loginUrl);
          
          const response = await fetch(loginUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password
            })
          });

          console.log('📊 Login response status:', response.status);
          console.log('📊 Login response headers:', Object.fromEntries(response.headers.entries()));
          
          if (response.ok) {
            const user = await response.json();
            console.log('✅ Login successful, user data:', {
              id: user.id,
              email: user.email,
              name: user.name,
              roles: user.roles
            });
            
            const userObject = {
              id: user.id,
              email: user.email,
              name: user.name,
              given_name: user.given_name,
              family_name: user.family_name,
              roles: user.roles || ["user"],
              permissions: user.permissions || ["read"]
            };
            
            console.log('✅ Returning user object:', userObject);
            return userObject;
          } else {
            console.log('❌ Login failed with status:', response.status);
            const errorText = await response.text();
            console.log('❌ Error response:', errorText);
            return null;
          }
        } catch (error) {
          console.error('❌ Error authenticating user:', error);
          console.error('❌ Error details:', error.message, error.stack);
          return null;
        }

        console.log('❌ Login failed, returning null');
        return null;
      }
    })
  ],
  
  callbacks: {
    /**
     * JWT Callback - Called when JWT is created or updated
     * Store user info in the token
     */
    async jwt({ token, account, profile, user }) {
      console.log('🔑 JWT callback called with:', { 
        hasUser: !!user, 
        hasAccount: !!account, 
        hasProfile: !!profile,
        tokenSub: token.sub 
      });
      
      // Credentials provider (or any flow that supplies a user object)
      if (user) {
        console.log('👤 Processing user object:', {
          id: user.id,
          email: user.email,
          name: user.name,
          roles: user.roles
        });
        
        // Narrow unknown user shape safely
        const u = user as unknown as {
          id?: string;
          email?: string;
          name?: string;
          given_name?: string;
          family_name?: string;
          roles?: string[];
          permissions?: string[];
        };
        token.sub = u.id ?? (token.sub as string);
        token.email = u.email ?? (token.email as string);
        token.name = u.name ?? (token.name as string);
        token.given_name = u.given_name ?? (token.given_name as string);
        token.family_name = u.family_name ?? (token.family_name as string);
        token.roles = u.roles ?? ((token.roles as string[] | undefined) ?? []);
        token.permissions = u.permissions ?? ((token.permissions as string[] | undefined) ?? []);
        
        console.log('🔑 Token updated with:', {
          sub: token.sub,
          email: token.email,
          name: token.name,
          roles: token.roles
        });
        
        console.log('🔑 Full token object:', JSON.stringify(token, null, 2));
      }

      // OAuth providers (Azure AD B2C, etc.)
      if (account && profile) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
        token.refreshToken = account.refresh_token;
        
        // Profile specific claims
        token.sub = profile.sub;
        token.email = profile.email;
        token.name = profile.name;
        token.given_name = (profile as Record<string, unknown>).given_name as string;
        token.family_name = (profile as Record<string, unknown>).family_name as string;
        
        // Custom claims
        token.roles = (profile as Record<string, unknown>).extension_Role as string[] || [];
        token.permissions = (profile as Record<string, unknown>).extension_Permissions as string[] || [];
      }
      
      return token;
    },

    /**
     * Session Callback - Send properties to client
     * Include user info in the session object
     */
    async session({ session, token }) {
      console.log('📋 Session callback called with token:', {
        sub: token.sub,
        email: token.email,
        name: token.name,
        roles: token.roles,
        hasToken: !!token,
        tokenKeys: Object.keys(token)
      });
      
      console.log('📋 Session callback called with session:', {
        hasSession: !!session,
        hasUser: !!session?.user,
        sessionKeys: session ? Object.keys(session) : []
      });
      
      // Attach token data to session
      if (token && token.sub) {
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
        
        console.log('📋 Session created for user:', {
          id: session.user.id,
          email: session.user.email,
          name: session.user.name,
          roles: session.user.roles
        });
      } else {
        console.log('❌ No token or token.sub found, session will be empty');
      }
      
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

  secret: process.env.NEXTAUTH_SECRET || "fallback-secret-for-development",

  debug: true, // Always enable debug mode // Enable debug mode in development
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };

