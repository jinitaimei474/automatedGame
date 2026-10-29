import { Badge, Card, Group, Progress, SimpleGrid, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconCrown } from '@tabler/icons-react';
import type { CrownProgress } from '../../shared/protocol';

export function CrownProgressCard({ progress, state }: { progress: CrownProgress; state: string }) {
  const rounds = progress.targetRounds != null;
  const target = rounds ? progress.targetRounds! : progress.targetCrowns;
  const done = rounds ? progress.roundCount : progress.earnedCrowns;
  const remaining = Math.max(target - done, 0);
  const percent = target ? Math.min((done / target) * 100, 100) : 0;
  return (
    <Card className="panel" radius="lg" padding="lg">
      <Group justify="space-between" mb="md">
        <Group><ThemeIcon color="yellow" variant="light"><IconCrown size={18} /></ThemeIcon><Text fw={700}>{rounds ? '连续对局进度' : '皇冠任务进度'}</Text></Group>
        <Badge variant="light" color={state === 'TARGET_REACHED' || state === 'COMPLETED' ? 'teal' : 'cyan'}>{state}</Badge>
      </Group>
      <SimpleGrid cols={{ base: 2, sm: 4 }} mb="lg">
        <Metric label={rounds ? "目标局数" : "目标皇冠"} value={target} />
        <Metric label={rounds ? "已完成" : "已获得"} value={done} accent />
        <Metric label="剩余" value={remaining} />
        <Metric label="完成对局" value={`${progress.roundCount} 局`} />
      </SimpleGrid>
      <Stack gap={7}>
        <Group justify="space-between"><Text size="sm" c="dimmed">累计 {done} / {target}{rounds ? " 局" : ""}</Text><Text size="sm">{Math.round(percent)}%</Text></Group>
        <Progress value={percent} size="lg" radius="xl" color={percent >= 100 ? 'teal' : 'cyan'} />
        <Group justify="space-between"><Text size="xs" c="dimmed">达标后自动停止，不再开始下一局</Text><Text size="xs">{progress.lastRoundCrowns == null ? '本局皇冠未识别' : `本局 +${progress.lastRoundCrowns} 皇冠`}</Text></Group>
      </Stack>
    </Card>
  );
}

function Metric({ label, value, accent = false }: { label: string; value: number | string; accent?: boolean }) {
  return <div className="metric"><Text size="xs" c="dimmed">{label}</Text><Text fz={24} fw={800} c={accent ? 'yellow' : undefined}>{value}</Text></div>;
}

