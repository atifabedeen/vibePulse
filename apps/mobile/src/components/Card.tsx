import React, { PropsWithChildren } from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';

import { colors } from '@/theme/colors';
import { radius, spacing } from '@/theme/spacing';

interface CardProps {
  style?: ViewStyle;
}

export function Card({ children, style }: PropsWithChildren<CardProps>) {
  return <View style={[styles.card, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
});
