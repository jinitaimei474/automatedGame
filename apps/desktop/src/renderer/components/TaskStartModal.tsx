import { Alert, Button, Group, Modal, NumberInput, Stack, Text } from '@mantine/core';
import { useEffect, useState } from 'react';
import type { TaskManifest } from '../../shared/protocol';

export function TaskStartModal({ task, opened, onClose, onStart }: {
  task: TaskManifest | null;
  opened: boolean;
  onClose: () => void;
  onStart: (parameters: Record<string, unknown>) => void;
}) {
  const schema = task?.parameters[0];
  const [value, setValue] = useState<string | number>('');
  useEffect(() => { if (opened && schema) setValue(schema.defaultValue as number); }, [opened, schema]);
  const valid = typeof value === 'number' && Number.isInteger(value) && value >= (schema?.min ?? 1) && value <= (schema?.max ?? 9999);
  let error = '';
  if (value === '') error = '请输入目标皇冠数量';
  else if (typeof value !== 'number' || !Number.isInteger(value)) error = '目标皇冠数量必须是正整数';
  else if (value < (schema?.min ?? 1)) error = `目标皇冠数量不能小于 ${schema?.min ?? 1}`;
  else if (value > (schema?.max ?? 9999)) error = `目标皇冠数量不能超过 ${schema?.max ?? 9999}`;

  return (
    <Modal opened={opened} onClose={onClose} title="启动经典 1v1 任务" centered radius="lg">
      <Stack>
        <Text size="sm" c="dimmed">每次新建任务都需要输入或确认皇冠目标。本次统计从 0 开始。</Text>
        {schema && <NumberInput label={schema.label} description={schema.description} suffix={` ${schema.unit || ''}`} min={schema.min} max={schema.max} value={value} onChange={setValue} error={!valid ? error : undefined} allowDecimal={false} allowNegative={false} required />}
        <Alert color="cyan" variant="light">累计皇冠达到或超过目标后，工作流会完成结算并安全停止。</Alert>
        <Group justify="flex-end"><Button variant="default" onClick={onClose}>取消</Button><Button disabled={!valid} onClick={() => onStart({ [schema!.key]: value })}>开始任务</Button></Group>
      </Stack>
    </Modal>
  );
}

