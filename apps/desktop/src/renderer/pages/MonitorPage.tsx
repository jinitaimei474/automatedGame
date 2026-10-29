import { Badge, Card, Code, Group, ScrollArea, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import type { CrownProgress } from '../../shared/protocol';
import type { LogEntry } from '../hooks/useBackend';

export function MonitorPage({ state, progress, logs, screenshot, detections }: { state: string; progress: CrownProgress; logs: LogEntry[]; screenshot: string | null; detections: Array<{ label: string; confidence: number }> }) {
  return <Stack gap="lg">
    <div><Text c="cyan" fw={700} size="sm">LIVE MONITOR</Text><Title order={2}>实时监控</Title></div>
    <SimpleGrid cols={{ base: 1, md: 2 }}>
      <Card className="panel screenshot-panel" radius="lg"><Group justify="space-between"><Text fw={700}>模拟器画面</Text><Badge>{state}</Badge></Group>{screenshot ? <img className="screen-image" src={screenshot} alt="最新模拟器截图与检测框" /> : <div className="screen-placeholder"><Text c="dimmed">等待截图...</Text><Text size="xs" c="dimmed">检测框将覆盖显示在这里</Text></div>}</Card>
      <Card className="panel" radius="lg"><Text fw={700} mb="md">识别摘要</Text><Stack gap="xs"><Info label="当前节点" value={state} /><Info label="最近皇冠" value={`${progress.lastRoundCrowns ?? "未识别"}`} /><Info label="累计进度" value={progress.targetRounds != null ? `${progress.roundCount} / ${progress.targetRounds} 局` : `${progress.earnedCrowns} / ${progress.targetCrowns}`} /><Info label="当前目标" value={detections.slice(0, 3).map((item) => `${item.label} ${(item.confidence * 100).toFixed(0)}%`).join(' · ') || '暂无'} /></Stack></Card>
    </SimpleGrid>
    <Card className="panel" radius="lg"><Group justify="space-between" mb="sm"><Text fw={700}>运行日志</Text><Badge variant="light">{logs.length} 条</Badge></Group><ScrollArea h={260}>{logs.length === 0 ? <Text c="dimmed" size="sm">暂无日志</Text> : logs.map((log, index) => <Code key={`${log.timestamp}-${index}`} block className="log-line">[{new Date(log.timestamp).toLocaleTimeString()}] {log.level} {log.message}</Code>)}</ScrollArea></Card>
  </Stack>;
}

function Info({ label, value }: { label: string; value: string }) { return <Group justify="space-between" className="info-row"><Text size="sm" c="dimmed">{label}</Text><Text size="sm" fw={600}>{value}</Text></Group>; }
