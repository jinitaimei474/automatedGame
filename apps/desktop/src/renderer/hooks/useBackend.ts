import { useCallback, useEffect, useMemo, useState } from 'react';
import type { BackendEvent, ClientMessage, CrownProgress, GameManifest } from '../../shared/protocol';

export interface LogEntry { timestamp: string; level: string; message: string; }

const emptyProgress: CrownProgress = {
  targetCrowns: 0, earnedCrowns: 0, remainingCrowns: 0, roundCount: 0,
  lastRoundCrowns: 0, status: 'IDLE'
};

export function useBackend() {
  const [connected, setConnected] = useState(false);
  const [games, setGames] = useState<GameManifest[]>([]);
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [progress, setProgress] = useState<CrownProgress>(emptyProgress);
  const [workflowState, setWorkflowState] = useState('IDLE');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [detections, setDetections] = useState<Array<{ label: string; confidence: number }>>([]);

  const addLog = useCallback((event: BackendEvent) => {
    const payload = event.payload as Record<string, unknown>;
    setLogs((current) => [...current.slice(-299), {
      timestamp: event.timestamp,
      level: String(payload.level || (event.type === 'task_failed' ? 'ERROR' : 'INFO')),
      message: String(payload.message || event.type)
    }]);
  }, []);

  useEffect(() => {
    if (!window.gameHub) return;
    const unsubscribe = window.gameHub.onBackendEvent((event) => {
      const payload = event.payload as Record<string, unknown>;
      if (event.type === 'backend_ready') {
        setConnected(true);
        window.gameHub?.send({ type: 'get_manifest' });
      } else if (event.type === 'manifest_updated') {
        setGames((payload.games as GameManifest[]) || []);
        setSettings((payload.settings as Record<string, unknown>) || {});
      } else if (event.type === 'task_state_changed') {
        setWorkflowState(String(payload.state));
      } else if (event.type === 'task_progress_updated' || event.type === 'task_started') {
        if ('targetCrowns' in payload) setProgress(payload as unknown as CrownProgress);
      } else if (event.type === 'task_target_reached' || event.type === 'task_completed') {
        if ('targetCrowns' in payload) setProgress(payload as unknown as CrownProgress);
        setCompleted(true);
        setWorkflowState(event.type === 'task_target_reached' ? 'TARGET_REACHED' : 'COMPLETED');
      } else if (event.type === 'task_stopped') {
        setProgress(payload as unknown as CrownProgress);
        setWorkflowState('STOPPED');
      } else if (event.type === 'task_paused') {
        setWorkflowState('PAUSED');
      } else if (event.type === 'task_failed') {
        setError(String(payload.message || '任务失败'));
        setWorkflowState('ERROR');
      } else if (event.type === 'diagnostic_result') {
        addLog({ ...event, type: 'log_message', payload: { level: payload.ok ? 'INFO' : 'ERROR', message: payload.message } });
      } else if (event.type === 'screenshot_updated') {
        setScreenshot(String(payload.image || ''));
      } else if (event.type === 'detections_updated') {
        setDetections((payload.detections as Array<{ label: string; confidence: number }>) || []);
      }
      if (event.type === 'log_message' || event.type === 'task_failed' || event.type === 'task_completed') addLog(event);
    });
    return unsubscribe;
  }, [addLog]);

  const send = useCallback((message: ClientMessage) => window.gameHub?.send(message), []);
  const newTask = useCallback(() => {
    setCompleted(false); setError(null); setWorkflowState('IDLE'); setProgress(emptyProgress);
  }, []);
  const isActive = useMemo(() => !['IDLE', 'STOPPED', 'ERROR', 'COMPLETED', 'TARGET_REACHED'].includes(workflowState), [workflowState]);

  return { connected, games, settings, setSettings, progress, workflowState, logs, error, completed, isActive, screenshot, detections, send, newTask };
}
