import { apiClient } from './client';
import type {
  AgentRejectIn,
  AgentResumeOut,
  AgentRunDetail,
  AgentRunOut,
} from './types';

export const agentsApi = {
  async listRuns(missionId: string): Promise<AgentRunOut[]> {
    const { data } = await apiClient.get<AgentRunOut[]>(
      `/missions/${missionId}/agents/runs`,
    );
    return data;
  },
  async getRun(missionId: string, runId: string): Promise<AgentRunDetail> {
    const { data } = await apiClient.get<AgentRunDetail>(
      `/missions/${missionId}/agents/runs/${runId}`,
    );
    return data;
  },
  async approve(
    missionId: string,
    runId: string,
  ): Promise<AgentResumeOut> {
    const { data } = await apiClient.post<AgentResumeOut>(
      `/missions/${missionId}/agents/runs/${runId}/approve`,
    );
    return data;
  },
  async reject(
    missionId: string,
    runId: string,
    body: AgentRejectIn,
  ): Promise<AgentResumeOut> {
    const { data } = await apiClient.post<AgentResumeOut>(
      `/missions/${missionId}/agents/runs/${runId}/reject`,
      body,
    );
    return data;
  },
};
