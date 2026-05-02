import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { PlaceOut } from '@/api';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

import { Card } from './Card';

interface Props {
  place: PlaceOut;
  rightSlot?: React.ReactNode;
}

export function PlaceCard({ place, rightSlot }: Props) {
  return (
    <Card>
      <View style={styles.row}>
        <View style={styles.flex}>
          <Text style={[typography.h3, { color: colors.text }]}>
            {place.name}
          </Text>
          {place.address ? (
            <Text style={[typography.caption, styles.muted]}>
              {place.address}
            </Text>
          ) : null}
          <View style={styles.metaRow}>
            {place.rating != null ? (
              <Text style={[typography.caption, styles.meta]}>
                ★ {place.rating.toFixed(1)}
                {place.user_rating_ct != null
                  ? ` (${place.user_rating_ct})`
                  : ''}
              </Text>
            ) : null}
            {place.price_level != null ? (
              <Text style={[typography.caption, styles.meta]}>
                {'$'.repeat(Math.max(1, place.price_level))}
              </Text>
            ) : null}
            {place.cuisines.length ? (
              <Text style={[typography.caption, styles.meta]}>
                {place.cuisines.slice(0, 3).join(' · ')}
              </Text>
            ) : null}
          </View>
        </View>
        {rightSlot ? <View>{rightSlot}</View> : null}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  flex: { flex: 1 },
  muted: { color: colors.textMuted, marginTop: spacing.xs },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  meta: { color: colors.textMuted },
});
