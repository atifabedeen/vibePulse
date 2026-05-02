import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { Alert, StyleSheet, Text, View } from 'react-native';

import { ApiError, missionsApi } from '@/api';
import type { MissionCreate } from '@/api';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { ScreenContainer } from '@/components/ScreenContainer';
import { colors } from '@/theme/colors';
import { spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';
import { MissionCreateInput, missionCreateSchema } from '@/utils/validation';

// Atlanta default per the C5 brief: tap-to-set on a map is later.
const ATLANTA = { lat: 33.749, lng: -84.388 };

const RADIUS_PRESETS = [1000, 3000, 5000, 10000];

export default function NewMissionScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [radius, setRadius] = useState(3000);

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<MissionCreateInput>({
    resolver: zodResolver(missionCreateSchema),
    defaultValues: {
      title: '',
      description: '',
      location: ATLANTA,
      search_radius_m: 3000,
    },
  });

  const create = useMutation({
    mutationFn: (body: MissionCreate) => missionsApi.create(body),
    onSuccess: async (mission) => {
      await queryClient.invalidateQueries({ queryKey: ['missions'] });
      router.replace(`/(app)/missions/${mission.id}`);
    },
    onError: (err) => {
      const msg =
        err instanceof ApiError ? err.detail : 'Failed to create mission.';
      Alert.alert('Could not create mission', msg);
    },
  });

  const onSubmit = (values: MissionCreateInput) => {
    const body: MissionCreate = {
      title: values.title,
      description: values.description ? values.description : null,
      location: values.location,
      search_radius_m: radius,
    };
    create.mutate(body);
  };

  return (
    <ScreenContainer scroll>
      <Text
        style={[typography.h2, { color: colors.text, marginBottom: spacing.md }]}
      >
        New mission
      </Text>

      <Controller
        control={control}
        name="title"
        render={({ field: { value, onChange, onBlur } }) => (
          <Input
            label="Title"
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            placeholder="Friday dinner"
            error={errors.title?.message}
          />
        )}
      />
      <Controller
        control={control}
        name="description"
        render={({ field: { value, onChange, onBlur } }) => (
          <Input
            label="Description (optional)"
            value={value ?? ''}
            onChangeText={onChange}
            onBlur={onBlur}
            multiline
            placeholder="Anything everyone should know."
            error={errors.description?.message}
          />
        )}
      />

      <Text style={[typography.label, styles.sectionLabel]}>Location</Text>
      <View style={styles.locationRow}>
        <Text style={[typography.body, { color: colors.text }]}>
          Atlanta, GA
        </Text>
        <Text
          style={[typography.caption, { color: colors.textMuted }]}
        >
          {ATLANTA.lat.toFixed(4)}, {ATLANTA.lng.toFixed(4)}
        </Text>
      </View>
      <Text
        style={[typography.caption, { color: colors.textMuted, marginBottom: spacing.md }]}
      >
        Map picker arrives in a later milestone.
      </Text>

      <Text style={[typography.label, styles.sectionLabel]}>
        Search radius: {(radius / 1000).toFixed(1)} km
      </Text>
      <View style={styles.pillRow}>
        {RADIUS_PRESETS.map((r) => {
          const active = radius === r;
          return (
            <Button
              key={r}
              title={`${(r / 1000).toFixed(0)}km`}
              variant={active ? 'primary' : 'secondary'}
              size="sm"
              onPress={() => setRadius(r)}
            />
          );
        })}
      </View>

      <Button
        title="Create mission"
        onPress={handleSubmit(onSubmit)}
        loading={isSubmitting || create.isPending}
        style={{ marginTop: spacing.lg }}
      />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  sectionLabel: {
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
  },
  locationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  pillRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    flexWrap: 'wrap',
  },
});
