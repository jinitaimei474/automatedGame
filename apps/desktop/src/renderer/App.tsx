import { AppShell, Badge, Group, NavLink, Text } from '@mantine/core';
import { IconActivity, IconBrandAmongUs, IconDashboard, IconDeviceGamepad2, IconMicroscope, IconSettings } from '@tabler/icons-react';
import { useState } from 'react';
import type { TaskManifest } from '../shared/protocol';
import { TaskStartModal } from './components/TaskStartModal';
import { useBackend } from './hooks/useBackend';
import { DashboardPage } from './pages/DashboardPage';
import { GamesPage } from './pages/GamesPage';
import { MonitorPage } from './pages/MonitorPage';
import { SettingsPage } from './pages/SettingsPage';
import { TrainingPage } from './pages/TrainingPage';

type Page = 'dashboard' | 'games' | 'monitor' | 'settings' | 'training';
const navigation = [
  ['dashboard', '仪表盘', IconDashboard], ['games', '游戏与功能', IconDeviceGamepad2],
  ['monitor', '实时监控', IconActivity], ['settings', '设置', IconSettings], ['training', '训练帮助', IconMicroscope]
] as const;

export function App() {
  const backend = useBackend();
  const [page, setPage] = useState<Page>('games');
  const [selectedTask, setSelectedTask] = useState<TaskManifest | null>(null);

  const requestStart = (task: TaskManifest) => {
    if (task.parameters.length) setSelectedTask(task);
    else backend.send({ type: 'start_task', payload: { gameId: 'clash_royale', taskId: task.id, parameters: {} } });
  };
  const startClassic = (parameters: Record<string, unknown>) => {
    backend.send({ type: 'start_task', payload: { gameId: 'clash_royale', taskId: 'classic_1v1_loop', parameters } });
    setSelectedTask(null); setPage('dashboard');
  };

  return <>
    <AppShell navbar={{ width: 260, breakpoint: 'sm' }} padding="xl">
      <AppShell.Navbar p="md" className="sidebar">
        <Group mb="xl" gap="sm"><div className="brand-mark"><IconBrandAmongUs size={24} /></div><div><Text fw={900}>GAME AUTO</Text><Text size="xs" c="dimmed">AUTOMATION HUB</Text></div></Group>
        {navigation.map(([id, label, Icon]) => <NavLink key={id} active={page === id} label={label} leftSection={<Icon size={19} />} onClick={() => setPage(id)} className="nav-item" />)}
        <div className="sidebar-bottom"><Text size="xs" c="dimmed">后端状态</Text><Group justify="space-between" mt={5}><Text size="sm">Python Core</Text><Badge color={backend.connected ? 'teal' : 'red'} variant="dot">{backend.connected ? '在线' : '离线'}</Badge></Group></div>
      </AppShell.Navbar>
      <AppShell.Main className="main-content">
        {page === 'dashboard' && <DashboardPage connected={backend.connected} state={backend.workflowState} progress={backend.progress} completed={backend.completed} error={backend.error} send={backend.send} onNew={() => { backend.newTask(); setPage('games'); }} />}
        {page === 'games' && <GamesPage games={backend.games} isActive={backend.isActive} completed={backend.completed} onStart={requestStart} />}
        {page === 'monitor' && <MonitorPage state={backend.workflowState} progress={backend.progress} logs={backend.logs} screenshot={backend.screenshot} detections={backend.detections} />}
        {page === 'settings' && <SettingsPage settings={backend.settings} setSettings={backend.setSettings} />}
        {page === 'training' && <TrainingPage />}
      </AppShell.Main>
    </AppShell>
    <TaskStartModal task={selectedTask} opened={selectedTask !== null} onClose={() => setSelectedTask(null)} onStart={startClassic} />
  </>;
}
