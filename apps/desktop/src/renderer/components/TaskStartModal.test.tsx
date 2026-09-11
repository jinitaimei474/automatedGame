import { fireEvent, render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { TaskStartModal } from './TaskStartModal';

const task = { id: 'classic_1v1_loop', name: '经典 1v1', description: '', parameters: [{ key: 'targetCrowns', label: '目标皇冠数量', type: 'integer' as const, required: true, defaultValue: 10, min: 1, max: 9999, unit: '个', description: '达标后自动停止' }] };

test('requires a valid integer before start', () => {
  const onStart = vi.fn();
  render(<MantineProvider><TaskStartModal task={task} opened onClose={() => {}} onStart={onStart} /></MantineProvider>);
  const input = screen.getByLabelText(/目标皇冠数量/);
  fireEvent.change(input, { target: { value: '0' } });
  expect(screen.getByRole('button', { name: '开始任务' })).toBeDisabled();
  fireEvent.change(input, { target: { value: '5' } });
  fireEvent.click(screen.getByRole('button', { name: '开始任务' }));
  expect(onStart).toHaveBeenCalledWith({ targetCrowns: 5 });
});
