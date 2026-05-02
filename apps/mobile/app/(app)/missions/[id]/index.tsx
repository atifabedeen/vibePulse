import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import * as Linking from 'expo-linking';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  Alert,
  RefreshControl,
  Share,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import {
  agentsApi,
  ApiError,
  missionsApi,
  placesApi,
} from '@/api';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ScreenContainer } from '@/components/ScreenContainer';
import { Spinner } from '@/components/Spinner';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';
import { formatRelative } from '@/utils/time';

export default function MissionOverviewScreen() {
  const params = useLocalSearchParams<{ id: string }>();
  const missionId = String(params.id ?? '');
  const router = useRouter();
  const queryClient = useQueryClient();

  const missionQ = useQuery({
    queryKey: ['mission', missionId],
    queryFn: () => missionsApi.get(missionId),
    enabled: !!missionId,
  });

  const [pollingRunId, setPollingRunId] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Poll the agent run after a Recommend! kick until status leaves 'running'.
  useEffect(() => {
    if (!pollingRunId) return;
    const tick = async () => {
      try {
        const detail = await agentsApi.getRun(missionId, pollingRunId);
        if (detail.status !== 'running' && detail.status !== 'pending') {
          setPollingRunId(null);
          await queryClient.invalidateQueries({
            queryKey: ['agent-runs', missionId],
          });
          if (detail.status === 'interrupted') {
            router.push(`/(app)/missions/${missionId}/runs`);
          } else if (detail.status === 'completed') {
            router.push(`/(app)/missions/${missionId}/rankings`);
          }
          return;
        }
      } catch {
        // swallow; try again on the next tick
      }
      pollTimer.current = setTimeout(tick, 2000);
    };
    pollTimer.current = setTimeout(tick, 2000);
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, [pollingRunId, missionId, queryClient, router]);

  const recommend = useMutation({
    mutationFn: () => placesApi.refresh(missionId),
    onSuccess: (resp) => {
      setPollingRunId(resp.agent_run_id);
    },
    onError: (err) => {
      const detail =
        err instanceof ApiError ? err.detail : 'Could not start a run.';
      Alert.alert('Recommend failed', detail);
    },
  });

  const inviteMutation = useMutation({
    mutationFn: () => missionsApi.createInvite(missionId, {}),
    onSuccess: async (invite) => {
      const url = Linking.createURL(`/invite/${invite.token}`);
      try {
        await Share.share({
          message: `Join my VibePulse mission: ${url}`,
          url,
        });
      } catch {
        // user cancelled
      }
    },
    onError: (err) => {
      const detail =
        err instanceof ApiError ? err.detail : 'Could not create invite.';
      Alert.alert('Invite failed', detail);
    },
  });

  if (!missionId) return null;

  return (
    <ScreenContainer
      scroll
      refreshControl={
        <RefreshControl
          refreshing={missionQ.isRefetching}
          onRefresh={() => {
            void missionQ.refetch();
          }}
          tintColor={colors.primary}
        />
      }
    >
      {missionQ.isLoading ? (
        <Spinner label="Loading mission…" />
      ) : missionQ.error ? (
        <Card>
          <Text style={[typography.body, { color: colors.danger }]}>
            {missionQ.error instanceof ApiError
              ? missionQ.error.detail
              : 'Failed to load mission.'}
          </Text>
        </Card>
      ) : missionQ.data ? (
        <>
          <Card>
            <Text style={[typography.h2, { color: colors.text }]}>
              {missionQ.data.title}
            </Text>
            <Text
              style={[typography.caption, { color: colors.textMuted, marginTop: spacing.xs }]}
            >
              {missionQ.data.status} · radius{' '}
              {(missionQ.data.search_radius_m / 1000).toFixed(1)} km
            </Text>
            {missionQ.data.description ? (
              <Text
                style={[typography.body, { color: colors.text, marginTop: spacing.sm }]}
              >
                {missionQ.data.description}
              </Text>
            ) : null}
            <View style={styles.actions}>
              <Button
                title={pollingRunId ? 'Working…' : 'Recommend!'}
                onPress={() => recommend.mutate()}
                loading={recommend.isPending || !!pollingRunId}
              />
              <Button
                title="Invite"
                variant="secondary"
                onPress={() => inviteMutation.mutate()}
                loading={inviteMutation.isPending}
              />
            </View>
            {pollingRunId ? (
              <Text
                style={[typography.caption, { color: colors.textMuted, marginTop: spacing.sm }]}
              >
                Run {pollingRunId.slice(0, 8)}… polling every 2s.
              </Text>
            ) : null}
          </Card>

          <Text
            style={[
              typography.h3,
              { color: colors.text, marginTop: spacing.md, marginBottom: spacing.sm },
            ]}
          >
            Members ({missionQ.data.members.length})
          </Text>
          {missionQ.data.members.map((m) => (
            <Card key={m.user_id}>
              <Text style={[typography.body, { color: colors.text }]}>
                {m.user_id.slice(0, 8)}
              </Text>
              <Text
                style={[typography.caption, { color: colors.textMuted, marginTop: spacing.xs }]}
              >
                {m.role} · joined {formatRelative(m.joined_at)}
              </Text>
            </Card>
          ))}
        </>
      ) : null}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
});
