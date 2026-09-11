import type { DesktopApi } from '../shared/protocol';

declare global {
  interface Window { gameHub?: DesktopApi; }
}

export {};
