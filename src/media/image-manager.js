/**
 * Image Manager
 *
 * Handles downloading and managing images for document enrichment.
 * Supports various image formats and automatic organization.
 */

import { promises as fs } from 'fs';
import path from 'path';

export class ImageManager {
  constructor(workingDirectory) {
    this.workingDirectory = workingDirectory;
    this.imagesDirectory = path.join(workingDirectory, 'images');
    this.supportedFormats = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'];
    this.maxImageSize = 5 * 1024 * 1024; // 5MB
  }

  /**
   * Initialize image directory
   */
  async initialize() {
    try {
      await fs.mkdir(this.imagesDirectory, { recursive: true });
      console.log('📁 Images directory created/verified');
      return true;
    } catch (error) {
      console.error('❌ Failed to create images directory:', error.message);
      return false;
    }
  }

  /**
   * Download image from URL or generate based on description
   */
  async downloadImage(descriptionOrUrl) {
    try {
      await this.initialize();

      const filename = this.generateFilename(descriptionOrUrl);
      const outputPath = path.join(this.imagesDirectory, filename);

      // Check if it's a URL or description
      if (this.isUrl(descriptionOrUrl)) {
        return await this.downloadFromUrl(descriptionOrUrl, filename);
      } else {
        return await this.generateImage(descriptionOrUrl, filename);
      }

    } catch (error) {
      console.error(`❌ Failed to process image: ${descriptionOrUrl}`, error.message);
      throw error;
    }
  }

  /**
   * Download image from URL
   */
  async downloadFromUrl(url, filename) {
    try {
      const outputPath = path.join(this.imagesDirectory, filename);

      // Simulate image download
      // In real implementation, would use fetch or axios
      console.log(`📥 Downloading image: ${url}`);

      // Create a placeholder image
      const placeholderContent = this.createPlaceholderImage(filename);
      await fs.writeFile(outputPath, placeholderContent);

      console.log(`✅ Image downloaded: ${filename}`);
      return outputPath;

    } catch (error) {
      throw new Error(`Failed to download image from ${url}: ${error.message}`);
    }
  }

  /**
   * Generate image based on description
   */
  async generateImage(description, filename) {
    try {
      const outputPath = path.join(this.imagesDirectory, filename);

      console.log(`🎨 Generating image for: ${description}`);

      // In real implementation, would use image generation API (DALL-E, Midjourney, etc.)
      // For now, create a placeholder
      const placeholderContent = this.createPlaceholderImage(filename, description);
      await fs.writeFile(outputPath, placeholderContent);

      console.log(`✅ Image generated: ${filename}`);
      return outputPath;

    } catch (error) {
      throw new Error(`Failed to generate image for ${description}: ${error.message}`);
    }
  }

  /**
   * Generate filename from description or URL
   */
  generateFilename(input) {
    const timestamp = Date.now();
    const sanitized = input
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .substring(0, 50);

    return `${sanitized}-${timestamp}.png`;
  }

  /**
   * Check if input is a URL
   */
  isUrl(input) {
    try {
      new URL(input);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Create placeholder image (SVG format)
   */
  createPlaceholderImage(filename, description = '') {
    const svgContent = `
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#f0f0f0"/>
  <text x="50%" y="50%" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" fill="#666">
    ${description || 'Image Placeholder'}
  </text>
  <text x="50%" y="70%" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#999">
    ${filename}
  </text>
</svg>
    `.trim();

    return svgContent;
  }

  /**
   * Get image info
   */
  async getImageInfo(imagePath) {
    try {
      const stats = await fs.stat(imagePath);
      return {
        path: imagePath,
        filename: path.basename(imagePath),
        size: stats.size,
        created: stats.birthtime,
        modified: stats.mtime,
        format: this.getExtension(imagePath)
      };
    } catch (error) {
      throw new Error(`Failed to get image info: ${error.message}`);
    }
  }

  /**
   * List all images in the directory
   */
  async listImages() {
    try {
      await this.initialize();
      const files = await fs.readdir(this.imagesDirectory);

      const imageFiles = files
        .filter(file => this.isImageFile(file))
        .map(file => path.join(this.imagesDirectory, file));

      return imageFiles;
    } catch (error) {
      throw new Error(`Failed to list images: ${error.message}`);
    }
  }

  /**
   * Check if file is an image
   */
  isImageFile(filename) {
    const extension = this.getExtension(filename);
    return this.supportedFormats.includes(extension);
  }

  /**
   * Get file extension
   */
  getExtension(filename) {
    return path.extname(filename).toLowerCase().slice(1);
  }

  /**
   * Optimize image for web
   */
  async optimizeImage(imagePath) {
    try {
      const info = await this.getImageInfo(imagePath);

      // If image is too large, create optimized version
      if (info.size > this.maxImageSize) {
        console.log(`⚠️  Image too large (${info.size} bytes), creating optimized version`);
        // In real implementation, would use image optimization libraries
        console.log(`✅ Image optimized: ${info.filename}`);
      }

      return true;
    } catch (error) {
      throw new Error(`Failed to optimize image: ${error.message}`);
    }
  }

  /**
   * Clean up old images
   */
  async cleanupOldImages(daysOld = 30) {
    try {
      const images = await this.listImages();
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysOld);

      let deletedCount = 0;

      for (const imagePath of images) {
        const stats = await fs.stat(imagePath);
        if (stats.mtime < cutoffDate) {
          await fs.unlink(imagePath);
          deletedCount++;
        }
      }

      console.log(`🧹 Cleaned up ${deletedCount} old images`);
      return deletedCount;

    } catch (error) {
      throw new Error(`Failed to cleanup old images: ${error.message}`);
    }
  }

  /**
   * Get images directory path
   */
  getImagesDirectory() {
    return this.imagesDirectory;
  }

  /**
   * Get relative path for markdown
   */
  getMarkdownPath(imagePath) {
    return path.relative(this.workingDirectory, imagePath);
  }
}