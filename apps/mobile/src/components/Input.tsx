import React from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
} from 'react-native';

import { colors } from '@/theme/colors';
import { radius, spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

interface InputProps extends Omit<TextInputProps, 'style'> {
  label?: string;
  error?: string;
  multiline?: boolean;
}

export function Input({ label, error, multiline, ...rest }: InputProps) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      {label ? (
        <Text style={[typography.label, styles.label]}>{label}</Text>
      ) : null}
      <TextInput
        placeholderTextColor={colors.textMuted}
        {...rest}
        multiline={multiline}
        style={[
          styles.input,
          multiline ? styles.multi : null,
          error ? styles.errorBorder : null,
        ]}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  label: {
    color: colors.textMuted,
    marginBottom: spacing.xs,
  },
  input: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
    color: colors.text,
    fontSize: 15,
  },
  multi: {
    minHeight: 96,
    textAlignVertical: 'top',
  },
  errorBorder: {
    borderColor: colors.danger,
  },
  error: {
    color: colors.danger,
    fontSize: 12,
    marginTop: spacing.xs,
  },
});
