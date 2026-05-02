import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useRouter } from 'expo-router';
import { Controller, useForm } from 'react-hook-form';
import { Alert, StyleSheet, Text, View } from 'react-native';

import { ApiError } from '@/api';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { ScreenContainer } from '@/components/ScreenContainer';
import { useAuth } from '@/hooks/useAuth';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';
import { LoginInput, loginSchema } from '@/utils/validation';

export default function LoginScreen() {
  const router = useRouter();
  const { login } = useAuth();
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const onSubmit = async (values: LoginInput) => {
    try {
      await login(values);
      router.replace('/(app)/missions');
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.detail : 'Login failed. Try again.';
      Alert.alert('Sign in failed', msg);
    }
  };

  return (
    <ScreenContainer scroll>
      <View style={styles.header}>
        <Text style={[typography.h1, { color: colors.text }]}>VibePulse</Text>
        <Text style={[typography.body, { color: colors.textMuted }]}>
          Sign in to keep planning hangouts.
        </Text>
      </View>

      <Controller
        control={control}
        name="email"
        render={({ field: { value, onChange, onBlur } }) => (
          <Input
            label="Email"
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            error={errors.email?.message}
          />
        )}
      />
      <Controller
        control={control}
        name="password"
        render={({ field: { value, onChange, onBlur } }) => (
          <Input
            label="Password"
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            secureTextEntry
            error={errors.password?.message}
          />
        )}
      />

      <Button
        title="Sign in"
        onPress={handleSubmit(onSubmit)}
        loading={isSubmitting}
      />

      <View style={styles.footer}>
        <Text style={[typography.body, { color: colors.textMuted }]}>
          New here?
        </Text>
        <Link href="/(auth)/register" style={styles.link}>
          Create an account
        </Link>
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { marginBottom: spacing.xl, gap: spacing.xs },
  footer: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.lg,
    alignItems: 'center',
  },
  link: { color: colors.link, fontWeight: '600' },
});
