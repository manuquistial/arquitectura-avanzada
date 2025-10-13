/**
 * Auth Store (Zustand) - Wrapper for NextAuth
 * Integrates NextAuth with Zustand for global state management
 * 
 * NOTE: This store is now a thin wrapper around NextAuth.
 * Use `useSession()` from next-auth/react for most auth operations.
 */

import { create } from 'zustand';

export interface User {
  id: string;
  name: string;
  email: string;
  given_name: string;
  family_name: string;
  roles: string[];
  permissions: string[];
}

interface AuthState {
  // UI state
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  
  // Backward compatibility (deprecated - use NextAuth hooks instead)
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
  
  // Helper methods
  hasRole: (role: string) => boolean;
  hasPermission: (permission: string) => boolean;
  
  // Cached user data (synced from NextAuth session)
  cachedUser: User | null;
  setCachedUser: (user: User | null) => void;
}

/**
 * Auth Store
 * 
 * Use this store for:
 * - UI loading states
 * - Role/permission checks
 * - Caching user data for offline access
 * 
 * For authentication operations, use NextAuth hooks:
 * - `useSession()` - Get session and user data
 * - `signIn()` - Trigger login
 * - `signOut()` - Trigger logout
 */
export const useAuthStore = create<AuthState>((set, get) => ({
  isLoading: false,
  cachedUser: null,
  
  // Backward compatibility
  isAuthenticated: false,
  user: null,
  token: null,

  setIsLoading: (loading: boolean) => set({ isLoading: loading }),

  setCachedUser: (user: User | null) => set({ cachedUser: user, user: user, isAuthenticated: !!user }),
  
  // Backward compatibility setters
  setUser: (user: User | null) => set({ user: user, cachedUser: user, isAuthenticated: !!user }),
  
  setToken: (token: string | null) => set({ token: token }),
  
  logout: () => {
    set({ user: null, cachedUser: null, token: null, isAuthenticated: false });
    // Also trigger NextAuth signOut
    if (typeof window !== 'undefined') {
      import('next-auth/react').then(({ signOut }) => signOut());
    }
  },

  hasRole: (role: string): boolean => {
    const { cachedUser } = get();
    return cachedUser?.roles?.includes(role) ?? false;
  },

  hasPermission: (permission: string): boolean => {
    const { cachedUser } = get();
    return cachedUser?.permissions?.includes(permission) ?? false;
  },
}));

