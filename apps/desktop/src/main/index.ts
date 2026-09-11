import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { ChildProcessWithoutNullStreams, spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createInterface } from 'node:readline';
import type { ClientMessage } from '../shared/protocol';

let mainWindow: BrowserWindow | null = null;
let backend: ChildProcessWithoutNullStreams | null = null;

function backendCommand(): { command: string; args: string[] } {
  if (app.isPackaged) {
    return {
      command: join(process.resourcesPath, 'backend', 'game-automation-backend.exe'),
      args: ['--config', join(app.getPath('userData'), 'config', 'settings.json')]
    };
  }
  return { command: process.env.PYTHON_EXECUTABLE || 'python', args: ['-m', 'automation.backend', '--config', 'config/settings.json'] };
}

function startBackend(): void {
  const { command, args } = backendCommand();
  backend = spawn(command, args, { cwd: app.isPackaged ? process.resourcesPath : resolve(__dirname, '../..'), windowsHide: true });
  const lines = createInterface({ input: backend.stdout });
  lines.on('line', (line) => {
    try {
      mainWindow?.webContents.send('backend:event', JSON.parse(line));
    } catch {
      mainWindow?.webContents.send('backend:event', { type: 'log_message', timestamp: new Date().toISOString(), payload: { level: 'ERROR', message: `后端输出无法解析: ${line}` } });
    }
  });
  backend.stderr.on('data', (chunk) => mainWindow?.webContents.send('backend:event', {
    type: 'log_message', timestamp: new Date().toISOString(), payload: { level: 'ERROR', message: String(chunk).trim() }
  }));
  backend.on('error', (error) => mainWindow?.webContents.send('backend:event', {
    type: 'task_failed', timestamp: new Date().toISOString(), payload: { message: `Python 后端启动失败: ${error.message}` }
  }));
  backend.on('exit', (code) => {
    backend = null;
    mainWindow?.webContents.send('backend:event', {
      type: 'task_failed', timestamp: new Date().toISOString(), payload: { message: `Python 后端已退出（代码 ${code ?? 'unknown'}）` }
    });
  });
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1080,
    minHeight: 700,
    backgroundColor: '#080b12',
    title: 'Game Automation Hub',
    webPreferences: { preload: join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false }
  });
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) void mainWindow.loadURL(devUrl);
  else void mainWindow.loadFile(join(__dirname, '../../dist/index.html'));
}

ipcMain.on('backend:send', (_event, message: ClientMessage) => {
  if (!backend?.stdin.writable) return;
  backend.stdin.write(`${JSON.stringify(message)}\n`);
});

ipcMain.handle('settings:save', (_event, settings: Record<string, unknown>) => {
  try {
    const configDir = app.isPackaged ? join(app.getPath('userData'), 'config') : resolve(__dirname, '../../config');
    mkdirSync(configDir, { recursive: true });
    writeFileSync(join(configDir, 'settings.json'), JSON.stringify(settings, null, 2), 'utf8');
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : String(error) };
  }
});

ipcMain.handle('dialog:choose-file', async (_event, kind: 'mumu' | 'adb' | 'model') => {
  const filters = kind === 'model'
    ? [{ name: 'YOLO 模型', extensions: ['pt', 'onnx'] }]
    : [{ name: 'Windows 可执行文件', extensions: ['exe'] }];
  const result = await dialog.showOpenDialog({ properties: ['openFile'], filters });
  return result.canceled ? null : result.filePaths[0];
});

app.whenReady().then(() => {
  createWindow();
  startBackend();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on('before-quit', () => {
  if (backend?.stdin.writable) backend.stdin.write(`${JSON.stringify({ type: 'stop_task' })}\n`);
  backend?.kill();
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
