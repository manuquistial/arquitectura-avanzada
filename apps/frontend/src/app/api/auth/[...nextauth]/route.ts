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
        console.log('🔐 NextAuth authorize called with:', { email: credentials?.email });
        
        if (!credentials?.email || !credentials?.password) {
          console.log('❌ Missing credentials');
          return null;
        }

        try {
          // Llamar al servicio de autenticación backend
          const authServiceUrl = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL;
          console.log('🌐 Auth service URL:', authServiceUrl);
          
          if (!authServiceUrl) {
            console.warn('NEXT_PUBLIC_AUTH_SERVICE_URL not configured, using demo credentials');
            throw new Error('Auth service URL not configured');
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
          
          if (response.ok) {
            const user = await response.json();
            console.log('✅ Login successful, user data:', {
              id: user.id,
              email: user.email,
              name: user.name,
              roles: user.roles
            });
            
            return {
              id: user.id,
              email: user.email,
              name: user.name,
              given_name: user.given_name,
              family_name: user.family_name,
              roles: user.roles || ["user"],
              permissions: user.permissions || ["read"]
            };
          } else {
            console.log('❌ Login failed with status:', response.status);
            const errorText = await response.text();
            console.log('❌ Error response:', errorText);
          }
        } catch (error) {
          console.error('❌ Error authenticating user:', error);
          console.log('Falling back to demo credentials...');
        }

        // Fallback para credenciales de demo
        if (credentials.email === "admin@carpeta.com" && credentials.password === "admin123") {
          return {
            id: "1",
            email: "admin@carpeta.com",
            name: "Administrador",
            given_name: "Admin",
            family_name: "Carpeta",
            roles: ["admin"],
            permissions: ["all"]
          };
        }

        if (credentials.email === "demo@carpeta.com" && credentials.password === "demo123") {
          return {
            id: "2",
            email: "demo@carpeta.com", 
            name: "Usuario Demo",
            given_name: "Usuario",
            family_name: "Demo",
            roles: ["user"],
            permissions: ["read"]
          };
        }

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
        roles: token.roles
      });
      
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
      
      console.log('📋 Session created for user:', {
        id: session.user.id,
        email: session.user.email,
        name: session.user.name,
        roles: session.user.roles
      });
      
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

  debug: process.env.NODE_ENV === 'development', // Enable debug mode in development
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };

