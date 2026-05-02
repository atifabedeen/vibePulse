import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import {
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { ApiError, missionsApi } from '@/api';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ScreenContainer } from '@/components/ScreenContainer';
import { Spinner } from '@/components/Spinner';
import { useAuth } from '@/hooks/useAuth';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';
import { formatRelative } from '@/utils/time';

export default function MissionsList() {
  const router = useRouter();
  const { logout } = useAuth();

  const query = useQuery({
    queryKey: ['missions'],
    queryFn: () => missionsApi.list({ limit: 50 }),
  });

  const onRefresh = () => {
    void query.refetch();
  };

  return (
    <ScreenContainer
      scroll
      refreshControl={
        <RefreshControl
          refreshing={query.isRefetching}
          onRefresh={onRefresh}
          tintColor={colors.primary}
        />
      }
    >
      <View style={styles.headerRow}>
        <Text style={[typography.h2, { color: colors.text }]}>
          Your missions
        </Text>
        <Button
          title="Sign out"
          variant="ghost"
          size="sm"
          onPress={() => {
            void logout();
          }}
        />
      </View>

      {query.isLoading ? (
        <Spinner label="Fetching missions…" />
      ) : query.error ? (
        <Card>
          <Text style={[typography.body, { color: colors.danger }]}>
            {query.error instanceof ApiError
              ? query.error.detail
              : 'Failed to load missions.'}
          </Text>
        </Card>
      ) : query.data && query.data.items.length === 0 ? (
        <Card>
          <Text style={[typography.h3, { color: colors.text }]}>
            No missions yet
          </Text>
          <Text
            style={[
              typography.body,
              { color: colors.textMuted, marginVertical: spacing.sm },
            ]}
          >
            Pick a place with friends. Create your first mission to get
            started.
          </Text>
          <Button
            title="Create your first mission"
            onPress={() => router.push('/(app)/missions/new')}
          />
        </Card>
      ) : (
        <>
          {query.data?.items.map((m) => (
            <Pressable
              key={m.id}
              onPress={() => router.push(`/(app)/missions/${m.id}`)}
            >
              <Card>
                <Text style={[typography.h3, { color: colors.text }]}>
                  {m.title}
                </Text>
                <Text
                  style={[
                    typography.caption,
                    { color: colors.textMuted, marginTop: spacing.xs },
                  ]}
                >
                  Status: {m.status} · Updated {formatRelative(m.updated_at)}
                </Text>
                {m.description ? (
                  <Text
                    style={[
                      typography.body,
                      { color: colors.text, marginTop: spacing.sm },
                    ]}
                    numberOfLines={2}
                  >
                    {m.description}
                  </Text>
                ) : null}
              </Card>
            </Pressable>
          ))}
          <Button
            title="New mission"
            onPress={() => router.push('/(app)/missions/new')}
            style={{ marginTop: spacing.sm }}
          />
        </>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
});
