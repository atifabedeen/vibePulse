import { Redirect } from 'expo-router';

import { Spinner } from '@/components/Spinner';
import { ScreenContainer } from '@/components/ScreenContainer';
import { useAuth } from '@/hooks/useAuth';

export default function AuthGate() {
  const { hydrated, isAuthenticated } = useAuth();

  if (!hydrated) {
    return (
      <ScreenContainer>
        <Spinner label="Loading…" />
      </ScreenContainer>
    );
  }

  if (isAuthenticated) {
    return <Redirect href="/(app)/missions" />;
  }
  return <Redirect href="/(auth)/login" />;
}
