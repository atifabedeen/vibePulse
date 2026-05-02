import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  ViewStyle,
} from 'react-native';

import { colors } from '@/theme/colors';
import { radius, spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  disabled,
  loading,
  style,
}: ButtonProps) {
  const isDisabled = disabled || loading;
  const palette = paletteFor(variant);
  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        sizeStyles[size],
        { backgroundColor: palette.bg, borderColor: palette.border },
        pressed && !isDisabled ? { opacity: 0.85 } : null,
        isDisabled ? { opacity: 0.5 } : null,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={palette.fg} />
      ) : (
        <Text style={[typography.bodyBold, { color: palette.fg }]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

function paletteFor(variant: Variant): {
  bg: string;
  fg: string;
  border: string;
} {
  switch (variant) {
    case 'secondary':
      return { bg: colors.surfaceAlt, fg: colors.text, border: colors.border };
    case 'danger':
      return { bg: colors.danger, fg: '#fff', border: colors.danger };
    case 'ghost':
      return { bg: 'transparent', fg: colors.text, border: colors.border };
    case 'primary':
    default:
      return { bg: colors.primary, fg: '#fff', border: colors.primary };
  }
}

const sizeStyles: Record<Size, ViewStyle> = {
  sm: { paddingVertical: spacing.xs, paddingHorizontal: spacing.md },
  md: { paddingVertical: spacing.sm + 2, paddingHorizontal: spacing.lg },
  lg: { paddingVertical: spacing.md + 2, paddingHorizontal: spacing.xl },
};

const styles = StyleSheet.create({
  base: {
    borderRadius: radius.md,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
});
