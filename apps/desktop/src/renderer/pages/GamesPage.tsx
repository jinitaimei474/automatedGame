import { Badge, Button, Card, Group, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { IconCrown, IconGift, IconLock } from '@tabler/icons-react';
import type { GameManifest, TaskManifest } from '../../shared/protocol';

export function GamesPage({ games, isActive, completed, onStart }: {
  games: GameManifest[]; isActive: boolean; completed: boolean; onStart: (task: TaskManifest) => void;
}) {
  const clash = games.find((game) => game.id === 'clash_royale');
  return <Stack gap="lg">
    <div><Text c="cyan" fw={700} size="sm">GAME PLUGINS</Text><Title order={2}>游戏与功能</Title><Text c="dimmed">每个任务拥有独立参数和状态机</Text></div>
    <SimpleGrid cols={{ base: 1, md: 4 }}>
      <GameCard name="皇室战争" active /><GameCard name="部落冲突" /><GameCard name="全明星街头派对" /><GameCard name="自定义游戏" />
    </SimpleGrid>
    <Title order={3}>皇室战争功能</Title>
    <SimpleGrid cols={{ base: 1, md: 2 }}>
      {clash?.tasks.map((task) => <Card key={task.id} className="panel task-card" radius="lg" padding="lg">
        <Group justify="space-between" mb="md"><div className="task-icon">{task.id === 'classic_1v1_loop' ? <IconCrown /> : <IconGift />}</div><Badge variant="light">可用</Badge></Group>
        <Text fw={800} fz="lg">{task.name}</Text><Text c="dimmed" size="sm" mih={45}>{task.description}</Text>
        <Button fullWidth mt="lg" disabled={isActive || completed} onClick={() => onStart(task)}>开始任务</Button>
      </Card>)}
    </SimpleGrid>
  </Stack>;
}

function GameCard({ name, active = false }: { name: string; active?: boolean }) {
  return <Card className={`panel game-card ${active ? 'selected' : ''}`} radius="lg"><Group justify="space-between"><div><Text fw={800}>{name}</Text><Text size="xs" c="dimmed">{active ? '插件已加载' : '即将支持'}</Text></div>{active ? <Badge color="teal">已支持</Badge> : <IconLock size={18} />}</Group></Card>;
}
