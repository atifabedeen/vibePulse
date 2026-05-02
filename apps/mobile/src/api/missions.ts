import { apiClient } from './client';
import type {
  InviteCreate,
  InviteOut,
  MissionCreate,
  MissionDetailOut,
  MissionListOut,
  MissionOut,
  MissionUpdate,
  RedeemIn,
  ReplanIn,
  ReplanOut,
} from './types';

export const missionsApi = {
  async list(params?: {
    status?: string;
    limit?: number;
    cursor?: string;
  }): Promise<MissionListOut> {
    const { data } = await apiClient.get<MissionListOut>('/missions', {
      params,
    });
    return data;
  },
  async create(body: MissionCreate): Promise<MissionOut> {
    const { data } = await apiClient.post<MissionOut>('/missions', body);
    return data;
  },
  async get(missionId: string): Promise<MissionDetailOut> {
    const { data } = await apiClient.get<MissionDetailOut>(
      `/missions/${missionId}`,
    );
    return data;
  },
  async patch(missionId: string, body: MissionUpdate): Promise<MissionOut> {
    const { data } = await apiClient.patch<MissionOut>(
      `/missions/${missionId}`,
      body,
    );
    return data;
  },
  async remove(missionId: string): Promise<void> {
    await apiClient.delete(`/missions/${missionId}`);
  },
  async createInvite(
    missionId: string,
    body: InviteCreate = {},
  ): Promise<InviteOut> {
    const { data } = await apiClient.post<InviteOut>(
      `/missions/${missionId}/invites`,
      body,
    );
    return data;
  },
  async redeemInvite(body: RedeemIn): Promise<MissionOut> {
    const { data } = await apiClient.post<MissionOut>(
      '/missions/invites/redeem',
      body,
    );
    return data;
  },
  async replan(missionId: string, body: ReplanIn = {}): Promise<ReplanOut> {
    const { data } = await apiClient.post<ReplanOut>(
      `/missions/${missionId}/replan`,
      body,
    );
    return data;
  },
};
