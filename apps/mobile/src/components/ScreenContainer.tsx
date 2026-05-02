import React, { PropsWithChildren } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
  ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';

interface Props {
  scroll?: boolean;
  refreshControl?: React.ReactElement;
  style?: ViewStyle;
  contentStyle?: ViewStyle;
  noPadding?: boolean;
}

export function ScreenContainer({
  children,
  scroll = false,
  refreshControl,
  style,
  contentStyle,
  noPadding,
}: PropsWithChildren<Props>) {
  const padded: ViewStyle = noPadding
    ? {}
    : { paddingHorizontal: spacing.lg, paddingVertical: spacing.lg };

  if (scroll) {
    return (
      <SafeAreaView style={[styles.safe, style]} edges={['top']}>
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <ScrollView
            style={styles.flex}
            contentContainerStyle={[padded, contentStyle]}
            keyboardShouldPersistTaps="handled"
            refreshControl={refreshControl}
          >
            {children}
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }
  return (
    <SafeAreaView style={[styles.safe, style]} edges={['top']}>
      <View style={[styles.flex, padded, contentStyle]}>{children}</View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  flex: { flex: 1 },
});
