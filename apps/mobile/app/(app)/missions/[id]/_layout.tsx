import {
  Stack,
  useLocalSearchParams,
  usePathname,
  useRouter,
} from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useMission } from '@/hooks/useMission';
import { colors } from '@/theme/colors';
import { radius, spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

const TABS: ReadonlyArray<{ slug: string; label: string }> = [
  { slug: '', label: 'Members' },
  { slug: 'preferences', label: 'Prefs' },
  { slug: 'places', label: 'Places' },
  { slug: 'rankings', label: 'Rankings' },
  { slug: 'vote', label: 'Vote' },
  { slug: 'runs', label: 'Runs' },
];

function TabBar({ missionId }: { missionId: string }) {
  const pathname = usePathname();
  const router = useRouter();
  return (
    <View style={styles.tabBarWrap}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.tabBar}
      >
        {TABS.map((t) => {
          const target = t.slug
            ? `/(app)/missions/${missionId}/${t.slug}`
            : `/(app)/missions/${missionId}`;
          const active =
            t.slug === ''
              ? pathname === `/missions/${missionId}`
              : pathname.endsWith(`/${t.slug}`);
          return (
            <Pressable
              key={t.slug || 'overview'}
              onPress={() => router.replace(target)}
              style={[styles.tab, active ? styles.tabActive : null]}
            >
              <Text
                style={[
                  typography.label,
                  { color: active ? '#fff' : colors.text },
                ]}
              >
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

export default function MissionDetailLayout() {
  const params = useLocalSearchParams<{ id: string }>();
  const id = String(params.id ?? '');
  const router = useRouter();
  useMission(id);

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.text,
        contentStyle: { backgroundColor: colors.bg },
        headerTitleStyle: { color: colors.text },
        header: ({ options }) => (
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <Pressable onPress={() => router.back()}>
                <Text style={[typography.label, { color: colors.link }]}>
                  ← Back
                </Text>
              </Pressable>
              <Text style={[typography.h3, { color: colors.text }]}>
                {options.title ?? 'Mission'}
              </Text>
            </View>
            <TabBar missionId={id} />
          </View>
        ),
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Mission' }} />
      <Stack.Screen name="preferences" options={{ title: 'Preferences' }} />
      <Stack.Screen name="places" options={{ title: 'Places' }} />
      <Stack.Screen name="rankings" options={{ title: 'Rankings' }} />
      <Stack.Screen name="vote" options={{ title: 'Vote' }} />
      <Stack.Screen name="runs" options={{ title: 'Agent runs' }} />
    </Stack>
  );
}

const styles = StyleSheet.create({
  header: {
    backgroundColor: colors.surface,
    paddingTop: spacing.xxl,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitleRow: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
    gap: spacing.xs,
  },
  tabBarWrap: { paddingBottom: spacing.sm },
  tabBar: {
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
  },
  tab: {
    paddingVertical: spacing.xs + 2,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
    backgroundColor: colors.pillBg,
  },
  tabActive: {
    backgroundColor: colors.pillActiveBg,
  },
});
