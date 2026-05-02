import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { useMemo } from 'react';
import { Alert, RefreshControl, StyleSheet, Text, View } from 'react-native';

import {
  ApiError,
  placesApi,
  rankingsApi,
  votesApi,
} from '@/api';
import type { PlaceOut, RankingItem, VoteOut, VoteTally } from '@/api';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PlaceCard } from '@/components/PlaceCard';
import { ScreenContainer } from '@/components/ScreenContainer';
import { Spinner } from '@/components/Spinner';
import { useAuthStore } from '@/state/authStore';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

export default function VoteScreen() {
  const params = useLocalSearchParams<{ id: string }>();
  const missionId = String(params.id ?? '');
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.user?.id);

  const rankingsQ = useQuery({
    queryKey: ['rankings', missionId],
    queryFn: () => rankingsApi.latest(missionId),
    enabled: !!missionId,
  });

  const placesQ = useQuery({
    queryKey: ['places', missionId],
    queryFn: () => placesApi.list(missionId),
    enabled: !!missionId,
  });

  const tallyQ = useQuery({
    queryKey: ['vote-tally', missionId],
    queryFn: () => votesApi.tally(missionId),
    enabled: !!missionId,
  });

  const placeById = useMemo(() => {
    const m = new Map<string, PlaceOut>();
    placesQ.data?.forEach((p) => m.set(p.id, p));
    return m;
  }, [placesQ.data]);

  const myVotesQ = useQuery({
    queryKey: ['my-votes', missionId, userId],
    queryFn: async () => {
      // The API only returns the caller's votes via PUT /votes/me. There's
      // no GET-mine endpoint; we derive "my last vote per place" by sending
      // a no-op PUT only when the user actually votes. Until then we keep
      // an empty map and rely on the optimistic update path below.
      return [] as VoteOut[];
    },
    enabled: false,
  });
  void myVotesQ;

  const voteMutation = useMutation({
    mutationFn: (input: { placeId: string; weight: 1 | -1 }) =>
      votesApi.putMine(missionId, {
        place_id: input.placeId,
        weight: input.weight,
      }),
    onMutate: async (input) => {
      // Optimistic tally update so the running counts respond instantly.
      await queryClient.cancelQueries({
        queryKey: ['vote-tally', missionId],
      });
      const prev = queryClient.getQueryData<VoteTally>([
        'vote-tally',
        missionId,
      ]);
      if (prev) {
        const next: VoteTally = {
          tally: { ...prev.tally },
        };
        const bucket = next.tally[input.placeId] ?? { up: 0, veto: 0 };
        if (input.weight === 1) bucket.up += 1;
        else bucket.veto += 1;
        next.tally[input.placeId] = bucket;
        queryClient.setQueryData(['vote-tally', missionId], next);
      }
      return { prev };
    },
    onError: (err, _input, ctx) => {
      if (ctx?.prev) {
        queryClient.setQueryData(['vote-tally', missionId], ctx.prev);
      }
      const detail =
        err instanceof ApiError ? err.detail : 'Vote failed.';
      Alert.alert('Vote failed', detail);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: ['vote-tally', missionId],
      });
    },
  });

  const finalizeMutation = useMutation({
    mutationFn: () => votesApi.finalize(missionId),
    onSuccess: (data) => {
      Alert.alert(
        'Finalized',
        data.winner
          ? `Winner: ${data.winner.name}${
              data.backup ? ` · Backup: ${data.backup.name}` : ''
            }`
          : 'No votes yet.',
      );
    },
    onError: (err) => {
      const detail =
        err instanceof ApiError ? err.detail : 'Finalize failed.';
      Alert.alert('Finalize failed', detail);
    },
  });

  if (rankingsQ.isLoading) {
    return (
      <ScreenContainer>
        <Spinner label="Loading…" />
      </ScreenContainer>
    );
  }

  const items: RankingItem[] = rankingsQ.data?.items ?? [];

  return (
    <ScreenContainer
      scroll
      refreshControl={
        <RefreshControl
          refreshing={rankingsQ.isRefetching || tallyQ.isRefetching}
          onRefresh={() => {
            void rankingsQ.refetch();
            void tallyQ.refetch();
          }}
          tintColor={colors.primary}
        />
      }
    >
      {items.length === 0 ? (
        <Card>
          <Text style={[typography.h3, { color: colors.text }]}>
            Nothing to vote on
          </Text>
          <Text
            style={[typography.body, { color: colors.textMuted, marginTop: spacing.sm }]}
          >
            Run the recommend graph from the overview tab first.
          </Text>
        </Card>
      ) : (
        <>
          {items.map((r) => {
            const place = placeById.get(r.place_id);
            const counts = tallyQ.data?.tally[r.place_id] ?? {
              up: 0,
              veto: 0,
            };
            return (
              <Card key={r.id}>
                {place ? (
                  <PlaceCard place={place} />
                ) : (
                  <Text style={[typography.body, { color: colors.text }]}>
                    Place {r.place_id.slice(0, 8)}
                  </Text>
                )}
                <View style={styles.voteRow}>
                  <Button
                    title={`👍 Up (${counts.up})`}
                    variant="secondary"
                    onPress={() =>
                      voteMutation.mutate({
                        placeId: r.place_id,
                        weight: 1,
                      })
                    }
                  />
                  <Button
                    title={`🚫 Veto (${counts.veto})`}
                    variant="danger"
                    onPress={() =>
                      voteMutation.mutate({
                        placeId: r.place_id,
                        weight: -1,
                      })
                    }
                  />
                </View>
              </Card>
            );
          })}

          <Button
            title="Finalize voting (owner)"
            onPress={() => finalizeMutation.mutate()}
            loading={finalizeMutation.isPending}
            style={{ marginTop: spacing.md }}
          />
        </>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  voteRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
});
