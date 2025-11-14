/**
 * Configuration Manager
 *
 * Handles loading configuration from local files or environment variables.
 * Prioritizes local configuration over environment variables.
 */

import { promises as fs } from 'fs';
import path from 'path';

export class ConfigManager {
  constructor() {
    this.config = null;
  }

  /**
   * Load configuration from local file or environment
   */
  async loadConfig(workingDirectory) {
    try {
      // Try local config first
      const localConfigPath = path.join(workingDirectory, '.doc-agent.json');

      if (await this.fileExists(localConfigPath)) {
        const configData = await fs.readFile(localConfigPath, 'utf8');
        this.config = JSON.parse(configData);

        // Resolve environment variables in config
        this.resolveEnvironmentVariables();

        return this.config;
      }

      // Fall back to environment variables
      this.config = {
        anthropic: {
          baseURL: process.env.ANTHROPIC_BASE_URL || 'https://api.anthropic.com',
          auth_token: process.env.ANTHROPIC_AUTH_TOKEN || '',
          model: process.env.ANTHROPIC_MODEL || 'deepseek-reasoner',
          small_fast_model: process.env.ANTHROPIC_SMALL_FAST_MODEL || 'deepseek-chat',
          timeout: parseInt(process.env.API_TIMEOUT_MS) || 600000,
          disable_nonessential_traffic: process.env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC === '1'
        }
      };

      return this.config;

    } catch (error) {
      console.warn('⚠️  Failed to load configuration, using defaults');
      return this.getDefaultConfig();
    }
  }

  /**
   * Resolve environment variables in configuration
   */
  resolveEnvironmentVariables() {
    const resolveString = (str) => {
      if (typeof str !== 'string') return str;
      return str.replace(/\$\{([^}]+)\}/g, (match, varName) => {
        return process.env[varName] || match;
      });
    };

    const resolveObject = (obj) => {
      if (Array.isArray(obj)) {
        return obj.map(resolveObject);
      } else if (obj && typeof obj === 'object') {
        const result = {};
        for (const [key, value] of Object.entries(obj)) {
          result[key] = resolveObject(value);
        }
        return result;
      }
      return resolveString(obj);
    };

    this.config = resolveObject(this.config);
  }

  /**
   * Get default configuration
   */
  getDefaultConfig() {
    return {
      anthropic: {
        baseURL: 'https://api.anthropic.com',
        auth_token: '',
        model: 'deepseek-reasoner',
        small_fast_model: 'deepseek-chat',
        timeout: 600000,
        disable_nonessential_traffic: true
      }
    };
  }

  /**
   * Check if file exists
   */
  async fileExists(filePath) {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }
}