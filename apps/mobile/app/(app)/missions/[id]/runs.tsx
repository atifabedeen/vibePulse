import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import {
  Alert,
  Modal,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { agentsApi, ApiError } from '@/api';
import type { AgentRunOut } from '@/api';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Input } from '@/components/Input';
import { ScreenContainer } from '@/components/ScreenContainer';
import { Spinner } from '@/components/Spinner';
import { colors } from '@/theme/colors';
import { radius, spacing } from '@/theme/spacing';
import { typography } from '@/theme/typography';
import { formatRelative } from '@/utils/time';

export default function RunsScreen() {
  const params = useLocalSearchParams<{ id: string }>();
  const missionId = String(params.id ?? '');
  const queryClient = useQueryClient();

  const runsQ = useQuery({
    queryKey: ['agent-runs', missionId],
    queryFn: () => agentsApi.listRuns(missionId),
    enabled: !!missionId,
    refetchInterval: (query) => {
      const data = query.state.data as AgentRunOut[] | undefined;
      const hasRunning = data?.some(
        (r) => r.status === 'running' || r.status === 'pending',
      );
      return hasRunning ? 2000 : false;
    },
  });

  const approveMutation = useMutation({
    mutationFn: (runId: string) => agentsApi.approve(missionId, runId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['agent-runs', missionId],
      });
    },
    onError: (err) => {
      const detail =
        err instanceof ApiError ? err.detail : 'Approve failed.';
      Alert.alert('Approve failed', detail);
    },
  });

  const [rejectFor, setRejectFor] = useState<AgentRunOut | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [budgetOverride, setBudgetOverride] = useState('');

  const rejectMutation = useMutation({
    mutationFn: (input: {
      runId: string;
      reason: string;
      overrides?: Record<string, unknown> | null;
    }) =>
      agentsApi.reject(missionId, input.runId, {
        reason: input.reason,
        overrides: input.overrides ?? null,
      }),
    onSuccess: async () => {
      setRejectFor(null);
      setRejectReason('');
      setBudgetOverride('');
      await queryClient.invalidateQueries({
        queryKey: ['agent-runs', missionId],
      });
    },
    onError: (err) => {
      const detail =
        err instanceof ApiError ? err.detail : 'Reject failed.';
      Alert.alert('Reject failed', detail);
    },
  });

  if (runsQ.isLoading) {
    return (
      <ScreenContainer>
        <Spinner label="Loading runs…" />
      </ScreenContainer>
    );
  }

  return (
    <>
      <ScreenContainer
        scroll
        refreshControl={
          <RefreshControl
            refreshing={runsQ.isRefetching}
            onRefresh={() => {
              void runsQ.refetch();
            }}
            tintColor={colors.primary}
          />
        }
      >
        {runsQ.error ? (
          <Card>
            <Text style={[typography.body, { color: colors.danger }]}>
              {runsQ.error instanceof ApiError
                ? runsQ.error.detail
                : 'Failed to load runs.'}
            </Text>
          </Card>
        ) : runsQ.data && runsQ.data.length > 0 ? (
          runsQ.data.map((run) => (
            <Card key={run.id}>
              <View style={styles.row}>
                <Text style={[typography.h3, { color: colors.text }]}>
                  {run.graph_name}
                </Text>
                <View style={[styles.badge, badgeStyle(run.status)]}>
                  <Text style={styles.badgeText}>{run.status}</Text>
                </View>
              </View>
              <Text
                style={[typography.caption, { color: colors.textMuted, marginTop: spacing.xs }]}
              >
                trigger: {run.trigger} · started{' '}
                {formatRelative(run.started_at)}
              </Text>
              {run.error ? (
                <Text
                  style={[typography.caption, { color: colors.danger, marginTop: spacing.xs }]}
                >
                  {run.error}
                </Text>
              ) : null}

              {run.status === 'interrupted' ? (
                <View style={styles.actions}>
                  <Button
                    title="Approve"
                    onPress={() => approveMutation.mutate(run.id)}
                    loading={approveMutation.isPending}
                  />
                  <Button
                    title="Reject…"
                    variant="danger"
                    onPress={() => setRejectFor(run)}
                  />
                </View>
              ) : null}
            </Card>
          ))
        ) : (
          <Card>
            <Text style={[typography.body, { color: colors.textMuted }]}>
              No runs yet. Tap “Recommend!” to kick one off.
            </Text>
          </Card>
        )}
      </ScreenContainer>

      <Modal
        visible={!!rejectFor}
        transparent
        animationType="slide"
        onRequestClose={() => setRejectFor(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <Text style={[typography.h3, { color: colors.text }]}>
              Reject run
            </Text>
            <Text
              style={[typography.caption, { color: colors.textMuted, marginTop: spacing.xs }]}
            >
              The graph will replan with these overrides.
            </Text>
            <View style={{ height: spacing.md }} />
            <Input
              label="Reason"
              placeholder="why are you rejecting?"
              value={rejectReason}
              onChangeText={setRejectReason}
              multiline
            />
            <Input
              label="Override budget (cents) — optional"
              keyboardType="number-pad"
              value={budgetOverride}
              onChangeText={(v) =>
                setBudgetOverride(v.replace(/[^0-9]/g, ''))
              }
              placeholder="e.g. 1500"
            />
            <View style={styles.actions}>
              <Button
                title="Cancel"
                variant="ghost"
                onPress={() => setRejectFor(null)}
              />
              <Button
                title="Submit"
                variant="danger"
                loading={rejectMutation.isPending}
                onPress={() => {
                  if (!rejectFor) return;
                  if (!rejectReason.trim()) {
                    Alert.alert('Reason required');
                    return;
                  }
                  const overrides = budgetOverride
                    ? { budget_max_cents: Number.parseInt(budgetOverride, 10) }
                    : null;
                  rejectMutation.mutate({
                    runId: rejectFor.id,
                    reason: rejectReason.trim(),
                    overrides,
                  });
                }}
              />
            </View>
          </View>
        </View>
      </Modal>
    </>
  );
}

function badgeStyle(status: string) {
  switch (status) {
    case 'running':
    case 'pending':
      return { backgroundColor: colors.warning };
    case 'interrupted':
      return { backgroundColor: colors.primary };
    case 'completed':
      return { backgroundColor: colors.success };
    case 'failed':
      return { backgroundColor: colors.danger };
    default:
      return { backgroundColor: colors.surfaceAlt };
  }
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  badge: {
    paddingVertical: 2,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.pill,
  },
  badgeText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 12,
    textTransform: 'uppercase',
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalSheet: {
    backgroundColor: colors.surface,
    padding: spacing.lg,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
  },
});
