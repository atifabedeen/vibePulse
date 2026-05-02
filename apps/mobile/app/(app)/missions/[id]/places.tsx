import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { RefreshControl, Text } from 'react-native';

import { ApiError, placesApi } from '@/api';
import { Card } from '@/components/Card';
import { PlaceCard } from '@/components/PlaceCard';
import { ScreenContainer } from '@/components/ScreenContainer';
import { Spinner } from '@/components/Spinner';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

export default function PlacesScreen() {
  const params = useLocalSearchParams<{ id: string }>();
  const missionId = String(params.id ?? '');

  const placesQ = useQuery({
    queryKey: ['places', missionId],
    queryFn: () => placesApi.list(missionId),
    enabled: !!missionId,
  });

  return (
    <ScreenContainer
      scroll
      refreshControl={
        <RefreshControl
          refreshing={placesQ.isRefetching}
          onRefresh={() => {
            void placesQ.refetch();
          }}
          tintColor={colors.primary}
        />
      }
    >
      {placesQ.isLoading ? (
        <Spinner label="Loading places…" />
      ) : placesQ.error ? (
        <Card>
          <Text style={[typography.body, { color: colors.danger }]}>
            {placesQ.error instanceof ApiError
              ? placesQ.error.detail
              : 'Failed to load places.'}
          </Text>
        </Card>
      ) : placesQ.data && placesQ.data.length > 0 ? (
        placesQ.data.map((p) => <PlaceCard key={p.id} place={p} />)
      ) : (
        <Card>
          <Text style={[typography.h3, { color: colors.text }]}>
            No candidates yet
          </Text>
          <Text
            style={[typography.body, { color: colors.textMuted, marginTop: spacing.sm }]}
          >
            Tap “Recommend!” on the overview tab to fetch candidates and
            score them.
          </Text>
        </Card>
      )}
    </ScreenContainer>
  );
}
