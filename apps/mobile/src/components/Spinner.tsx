import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

interface SpinnerProps {
  label?: string;
  size?: 'small' | 'large';
}

export function Spinner({ label, size = 'large' }: SpinnerProps) {
  return (
    <View style={styles.wrap}>
      <ActivityIndicator size={size} color={colors.primary} />
      {label ? <Text style={styles.label}>{label}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl,
    gap: spacing.sm,
  },
  label: {
    ...typography.body,
    color: colors.textMuted,
    marginTop: spacing.sm,
  },
});
