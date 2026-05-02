import { apiClient } from './client';
import type {
  AccessTokenOut,
  LoginIn,
  MeOut,
  RegisterIn,
  TokenPair,
  UserOut,
  UserUpdate,
} from './types';

export const authApi = {
  async register(body: RegisterIn): Promise<TokenPair> {
    const { data } = await apiClient.post<TokenPair>('/auth/register', body);
    return data;
  },
  async login(body: LoginIn): Promise<TokenPair> {
    const { data } = await apiClient.post<TokenPair>('/auth/login', body);
    return data;
  },
  async refresh(refreshToken: string): Promise<AccessTokenOut> {
    const { data } = await apiClient.post<AccessTokenOut>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return data;
  },
  async logout(): Promise<void> {
    await apiClient.post('/auth/logout');
  },
  async me(): Promise<MeOut> {
    const { data } = await apiClient.get<MeOut>('/auth/me');
    return data;
  },
  async patchMe(body: UserUpdate): Promise<UserOut> {
    const { data } = await apiClient.patch<UserOut>('/users/me', body);
    return data;
  },
  async deleteMe(): Promise<void> {
    await apiClient.delete('/users/me');
  },
};
