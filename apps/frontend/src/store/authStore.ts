import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  name: string;
  email: string;
  operatorId: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User, token: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      token: null,

      login: async (email: string) => {
        // TODO: Implement Cognito OIDC login with PKCE
        // For now, using mock authentication (password will be used in real implementation)
        const mockUser: User = {
          id: 1234567890,
          name: 'Carlos Andres Caro',
          email,
          operatorId: process.env.NEXT_PUBLIC_OPERATOR_ID || '',
        };

        const mockToken = 'mock-jwt-token';

        set({
          isAuthenticated: true,
          user: mockUser,
          token: mockToken,
        });
      },

      logout: () => {
        set({
          isAuthenticated: false,
          user: null,
          token: null,
        });
      },

      setUser: (user: User, token: string) => {
        set({
          isAuthenticated: true,
          user,
          token,
        });
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);

