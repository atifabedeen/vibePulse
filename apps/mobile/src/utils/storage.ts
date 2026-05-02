import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  ACCESS: 'vp.accessToken',
  REFRESH: 'vp.refreshToken',
  USER: 'vp.user',
} as const;

export const storage = {
  async getAccess(): Promise<string | null> {
    return AsyncStorage.getItem(KEYS.ACCESS);
  },
  async getRefresh(): Promise<string | null> {
    return AsyncStorage.getItem(KEYS.REFRESH);
  },
  async setTokens(access: string, refresh: string): Promise<void> {
    await AsyncStorage.multiSet([
      [KEYS.ACCESS, access],
      [KEYS.REFRESH, refresh],
    ]);
  },
  async setAccess(access: string): Promise<void> {
    await AsyncStorage.setItem(KEYS.ACCESS, access);
  },
  async clearTokens(): Promise<void> {
    await AsyncStorage.multiRemove([KEYS.ACCESS, KEYS.REFRESH, KEYS.USER]);
  },
  async getUser<T = unknown>(): Promise<T | null> {
    const raw = await AsyncStorage.getItem(KEYS.USER);
    return raw ? (JSON.parse(raw) as T) : null;
  },
  async setUser(user: unknown): Promise<void> {
    await AsyncStorage.setItem(KEYS.USER, JSON.stringify(user));
  },
};

export const STORAGE_KEYS = KEYS;
