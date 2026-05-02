import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { PlaceOut, RankingItem } from '@/api';
import { colors } from '@/theme/colors';
import { radius, spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

import { Card } from './Card';

interface Props {
  ranking: RankingItem;
  place: PlaceOut | null;
}

export function RankingCard({ ranking, place }: Props) {
  const pros = (ranking.reasons?.pros ?? []) as string[];
  const cons = (ranking.reasons?.cons ?? []) as string[];
  // Score is a floating-point in some unspecified range; clamp 0-1 visualisation.
  const pct = Math.max(0, Math.min(1, ranking.score));
  return (
    <Card>
      <View style={styles.headerRow}>
        <View style={styles.rankBadge}>
          <Text style={styles.rankText}>#{ranking.rank}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[typography.h3, { color: colors.text }]}>
            {place?.name ?? `Place ${ranking.place_id.slice(0, 6)}`}
          </Text>
          {place?.address ? (
            <Text style={[typography.caption, { color: colors.textMuted }]}>
              {place.address}
            </Text>
          ) : null}
        </View>
        <Text style={[typography.bodyBold, { color: colors.primary }]}>
          {ranking.score.toFixed(2)}
        </Text>
      </View>

      <View style={styles.barTrack}>
        <View style={[styles.barFill, { width: `${pct * 100}%` }]} />
      </View>

      {pros.length ? (
        <View style={styles.section}>
          <Text style={[typography.label, { color: colors.success }]}>
            Pros
          </Text>
          {pros.map((p, i) => (
            <Text
              key={`pro-${i}`}
              style={[typography.body, { color: colors.text }]}
            >
              <Text style={{ color: colors.success }}>{'✓'} </Text>
              {p}
            </Text>
          ))}
        </View>
      ) : null}

      {cons.length ? (
        <View style={styles.section}>
          <Text style={[typography.label, { color: colors.danger }]}>Cons</Text>
          {cons.map((c, i) => (
            <Text
              key={`con-${i}`}
              style={[typography.body, { color: colors.text }]}
            >
              <Text style={{ color: colors.danger }}>{'✗'} </Text>
              {c}
            </Text>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  rankBadge: {
    backgroundColor: colors.primaryDim,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: radius.md,
  },
  rankText: { color: '#fff', fontWeight: '700' },
  barTrack: {
    height: 6,
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.pill,
    overflow: 'hidden',
    marginBottom: spacing.sm,
  },
  barFill: {
    height: '100%',
    backgroundColor: colors.primary,
  },
  section: { marginTop: spacing.sm, gap: spacing.xs },
});
