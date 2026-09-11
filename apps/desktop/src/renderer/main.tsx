import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider } from '@mantine/core';
import '@mantine/core/styles.css';
import './styles.css';
import { App } from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="dark" theme={{ primaryColor: 'cyan', fontFamily: 'Inter, "Microsoft YaHei", sans-serif' }}>
      <App />
    </MantineProvider>
  </React.StrictMode>
);

