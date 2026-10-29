import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { CrownProgressCard } from './CrownProgressCard';

test('caps progress at 100 while preserving actual overshoot text', () => {
  render(<MantineProvider><CrownProgressCard state="TARGET_REACHED" progress={{ targetCrowns: 5, earnedCrowns: 6, remainingCrowns: 0, roundCount: 2, lastRoundCrowns: 3, status: 'COMPLETED' }} /></MantineProvider>);
  expect(screen.getByText('累计 6 / 5')).toBeInTheDocument();
  expect(screen.getByText('100%')).toBeInTheDocument();
});


test('shows round progress independently of crowns', () => {
  render(<MantineProvider><CrownProgressCard state="IN_BATTLE" progress={{ targetRounds: 5, remainingRounds: 3, targetCrowns: 1, earnedCrowns: 6, remainingCrowns: 0, roundCount: 2, lastRoundCrowns: null, status: 'RUNNING' }} /></MantineProvider>);
  expect(screen.getByText('连续对局进度')).toBeInTheDocument();
  expect(screen.getByText('累计 2 / 5 局')).toBeInTheDocument();
  expect(screen.getByText('40%')).toBeInTheDocument();
  expect(screen.getByText('本局皇冠未识别')).toBeInTheDocument();
});
