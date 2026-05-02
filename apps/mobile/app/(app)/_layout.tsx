import { Redirect, Stack } from 'expo-router';

import { Spinner } from '@/components/Spinner';
import { ScreenContainer } from '@/components/ScreenContainer';
import { useAuth } from '@/hooks/useAuth';
import { colors } from '@/theme/colors';

export default function AppLayout() {
  const { hydrated, isAuthenticated } = useAuth();

  if (!hydrated) {
    return (
      <ScreenContainer>
        <Spinner label="Loading session…" />
      </ScreenContainer>
    );
  }
  if (!isAuthenticated) {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.text,
        contentStyle: { backgroundColor: colors.bg },
        headerTitleStyle: { color: colors.text },
      }}
    >
      <Stack.Screen
        name="missions/index"
        options={{ title: 'Missions' }}
      />
      <Stack.Screen
        name="missions/new"
        options={{ title: 'New mission', presentation: 'modal' }}
      />
      <Stack.Screen
        name="missions/[id]"
        options={{ headerShown: false }}
      />
    </Stack>
  );
}
