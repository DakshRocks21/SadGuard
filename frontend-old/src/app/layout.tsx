// frontend/app/layout.tsx
import './globals.css';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import React from 'react';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <title>Sandbox Manager</title>
      </head>
      <body>
        <CssBaseline />
        {children}
      </body>
    </html>
  );
}
