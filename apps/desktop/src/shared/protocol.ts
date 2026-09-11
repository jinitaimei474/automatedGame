export type ParameterType = 'integer' | 'number' | 'boolean' | 'string' | 'select';

export interface TaskParameterSchema {
  key: string;
  label: string;
  type: ParameterType;
  required: boolean;
  defaultValue: unknown;
  min?: number;
  max?: number;
  description?: string;
  unit?: string;
  options?: string[];
}

export interface TaskManifest {
  id: string;
  name: string;
  description: string;
  parameters: TaskParameterSchema[];
}

export interface GameManifest {
  id: string;
  name: string;
  packageName: string;
  modelPath: string;
  tasks: TaskManifest[];
}

export interface CrownProgress {
  targetCrowns: number;
  earnedCrowns: number;
  remainingCrowns: number;
  roundCount: number;
  lastRoundCrowns: number;
  status: string;
  startedAt?: string;
  completedAt?: string | null;
  stopReason?: string | null;
}

export interface BackendEvent<T = Record<string, unknown>> {
  type:
    | 'backend_ready' | 'manifest_updated' | 'task_started' | 'task_state_changed'
    | 'task_progress_updated' | 'crown_result_detected' | 'crown_result_confirmed'
    | 'task_target_reached' | 'task_completed' | 'task_paused' | 'task_stopped'
    | 'task_failed' | 'screenshot_updated' | 'detections_updated' | 'diagnostic_result' | 'log_message';
  timestamp: string;
  payload: T;
}

export type ClientMessage =
  | { type: 'get_manifest'; payload?: Record<string, never> }
  | { type: 'start_task'; payload: { gameId: string; taskId: string; parameters: Record<string, unknown>; mockRounds?: number[] } }
  | { type: 'pause_task' | 'resume_task' | 'stop_task' | 'emergency_stop'; payload?: Record<string, never> }
  | { type: 'test_connection' | 'test_screenshot' | 'test_launch_game' | 'test_model' | 'test_crown_detection'; payload?: Record<string, never> };

export interface DesktopApi {
  send: (message: ClientMessage) => void;
  onBackendEvent: (listener: (event: BackendEvent) => void) => () => void;
  saveSettings: (settings: Record<string, unknown>) => Promise<{ ok: boolean; error?: string }>;
  chooseFile: (kind: 'mumu' | 'adb' | 'model') => Promise<string | null>;
}
