import { Alert, Button, Group, SimpleGrid, Text } from '@mantine/core';
import type { CrownProgress } from '../../shared/protocol';

export function CompletionCard({ progress, onNew }: { progress: CrownProgress; onNew: () => void }) {
  const duration = progress.startedAt && progress.completedAt
    ? Math.max(0, Math.round((Date.parse(progress.completedAt) - Date.parse(progress.startedAt)) / 1000)) : 0;
  return (
    <Alert color="teal" title="任务已完成" radius="lg">
      <Text mb="sm">自动停止原因：已达到目标皇冠数量。</Text>
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <Text size="sm">目标：{progress.targetCrowns}</Text><Text size="sm">实际：{progress.earnedCrowns}</Text>
        <Text size="sm">对局：{progress.roundCount}</Text><Text size="sm">用时：{duration} 秒</Text>
      </SimpleGrid>
      <Text size="xs" c="dimmed" mt="sm">开始：{progress.startedAt ? new Date(progress.startedAt).toLocaleString() : '—'} · 完成：{progress.completedAt ? new Date(progress.completedAt).toLocaleString() : '—'}</Text>
      <Group mt="md"><Button color="teal" onClick={onNew}>新建任务</Button></Group>
    </Alert>
  );
}
