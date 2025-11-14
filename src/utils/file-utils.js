/**
 * File Utilities
 *
 * Utility functions for file operations and path handling.
 */

import { promises as fs } from 'fs';
import path from 'path';
import { glob } from 'glob';

export class FileUtils {
  /**
   * Check if file exists
   */
  static async exists(filePath) {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Read file content
   */
  static async readFile(filePath) {
    try {
      return await fs.readFile(filePath, 'utf8');
    } catch (error) {
      throw new Error(`Failed to read file ${filePath}: ${error.message}`);
    }
  }

  /**
   * Write file content
   */
  static async writeFile(filePath, content) {
    try {
      // Ensure directory exists
      const dir = path.dirname(filePath);
      await fs.mkdir(dir, { recursive: true });

      await fs.writeFile(filePath, content, 'utf8');
      return true;
    } catch (error) {
      throw new Error(`Failed to write file ${filePath}: ${error.message}`);
    }
  }

  /**
   * Find files matching a pattern
   */
  static async findFiles(pattern, options = {}) {
    const defaultOptions = {
      cwd: process.cwd(),
      ignore: ['node_modules/**', '.git/**', '**/.DS_Store'],
      ...options
    };

    try {
      return await glob(pattern, defaultOptions);
    } catch (error) {
      throw new Error(`Failed to find files: ${error.message}`);
    }
  }

  /**
   * Get file stats
   */
  static async getStats(filePath) {
    try {
      const stats = await fs.stat(filePath);
      return {
        size: stats.size,
        created: stats.birthtime,
        modified: stats.mtime,
        isDirectory: stats.isDirectory(),
        isFile: stats.isFile()
      };
    } catch (error) {
      throw new Error(`Failed to get file stats for ${filePath}: ${error.message}`);
    }
  }

  /**
   * Create directory if it doesn't exist
   */
  static async ensureDirectory(dirPath) {
    try {
      await fs.mkdir(dirPath, { recursive: true });
      return true;
    } catch (error) {
      throw new Error(`Failed to create directory ${dirPath}: ${error.message}`);
    }
  }

  /**
   * Get relative path from current working directory
   */
  static getRelativePath(filePath) {
    return path.relative(process.cwd(), filePath);
  }

  /**
   * Get file extension
   */
  static getExtension(filePath) {
    return path.extname(filePath).toLowerCase();
  }

  /**
   * Get file name without extension
   */
  static getBaseName(filePath) {
    return path.basename(filePath, path.extname(filePath));
  }
}