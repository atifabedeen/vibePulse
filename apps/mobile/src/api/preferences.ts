import { apiClient } from './client';
import type {
  PreferenceOut,
  PreferenceParseIn,
  PreferencePayload,
} from './types';

export const preferencesApi = {
  async list(missionId: string): Promise<PreferenceOut[]> {
    // The router mounts at `/missions/{id}/preferences/` (trailing slash on GET).
    const { data } = await apiClient.get<PreferenceOut[]>(
      `/missions/${missionId}/preferences/`,
    );
    return data;
  },
  async putMine(
    missionId: string,
    body: PreferencePayload,
  ): Promise<PreferenceOut> {
    const { data } = await apiClient.put<PreferenceOut>(
      `/missions/${missionId}/preferences/me`,
      body,
    );
    return data;
  },
  async parseMine(
    missionId: string,
    body: PreferenceParseIn,
  ): Promise<PreferenceOut> {
    const { data } = await apiClient.post<PreferenceOut>(
      `/missions/${missionId}/preferences/me/parse`,
      body,
    );
    return data;
  },
};
