export const colors = {
  bg: '#0d0f12',
  surface: '#161a20',
  surfaceAlt: '#1f242c',
  border: '#2a2f38',
  text: '#f4f5f7',
  textMuted: '#9aa3af',
  primary: '#7c5cff',
  primaryDim: '#5a3fcf',
  accent: '#34d399',
  danger: '#ef4444',
  warning: '#f59e0b',
  success: '#22c55e',
  link: '#60a5fa',
  pillBg: '#262c36',
  pillActiveBg: '#7c5cff',
} as const;

export type Color = keyof typeof colors;
