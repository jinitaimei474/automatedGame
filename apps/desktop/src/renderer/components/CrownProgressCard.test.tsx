import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { CrownProgressCard } from './CrownProgressCard';

test('caps progress at 100 while preserving actual overshoot text', () => {
  render(<MantineProvider><CrownProgressCard state="TARGET_REACHED" progress={{ targetCrowns: 5, earnedCrowns: 6, remainingCrowns: 0, roundCount: 2, lastRoundCrowns: 3, status: 'COMPLETED' }} /></MantineProvider>);
  expect(screen.getByText('累计 6 / 5')).toBeInTheDocument();
  expect(screen.getByText('100%')).toBeInTheDocument();
});

