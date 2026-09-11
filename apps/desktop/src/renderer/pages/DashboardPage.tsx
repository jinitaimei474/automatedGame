import { Alert, Badge, Button, Card, Group, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { IconPlayerPause, IconPlayerStop, IconRefresh, IconShieldX } from '@tabler/icons-react';
import type { ClientMessage, CrownProgress } from '../../shared/protocol';
import { useEffect, useState } from 'react';
import { CompletionCard } from '../components/CompletionCard';
import { CrownProgressCard } from '../components/CrownProgressCard';

export function DashboardPage({ connected, state, progress, completed, error, send, onNew }: {
  connected: boolean; state: string; progress: CrownProgress; completed: boolean; error: string | null;
  send: (message: ClientMessage) => void; onNew: () => void;
}) {
  const running = !['IDLE', 'STOPPED', 'ERROR', 'COMPLETED', 'TARGET_REACHED'].includes(state);
  return <Stack gap="lg">
    <div><Text c="cyan" fw={700} size="sm">COMMAND CENTER</Text><Title order={2}>自动化仪表盘</Title><Text c="dimmed">设备、视觉识别与任务状态总览</Text></div>
    {error && <Alert color="red" title="任务异常">{error}</Alert>}
    {completed && <CompletionCard progress={progress} onNew={onNew} />}
    <SimpleGrid cols={{ base: 1, sm: 4 }}>
      <StatusCard label="Python 后端" value={connected ? '在线' : '未连接'} ok={connected} />
      <StatusCard label="当前游戏" value="皇室战争" ok />
      <StatusCard label="工作流状态" value={state} ok={state !== 'ERROR'} />
      <StatusCard label="已运行时间" value={<Elapsed startedAt={progress.startedAt} active={running} />} ok />
    </SimpleGrid>
    <CrownProgressCard progress={progress} state={state} />
    <Card className="panel" radius="lg">
      <Group justify="space-between">
        <div><Text fw={700}>任务控制</Text><Text size="sm" c="dimmed">停止信号会取消尚未执行的所有动作</Text></div>
        <Group>
          <Button leftSection={<IconPlayerPause size={17} />} variant="default" disabled={!running || state === 'PAUSED'} onClick={() => send({ type: 'pause_task' })}>暂停</Button>
          <Button leftSection={<IconRefresh size={17} />} variant="default" disabled={state !== 'PAUSED'} onClick={() => send({ type: 'resume_task' })}>继续</Button>
          <Button leftSection={<IconPlayerStop size={17} />} color="orange" disabled={!running} onClick={() => send({ type: 'stop_task' })}>停止</Button>
          <Button leftSection={<IconShieldX size={17} />} color="red" disabled={!running} onClick={() => send({ type: 'emergency_stop' })}>紧急停止</Button>
        </Group>
      </Group>
    </Card>
  </Stack>;
}

function StatusCard({ label, value, ok }: { label: string; value: React.ReactNode; ok: boolean }) {
  return <Card className="panel" radius="lg"><Group justify="space-between"><div><Text size="xs" c="dimmed">{label}</Text><Text fw={700}>{value}</Text></div><Badge color={ok ? 'teal' : 'red'}>{ok ? '正常' : '注意'}</Badge></Group></Card>;
}

function Elapsed({ startedAt, active }: { startedAt?: string; active: boolean }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [active]);
  if (!startedAt) return <>0 秒</>;
  const seconds = Math.max(0, Math.floor((now - Date.parse(startedAt)) / 1000));
  return <>{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}</>;
}
