import { create } from 'zustand';

interface MissionState {
  currentMissionId: string | null;
  setCurrentMissionId: (id: string | null) => void;
}

export const useMissionStore = create<MissionState>((set) => ({
  currentMissionId: null,
  setCurrentMissionId: (id) => set({ currentMissionId: id }),
}));
