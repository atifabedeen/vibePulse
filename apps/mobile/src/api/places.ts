import { apiClient } from './client';
import type { PlaceDetail, PlaceOut, PlaceRefreshOut } from './types';

export const placesApi = {
  async list(missionId: string): Promise<PlaceOut[]> {
    // Router mounts at `/missions/{id}/places/` with trailing slash on GET.
    const { data } = await apiClient.get<PlaceOut[]>(
      `/missions/${missionId}/places/`,
    );
    return data;
  },
  async get(missionId: string, placeId: string): Promise<PlaceDetail> {
    const { data } = await apiClient.get<PlaceDetail>(
      `/missions/${missionId}/places/${placeId}`,
    );
    return data;
  },
  async refresh(missionId: string): Promise<PlaceRefreshOut> {
    const { data } = await apiClient.post<PlaceRefreshOut>(
      `/missions/${missionId}/places/refresh`,
    );
    return data;
  },
};
