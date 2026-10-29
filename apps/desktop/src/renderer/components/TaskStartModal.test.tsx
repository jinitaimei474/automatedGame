import { fireEvent, render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { TaskStartModal } from './TaskStartModal';

const task = { id: 'classic_1v1_loop', name: '经典 1v1', description: '', parameters: [{ key: 'targetRounds', label: '目标对局数', type: 'integer' as const, required: true, defaultValue: 2, min: 1, max: 1000, unit: '局', description: '达标后自动停止' }] };

test('requires a valid integer before start', () => {
  const onStart = vi.fn();
  render(<MantineProvider><TaskStartModal task={task} opened onClose={() => {}} onStart={onStart} /></MantineProvider>);
  const input = screen.getByLabelText(/目标对局数/);
  fireEvent.change(input, { target: { value: '0' } });
  expect(screen.getByRole('button', { name: '开始任务' })).toBeDisabled();
  fireEvent.change(input, { target: { value: '5' } });
  fireEvent.click(screen.getByRole('button', { name: '开始任务' }));
  expect(onStart).toHaveBeenCalledWith({ targetRounds: 5 });
});
