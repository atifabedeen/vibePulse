import { useEffect } from 'react';

import { useMissionStore } from '@/state/missionStore';

export function useMission(missionId: string | undefined | null) {
  const setCurrent = useMissionStore((s) => s.setCurrentMissionId);
  const current = useMissionStore((s) => s.currentMissionId);

  useEffect(() => {
    if (missionId && missionId !== current) {
      setCurrent(missionId);
    }
  }, [missionId, current, setCurrent]);

  return { missionId: missionId ?? current ?? null };
}
