import { apiClient } from './client';
import type { RankingBatch } from './types';

export const rankingsApi = {
  async latest(missionId: string): Promise<RankingBatch> {
    const { data } = await apiClient.get<RankingBatch>(
      `/missions/${missionId}/rankings/latest`,
    );
    return data;
  },
  async forRun(missionId: string, runId: string): Promise<RankingBatch> {
    const { data } = await apiClient.get<RankingBatch>(
      `/missions/${missionId}/rankings/runs/${runId}`,
    );
    return data;
  },
};
