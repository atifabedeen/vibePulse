import { create } from 'zustand';

import { authApi, setOnAuthFailure } from '@/api';
import type { LoginIn, RegisterIn, UserOut } from '@/api';
import { storage } from '@/utils/storage';

interface AuthState {
  hydrated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  user: UserOut | null;
  hydrate: () => Promise<void>;
  login: (input: LoginIn) => Promise<void>;
  register: (input: RegisterIn) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: UserOut | null) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  hydrated: false,
  accessToken: null,
  refreshToken: null,
  user: null,

  async hydrate() {
    const [access, refresh, user] = await Promise.all([
      storage.getAccess(),
      storage.getRefresh(),
      storage.getUser<UserOut>(),
    ]);
    set({
      accessToken: access,
      refreshToken: refresh,
      user,
      hydrated: true,
    });
  },

  async login(input) {
    const pair = await authApi.login(input);
    await storage.setTokens(pair.access_token, pair.refresh_token);
    await storage.setUser(pair.user);
    set({
      accessToken: pair.access_token,
      refreshToken: pair.refresh_token,
      user: pair.user,
    });
  },

  async register(input) {
    const pair = await authApi.register(input);
    await storage.setTokens(pair.access_token, pair.refresh_token);
    await storage.setUser(pair.user);
    set({
      accessToken: pair.access_token,
      refreshToken: pair.refresh_token,
      user: pair.user,
    });
  },

  async logout() {
    // Best-effort server logout; ignore failures (server is a stub anyway).
    try {
      if (get().accessToken) await authApi.logout();
    } catch {
      // ignore
    }
    await storage.clearTokens();
    set({ accessToken: null, refreshToken: null, user: null });
  },

  setUser(user) {
    set({ user });
    if (user) void storage.setUser(user);
  },
}));

// Wire the api client's auth-failure hook to the store. When the
// interceptor's refresh fails, it calls this -> we clear local state and
// the auth gate redirects to /login.
setOnAuthFailure(async () => {
  await storage.clearTokens();
  useAuthStore.setState({ accessToken: null, refreshToken: null, user: null });
});
