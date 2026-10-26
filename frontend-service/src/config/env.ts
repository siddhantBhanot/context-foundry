/**
 * Environment configuration module.
 * Safely accesses and provides fallback for Vite environment variables.
 */

export interface AppConfig {
  apiBaseUrl: string;
  isProduction: boolean;
  isDevelopment: boolean;
}

export const config: AppConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  isProduction: import.meta.env.PROD,
  isDevelopment: import.meta.env.DEV,
};

export default config;
