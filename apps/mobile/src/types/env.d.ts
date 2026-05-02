// Type augmentation for app.json `expo.extra` so `Constants.expoConfig.extra`
// is typed where we read it.
import 'expo-constants';

declare module 'expo-constants' {
  interface ExpoConfigExtra {
    apiBaseUrl: string;
  }
}

export {};
