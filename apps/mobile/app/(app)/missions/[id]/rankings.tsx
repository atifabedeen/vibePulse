import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { useMemo } from 'react';
import { RefreshControl, Text } from 'react-native';

import { ApiError, placesApi, rankingsApi } from '@/api';
import type { PlaceOut } from '@/api';
import { Card } from '@/components/Card';
import { RankingCard } from '@/components/RankingCard';
import { ScreenContainer } from '@/components/ScreenContainer';
import { Spinner } from '@/components/Spinner';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

export default function RankingsScreen() {
  const params = useLocalSearchParams<{ id: string }>();
  const missionId = String(params.id ?? '');

  const rankingsQ = useQuery({
    queryKey: ['rankings', missionId],
    queryFn: () => rankingsApi.latest(missionId),
    enabled: !!missionId,
  });

  // Cross-reference with the cached places list so each ranking row can
  // show the place name + address.
  const placesQ = useQuery({
    queryKey: ['places', missionId],
    queryFn: () => placesApi.list(missionId),
    enabled: !!missionId,
  });

  const placeById = useMemo(() => {
    const m = new Map<string, PlaceOut>();
    placesQ.data?.forEach((p) => m.set(p.id, p));
    return m;
  }, [placesQ.data]);

  return (
    <ScreenContainer
      scroll
      refreshControl={
        <RefreshControl
          refreshing={rankingsQ.isRefetching || placesQ.isRefetching}
          onRefresh={() => {
            void rankingsQ.refetch();
            void placesQ.refetch();
          }}
          tintColor={colors.primary}
        />
      }
    >
      {rankingsQ.isLoading ? (
        <Spinner label="Loading rankings…" />
      ) : rankingsQ.error ? (
        <Card>
          <Text style={[typography.body, { color: colors.danger }]}>
            {rankingsQ.error instanceof ApiError
              ? rankingsQ.error.detail
              : 'Failed to load rankings.'}
          </Text>
        </Card>
      ) : rankingsQ.data && rankingsQ.data.items.length > 0 ? (
        rankingsQ.data.items
          .slice(0, 5)
          .map((r) => (
            <RankingCard
              key={r.id}
              ranking={r}
              place={placeById.get(r.place_id) ?? null}
            />
          ))
      ) : (
        <Card>
          <Text style={[typography.h3, { color: colors.text }]}>
            No rankings yet
          </Text>
          <Text
            style={[typography.body, { color: colors.textMuted, marginTop: spacing.sm }]}
          >
            Run the recommend graph from the overview tab to score
            candidates.
          </Text>
        </Card>
      )}
    </ScreenContainer>
  );
}
