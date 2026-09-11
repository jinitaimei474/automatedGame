import { contextBridge, ipcRenderer } from 'electron';
import type { BackendEvent, ClientMessage, DesktopApi } from '../shared/protocol';

const api: DesktopApi = {
  send: (message: ClientMessage) => ipcRenderer.send('backend:send', message),
  onBackendEvent: (listener: (event: BackendEvent) => void) => {
    const wrapped = (_event: Electron.IpcRendererEvent, payload: BackendEvent) => listener(payload);
    ipcRenderer.on('backend:event', wrapped);
    return () => ipcRenderer.removeListener('backend:event', wrapped);
  },
  saveSettings: (settings) => ipcRenderer.invoke('settings:save', settings),
  chooseFile: (kind) => ipcRenderer.invoke('dialog:choose-file', kind)
};

contextBridge.exposeInMainWorld('gameHub', api);

