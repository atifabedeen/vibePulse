import { useEffect } from 'react';

import { useAuthStore } from '@/state/authStore';

/**
 * Hydrate auth from AsyncStorage exactly once per app boot, then expose a
 * normalised view of the auth store to callers.
 */
export function useAuth() {
  const state = useAuthStore();

  useEffect(() => {
    if (!state.hydrated) {
      void state.hydrate();
    }
  }, [state.hydrated, state.hydrate, state]);

  return {
    hydrated: state.hydrated,
    isAuthenticated: !!state.accessToken,
    accessToken: state.accessToken,
    user: state.user,
    login: state.login,
    register: state.register,
    logout: state.logout,
  };
}
