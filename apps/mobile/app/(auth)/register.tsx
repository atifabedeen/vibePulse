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
import { RegisterInput, registerSchema } from '@/utils/validation';

export default function RegisterScreen() {
  const router = useRouter();
  const { register } = useAuth();
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      password: '',
      display_name: '',
      avatar_url: '',
    },
  });

  const onSubmit = async (values: RegisterInput) => {
    try {
      const payload = {
        email: values.email,
        password: values.password,
        display_name: values.display_name,
        avatar_url: values.avatar_url ? values.avatar_url : null,
      };
      await register(payload);
      router.replace('/(app)/missions');
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.detail
          : 'Could not create your account.';
      Alert.alert('Sign up failed', msg);
    }
  };

  return (
    <ScreenContainer scroll>
      <View style={styles.header}>
        <Text style={[typography.h1, { color: colors.text }]}>
          Create account
        </Text>
        <Text style={[typography.body, { color: colors.textMuted }]}>
          Join missions and vote with friends.
        </Text>
      </View>

      <Controller
        control={control}
        name="display_name"
        render={({ field: { value, onChange, onBlur } }) => (
          <Input
            label="Display name"
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            error={errors.display_name?.message}
          />
        )}
      />
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
      <Controller
        control={control}
        name="avatar_url"
        render={({ field: { value, onChange, onBlur } }) => (
          <Input
            label="Avatar URL (optional)"
            value={value ?? ''}
            onChangeText={onChange}
            onBlur={onBlur}
            autoCapitalize="none"
            keyboardType="url"
            error={errors.avatar_url?.message}
          />
        )}
      />

      <Button
        title="Create account"
        onPress={handleSubmit(onSubmit)}
        loading={isSubmitting}
      />

      <View style={styles.footer}>
        <Text style={[typography.body, { color: colors.textMuted }]}>
          Already have an account?
        </Text>
        <Link href="/(auth)/login" style={styles.link}>
          Sign in
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
