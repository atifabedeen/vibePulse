import { apiClient } from './client';
import type { FinalizeOut, VoteOut, VotePayload, VoteTally } from './types';

export const votesApi = {
  async putMine(missionId: string, body: VotePayload): Promise<VoteOut[]> {
    const { data } = await apiClient.put<VoteOut[]>(
      `/missions/${missionId}/votes/me`,
      body,
    );
    return data;
  },
  async tally(missionId: string): Promise<VoteTally> {
    const { data } = await apiClient.get<VoteTally>(
      `/missions/${missionId}/votes/`,
    );
    return data;
  },
  async finalize(missionId: string): Promise<FinalizeOut> {
    const { data } = await apiClient.post<FinalizeOut>(
      `/missions/${missionId}/votes/finalize`,
    );
    return data;
  },
};
