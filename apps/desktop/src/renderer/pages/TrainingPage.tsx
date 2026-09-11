import { Card, Code, List, Stack, Text, Title } from '@mantine/core';

export function TrainingPage() {
  return <Stack gap="lg"><div><Text c="cyan" fw={700} size="sm">MODEL LAB</Text><Title order={2}>训练帮助</Title><Text c="dimmed">皇冠结算模型的数据准备与部署入口</Text></div>
    <Card className="panel" radius="lg"><Title order={4}>数据集目录</Title><Code block mt="sm">automation/training/clash_royale/datasets/images/{'{train,val,test}'}{`\n`}automation/training/clash_royale/datasets/labels/{'{train,val,test}'}</Code></Card>
    <Card className="panel" radius="lg"><Title order={4}>快速命令</Title><Code block mt="sm">python automation/training/clash_royale/check_dataset.py{`\n`}python automation/training/clash_royale/train.py --epochs 100 --device 0{`\n`}python automation/training/clash_royale/export.py --weights automation/training/clash_royale/runs/train/weights/best.pt</Code></Card>
    <Card className="panel" radius="lg"><Title order={4}>皇冠样本要点</Title><List mt="sm" spacing="xs"><List.Item>分别采集胜利、失败、平局以及 0～3 皇冠结算页面。</List.Item><List.Item>优先标注完整类别 result_crowns_0～3，不混入主页或奖励皇冠。</List.Item><List.Item>同一视频片段按场景分组划分，避免相邻帧跨训练集与验证集。</List.Item><List.Item>完整细则见中文训练指南。</List.Item></List></Card>
  </Stack>;
}
