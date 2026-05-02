import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
} from 'axios';
import Constants from 'expo-constants';

import { storage } from '@/utils/storage';

import type { AccessTokenOut, ProblemDetail } from './types';

/**
 * Custom error wrapping a FastAPI / RFC 7807-shaped error response so
 * call sites get one consistent type to handle.
 */
export class ApiError extends Error {
  status: number;
  title: string;
  detail: string;
  problem: ProblemDetail | null;

  constructor(opts: {
    status: number;
    title: string;
    detail: string;
    problem?: ProblemDetail | null;
  }) {
    super(opts.detail || opts.title);
    this.name = 'ApiError';
    this.status = opts.status;
    this.title = opts.title;
    this.detail = opts.detail;
    this.problem = opts.problem ?? null;
  }
}

function readBaseUrl(): string {
  // expo-constants exposes app.json `expo.extra` here.
  const extra = Constants.expoConfig?.extra as
    | { apiBaseUrl?: string }
    | undefined;
  const url = extra?.apiBaseUrl;
  if (!url) {
    // Soft fallback so dev still boots; logs a clear warning.
    // eslint-disable-next-line no-console
    console.warn(
      '[api] apiBaseUrl missing from app.json expo.extra; falling back to http://localhost:8000/api/v1',
    );
    return 'http://localhost:8000/api/v1';
  }
  return url.replace(/\/+$/, '');
}

const baseURL = readBaseUrl();

// Hooks the auth store can install at runtime to react to refresh failures
// without the api/client.ts file importing the store (avoids cycle).
type LogoutHook = () => Promise<void> | void;
let onAuthFailureHook: LogoutHook | null = null;
export function setOnAuthFailure(hook: LogoutHook | null): void {
  onAuthFailureHook = hook;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
});

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  // Skip token attach on the auth endpoints that don't take one.
  const url = config.url ?? '';
  const skip =
    url.startsWith('/auth/login') ||
    url.startsWith('/auth/register') ||
    url.startsWith('/auth/refresh');

  if (!skip) {
    const token = await storage.getAccess();
    if (token) {
      config.headers = config.headers ?? {};
      (config.headers as Record<string, string>)['Authorization'] =
        `Bearer ${token}`;
    }
  }
  return config;
});

interface RetryConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

/**
 * Hand-rolled refresh queue: while a refresh is in flight, queue any other
 * 401s so we only mint one new access token per refresh window.
 */
let refreshInFlight: Promise<string | null> | null = null;

async function runRefresh(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async (): Promise<string | null> => {
    try {
      const refresh = await storage.getRefresh();
      if (!refresh) return null;
      // Hit /auth/refresh directly with axios (not the wrapped client) to
      // avoid recursing through this same interceptor.
      const resp = await axios.post<AccessTokenOut>(
        `${baseURL}/auth/refresh`,
        { refresh_token: refresh },
        { headers: { 'Content-Type': 'application/json' } },
      );
      const access = resp.data?.access_token;
      if (!access) return null;
      await storage.setAccess(access);
      return access;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

apiClient.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError<ProblemDetail>) => {
    const original = error.config as RetryConfig | undefined;
    const status = error.response?.status;

    if (status === 401 && original && !original._retry) {
      // Skip refresh for refresh-token failures themselves.
      if ((original.url ?? '').startsWith('/auth/refresh')) {
        await storage.clearTokens();
        if (onAuthFailureHook) await onAuthFailureHook();
        return Promise.reject(toApiError(error));
      }
      original._retry = true;
      const newAccess = await runRefresh();
      if (newAccess) {
        original.headers = original.headers ?? {};
        (original.headers as Record<string, string>)['Authorization'] =
          `Bearer ${newAccess}`;
        return apiClient.request(original);
      }
      // Refresh failed — log out.
      await storage.clearTokens();
      if (onAuthFailureHook) await onAuthFailureHook();
    }

    return Promise.reject(toApiError(error));
  },
);

function toApiError(err: AxiosError<ProblemDetail>): ApiError {
  const status = err.response?.status ?? 0;
  const data = err.response?.data;
  let title = err.message || 'Request failed';
  let detail = '';

  if (data && typeof data === 'object') {
    if (typeof data.title === 'string') title = data.title;
    if (typeof data.detail === 'string') {
      detail = data.detail;
    } else if (data.detail && typeof data.detail === 'object') {
      try {
        detail = JSON.stringify(data.detail);
      } catch {
        detail = '';
      }
    }
  }

  if (!detail) {
    if (status === 0) detail = 'Network error — is the API reachable?';
    else if (status === 401) detail = 'Not signed in';
    else if (status === 403) detail = 'Forbidden';
    else if (status === 404) detail = 'Not found';
    else if (status === 409) detail = 'Conflict';
    else detail = err.message ?? 'Request failed';
  }

  return new ApiError({
    status,
    title,
    detail,
    problem: data ?? null,
  });
}

/** Strip an empty-string optional field so it omits in the JSON body. */
export function stripEmpty<T extends Record<string, unknown>>(obj: T): Partial<T> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v === '' || v === undefined) continue;
    out[k] = v;
  }
  return out as Partial<T>;
}

export const apiBaseUrl = baseURL;
