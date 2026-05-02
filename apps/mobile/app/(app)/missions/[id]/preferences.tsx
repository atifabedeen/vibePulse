import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { ApiError, preferencesApi } from '@/api';
import type { PreferencePayload } from '@/api';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Input } from '@/components/Input';
import { ScreenContainer } from '@/components/ScreenContainer';
import { Spinner } from '@/components/Spinner';
import { useAuthStore } from '@/state/authStore';
import { colors } from '@/theme/colors';
import { radius, spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';

const DIETARY = [
  'vegetarian',
  'vegan',
  'gluten_free',
  'halal',
  'kosher',
  'pescatarian',
  'dairy_free',
  'nut_free',
];

const CUISINE_SUGGESTIONS = [
  'italian',
  'japanese',
  'thai',
  'mexican',
  'indian',
  'chinese',
  'mediterranean',
  'american',
  'korean',
  'vietnamese',
  'ethiopian',
  'bbq',
];

const NOISE_LEVELS = [0, 1, 2, 3, 4, 5];

interface FormState {
  budget_max_cents: string;
  dietary: string[];
  likes: string[];
  dislikes: string[];
  vibe: string;
  noise: number | null;
  rawComment: string;
}

const EMPTY_FORM: FormState = {
  budget_max_cents: '',
  dietary: [],
  likes: [],
  dislikes: [],
  vibe: '',
  noise: null,
  rawComment: '',
};

export default function PreferencesScreen() {
  const params = useLocalSearchParams<{ id: string }>();
  const missionId = String(params.id ?? '');
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.user?.id);

  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const prefsQ = useQuery({
    queryKey: ['preferences', missionId],
    queryFn: () => preferencesApi.list(missionId),
    enabled: !!missionId,
  });

  // Hydrate the form once we have a row for the current user.
  useEffect(() => {
    if (!prefsQ.data || !userId) return;
    const mine = prefsQ.data.find((p) => p.user_id === userId);
    if (mine) {
      setForm({
        budget_max_cents:
          mine.budget_max_cents != null
            ? String(mine.budget_max_cents)
            : '',
        dietary: mine.dietary_restrictions ?? [],
        likes: mine.cuisines_like ?? [],
        dislikes: mine.cuisines_dislike ?? [],
        vibe: mine.vibe ?? '',
        noise: mine.noise_tolerance ?? null,
        rawComment: mine.raw_comment ?? '',
      });
    }
  }, [prefsQ.data, userId]);

  const buildPayload = (): PreferencePayload => {
    const cents = form.budget_max_cents
      ? Number.parseInt(form.budget_max_cents, 10)
      : null;
    return {
      budget_max_cents:
        cents != null && Number.isFinite(cents) ? cents : null,
      dietary_restrictions: form.dietary,
      cuisines_like: form.likes,
      cuisines_dislike: form.dislikes,
      vibe: form.vibe ? form.vibe : null,
      noise_tolerance: form.noise,
      raw_comment: form.rawComment ? form.rawComment : null,
    };
  };

  const saveMutation = useMutation({
    mutationFn: () => preferencesApi.putMine(missionId, buildPayload()),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['preferences', missionId],
      });
      Alert.alert('Saved', 'Preferences updated.');
    },
    onError: (err) => {
      const msg =
        err instanceof ApiError ? err.detail : 'Could not save preferences.';
      Alert.alert('Save failed', msg);
    },
  });

  const parseMutation = useMutation({
    mutationFn: () =>
      preferencesApi.parseMine(missionId, { raw_comment: form.rawComment }),
    onSuccess: async (parsed) => {
      // Merge parsed scalar/list fields back into the form state.
      setForm((prev) => ({
        ...prev,
        budget_max_cents:
          parsed.budget_max_cents != null
            ? String(parsed.budget_max_cents)
            : prev.budget_max_cents,
        dietary: parsed.dietary_restrictions ?? prev.dietary,
        likes: parsed.cuisines_like ?? prev.likes,
        dislikes: parsed.cuisines_dislike ?? prev.dislikes,
        vibe: parsed.vibe ?? prev.vibe,
        noise:
          parsed.noise_tolerance != null
            ? parsed.noise_tolerance
            : prev.noise,
      }));
      await queryClient.invalidateQueries({
        queryKey: ['preferences', missionId],
      });
    },
    onError: (err) => {
      const msg =
        err instanceof ApiError ? err.detail : 'Parse failed.';
      Alert.alert('Could not parse', msg);
    },
  });

  const toggle = <K extends keyof FormState>(
    key: K,
    item: string,
  ) => {
    setForm((prev) => {
      const list = (prev[key] as string[]) ?? [];
      const next = list.includes(item)
        ? list.filter((i) => i !== item)
        : [...list, item];
      return { ...prev, [key]: next } as FormState;
    });
  };

  if (prefsQ.isLoading) {
    return (
      <ScreenContainer>
        <Spinner label="Loading preferences…" />
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer scroll>
      <Card>
        <Text style={[typography.h3, { color: colors.text }]}>
          Your preferences
        </Text>
        <Text
          style={[typography.caption, { color: colors.textMuted, marginTop: spacing.xs }]}
        >
          These shape the recommend graph's scoring for this mission.
        </Text>
      </Card>

      <Input
        label="Budget per person (cents)"
        keyboardType="number-pad"
        value={form.budget_max_cents}
        onChangeText={(v) =>
          setForm((p) => ({ ...p, budget_max_cents: v.replace(/[^0-9]/g, '') }))
        }
        placeholder="e.g. 4000 = $40"
      />

      <Text style={[typography.label, styles.sectionLabel]}>
        Dietary restrictions
      </Text>
      <View style={styles.chipRow}>
        {DIETARY.map((d) => (
          <Chip
            key={d}
            label={d.replace('_', ' ')}
            active={form.dietary.includes(d)}
            onPress={() => toggle('dietary', d)}
          />
        ))}
      </View>

      <Text style={[typography.label, styles.sectionLabel]}>Cuisines I like</Text>
      <View style={styles.chipRow}>
        {CUISINE_SUGGESTIONS.map((c) => (
          <Chip
            key={`like-${c}`}
            label={c}
            active={form.likes.includes(c)}
            onPress={() => toggle('likes', c)}
          />
        ))}
      </View>

      <Text style={[typography.label, styles.sectionLabel]}>
        Cuisines I want to avoid
      </Text>
      <View style={styles.chipRow}>
        {CUISINE_SUGGESTIONS.map((c) => (
          <Chip
            key={`dislike-${c}`}
            label={c}
            active={form.dislikes.includes(c)}
            tone="danger"
            onPress={() => toggle('dislikes', c)}
          />
        ))}
      </View>

      <Input
        label="Vibe"
        value={form.vibe}
        onChangeText={(v) => setForm((p) => ({ ...p, vibe: v }))}
        placeholder="cozy / trendy / family-friendly / quiet …"
      />

      <Text style={[typography.label, styles.sectionLabel]}>
        Noise tolerance: {form.noise == null ? '—' : form.noise}
      </Text>
      <View style={styles.chipRow}>
        {NOISE_LEVELS.map((n) => (
          <Chip
            key={`noise-${n}`}
            label={String(n)}
            active={form.noise === n}
            onPress={() => setForm((p) => ({ ...p, noise: n }))}
          />
        ))}
      </View>

      <Input
        label="Free-form comment"
        multiline
        value={form.rawComment}
        onChangeText={(v) => setForm((p) => ({ ...p, rawComment: v }))}
        placeholder="I'm starving and tired, $30 max, somewhere quiet near work…"
      />

      <View style={styles.actions}>
        <Button
          title="Parse with AI"
          variant="secondary"
          onPress={() => {
            if (!form.rawComment.trim()) {
              Alert.alert('Nothing to parse', 'Add a comment first.');
              return;
            }
            parseMutation.mutate();
          }}
          loading={parseMutation.isPending}
        />
        <Button
          title="Save"
          onPress={() => saveMutation.mutate()}
          loading={saveMutation.isPending}
        />
      </View>
    </ScreenContainer>
  );
}

function Chip({
  label,
  active,
  onPress,
  tone = 'primary',
}: {
  label: string;
  active: boolean;
  onPress: () => void;
  tone?: 'primary' | 'danger';
}) {
  const activeBg = tone === 'danger' ? colors.danger : colors.primary;
  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.chip,
        active ? { backgroundColor: activeBg, borderColor: activeBg } : null,
      ]}
    >
      <Text
        style={[
          typography.label,
          { color: active ? '#fff' : colors.text },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  sectionLabel: {
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  chip: {
    backgroundColor: colors.pillBg,
    borderColor: colors.border,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    borderRadius: radius.pill,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
});
