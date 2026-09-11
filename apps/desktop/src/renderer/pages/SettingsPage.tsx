import { Alert, Button, Card, Checkbox, Group, NumberInput, SimpleGrid, Stack, Switch, Text, TextInput, Title } from '@mantine/core';
import { useState } from 'react';

const pathFields = [
  ['mumuExecutable', 'MuMu 可执行文件', 'mumu'], ['adbPath', 'adb.exe 路径', 'adb'], ['modelPath', 'YOLO 模型路径', 'model']
] as const;

export function SettingsPage({ settings, setSettings }: { settings: Record<string, unknown>; setSettings: (value: Record<string, unknown>) => void }) {
  const [notice, setNotice] = useState('');
  const update = (key: string, value: unknown) => setSettings({ ...settings, [key]: value });
  const save = async () => { const result = await window.gameHub?.saveSettings(settings); setNotice(result?.ok ? '设置已保存，重启后端后生效' : `保存失败：${result?.error || '桌面桥接不可用'}`); };
  const diagnostic = (type: 'test_connection' | 'test_screenshot' | 'test_launch_game' | 'test_model' | 'test_crown_detection') => { window.gameHub?.send({ type }); setNotice('诊断请求已发送，请在实时监控日志中查看结果'); };
  return <Stack gap="lg">
    <div><Text c="cyan" fw={700} size="sm">CONFIGURATION</Text><Title order={2}>设置</Title><Text c="dimmed">所有环境路径和识别阈值均可编辑</Text></div>
    {notice && <Alert color={notice.startsWith('保存失败') ? 'red' : 'teal'}>{notice}</Alert>}
    <Card className="panel" radius="lg"><Title order={4} mb="md">模拟器与模型</Title><Stack>
      {pathFields.map(([key, label, kind]) => <Group key={key} align="end"><TextInput label={label} value={String(settings[key] || '')} onChange={(event) => update(key, event.currentTarget.value)} style={{ flex: 1 }} /><Button variant="default" onClick={async () => { const path = await window.gameHub?.chooseFile(kind); if (path) update(key, path); }}>选择</Button></Group>)}
      <SimpleGrid cols={{ base: 1, sm: 2 }}><TextInput label="ADB 设备序列号" value={String(settings.adbSerial || '')} onChange={(e) => update('adbSerial', e.currentTarget.value)} /><TextInput label="游戏包名" value={String(settings.clashRoyalePackage || '')} onChange={(e) => update('clashRoyalePackage', e.currentTarget.value)} /><TextInput label="启动 Activity（可留空）" value={String(settings.clashRoyaleActivity || '')} onChange={(e) => update('clashRoyaleActivity', e.currentTarget.value)} /><TextInput label="调试截图目录" value={String(settings.debugScreenshotDirectory || '')} onChange={(e) => update('debugScreenshotDirectory', e.currentTarget.value)} /></SimpleGrid>
    </Stack></Card>
    <Card className="panel" radius="lg"><Title order={4} mb="md">识别与可靠性</Title><SimpleGrid cols={{ base: 1, sm: 3 }}>
      <NumberInput label="YOLO 置信度" min={0.1} max={1} step={0.05} value={Number(settings.yoloConfidence ?? 0.6)} onChange={(v) => update('yoloConfidence', v)} />
      <NumberInput label="皇冠置信度" min={0.1} max={1} step={0.05} value={Number(settings.crownConfidence ?? 0.75)} onChange={(v) => update('crownConfidence', v)} />
      <NumberInput label="皇冠连续确认帧" min={1} max={10} value={Number(settings.crownConfirmationFrames ?? 3)} onChange={(v) => update('crownConfirmationFrames', v)} />
      <NumberInput label="单状态超时（秒）" min={1} value={Number(settings.stateTimeoutSeconds ?? 30)} onChange={(v) => update('stateTimeoutSeconds', v)} />
      <NumberInput label="最大重试次数" min={0} value={Number(settings.maxRetries ?? 3)} onChange={(v) => update('maxRetries', v)} />
      <NumberInput label="最大皇冠识别失败" min={1} value={Number(settings.maxCrownFailures ?? 5)} onChange={(v) => update('maxCrownFailures', v)} />
      <NumberInput label="截图间隔（毫秒）" min={100} value={Number(settings.screenshotIntervalMs ?? 500)} onChange={(v) => update('screenshotIntervalMs', v)} />
      <NumberInput label="推理间隔（毫秒）" min={100} value={Number(settings.inferenceIntervalMs ?? 500)} onChange={(v) => update('inferenceIntervalMs', v)} />
      <NumberInput label="滑动距离" min={100} value={Number(settings.swipeDistance ?? 650)} onChange={(v) => update('swipeDistance', v)} />
      <NumberInput label="滑动时长（毫秒）" min={100} value={Number(settings.swipeDurationMs ?? 450)} onChange={(v) => update('swipeDurationMs', v)} />
      <NumberInput label="游戏启动等待（秒）" min={1} value={Number(settings.gameLaunchWaitSeconds ?? 10)} onChange={(v) => update('gameLaunchWaitSeconds', v)} />
      <TextInput label="日志级别" value={String(settings.logLevel || 'INFO')} onChange={(e) => update('logLevel', e.currentTarget.value)} />
    </SimpleGrid></Card>
    <Card className="panel" radius="lg"><Group><Switch checked={Boolean(settings.mockMode)} onChange={(e) => update('mockMode', e.currentTarget.checked)} label="Mock 模式" /><Checkbox checked={Boolean(settings.saveDebugScreenshots)} onChange={(e) => update('saveDebugScreenshots', e.currentTarget.checked)} label="保存调试截图" /><Checkbox checked={Boolean(settings.closeGameOnCompletion)} onChange={(e) => update('closeGameOnCompletion', e.currentTarget.checked)} label="完成后关闭游戏" /><Checkbox checked={Boolean(settings.closeEmulatorOnCompletion)} onChange={(e) => update('closeEmulatorOnCompletion', e.currentTarget.checked)} label="完成后关闭模拟器" /></Group></Card>
    <Group><Button onClick={save}>保存设置</Button><Button variant="default" onClick={() => diagnostic('test_connection')}>测试连接</Button><Button variant="default" onClick={() => diagnostic('test_screenshot')}>测试截图</Button><Button variant="default" onClick={() => diagnostic('test_launch_game')}>测试启动游戏</Button><Button variant="default" onClick={() => diagnostic('test_model')}>测试模型</Button><Button variant="default" onClick={() => diagnostic('test_crown_detection')}>测试皇冠识别</Button></Group>
  </Stack>;
}
