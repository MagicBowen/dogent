/**
 * Citation Manager
 *
 * Handles citation creation, formatting, and management for document references.
 * Supports multiple citation styles and automatic source validation.
 */

export class CitationManager {
  constructor() {
    this.citations = [];
    this.supportedStyles = ['APA', 'MLA', 'Chicago', 'IEEE', 'Harvard'];
    this.defaultStyle = 'APA';
  }

  /**
   * Create a citation from a source
   */
  async createCitation(source, style = this.defaultStyle) {
    try {
      const citation = {
        id: this.generateCitationId(),
        source: source,
        style: style,
        createdAt: new Date().toISOString(),
        formatted: this.formatCitation(source, style),
        metadata: this.extractMetadata(source)
      };

      this.citations.push(citation);
      console.log(`📚 Citation created: ${source}`);

      return citation;
    } catch (error) {
      throw new Error(`Failed to create citation for ${source}: ${error.message}`);
    }
  }

  /**
   * Generate unique citation ID
   */
  generateCitationId() {
    return `cite_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Format citation according to style
   */
  formatCitation(source, style) {
    const metadata = this.extractMetadata(source);

    switch (style) {
      case 'APA':
        return this.formatAPA(metadata);
      case 'MLA':
        return this.formatMLA(metadata);
      case 'Chicago':
        return this.formatChicago(metadata);
      case 'IEEE':
        return this.formatIEEE(metadata);
      case 'Harvard':
        return this.formatHarvard(metadata);
      default:
        return this.formatAPA(metadata);
    }
  }

  /**
   * Extract metadata from source
   */
  extractMetadata(source) {
    // Try to parse as URL first
    if (this.isValidUrl(source)) {
      return this.extractUrlMetadata(source);
    }

    // Try to parse as academic reference
    if (this.looksLikeAcademicReference(source)) {
      return this.extractAcademicMetadata(source);
    }

    // Default metadata
    return {
      type: 'general',
      title: source,
      authors: ['Unknown'],
      year: new Date().getFullYear().toString(),
      url: this.isValidUrl(source) ? source : null
    };
  }

  /**
   * Extract metadata from URL
   */
  extractUrlMetadata(url) {
    try {
      const urlObj = new URL(url);
      const hostname = urlObj.hostname;

      return {
        type: 'web',
        title: this.extractTitleFromUrl(url),
        authors: [this.extractAuthorFromUrl(url)],
        year: new Date().getFullYear().toString(),
        website: hostname,
        url: url,
        accessDate: new Date().toISOString().split('T')[0]
      };
    } catch (error) {
      return {
        type: 'web',
        title: url,
        authors: ['Unknown'],
        year: new Date().getFullYear().toString(),
        url: url,
        accessDate: new Date().toISOString().split('T')[0]
      };
    }
  }

  /**
   * Extract title from URL (simulated)
   */
  extractTitleFromUrl(url) {
    const pathname = new URL(url).pathname;
    const segments = pathname.split('/').filter(Boolean);
    const lastSegment = segments[segments.length - 1];

    // Convert URL segment to readable title
    return lastSegment
      .replace(/-/g, ' ')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  /**
   * Extract author from URL (simulated)
   */
  extractAuthorFromUrl(url) {
    const hostname = new URL(url).hostname;

    // Map common domains to authors
    const domainAuthors = {
      'github.com': 'GitHub Community',
      'stackoverflow.com': 'Stack Overflow Community',
      'medium.com': 'Medium Author',
      'dev.to': 'DEV Community',
      'example.com': 'Example Author'
    };

    return domainAuthors[hostname] || 'Web Author';
  }

  /**
   * Extract metadata from academic reference
   */
  extractAcademicReference(reference) {
    // Simple parsing for academic references
    // In real implementation, would use more sophisticated parsing

    const yearMatch = reference.match(/\b(19|20)\d{2}\b/);
    const year = yearMatch ? yearMatch[0] : new Date().getFullYear().toString();

    return {
      type: 'academic',
      title: reference,
      authors: ['Academic Author'],
      year: year,
      journal: 'Academic Journal',
      doi: null
    };
  }

  /**
   * Check if string is a valid URL
   */
  isValidUrl(string) {
    try {
      new URL(string);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Check if string looks like an academic reference
   */
  looksLikeAcademicReference(reference) {
    const academicKeywords = [
      'journal', 'conference', 'proceedings', 'university', 'press',
      'doi:', 'isbn:', 'vol.', 'pp.', 'et al.'
    ];

    return academicKeywords.some(keyword =>
      reference.toLowerCase().includes(keyword)
    );
  }

  /**
   * Format citation in APA style
   */
  formatAPA(metadata) {
    if (metadata.type === 'web') {
      return `${metadata.authors[0]} (${metadata.year}). *${metadata.title}*. Retrieved ${metadata.accessDate}, from ${metadata.url}`;
    } else if (metadata.type === 'academic') {
      return `${metadata.authors[0]} (${metadata.year}). ${metadata.title}. *${metadata.journal}*.`;
    } else {
      return `${metadata.authors[0]} (${metadata.year}). ${metadata.title}.`;
    }
  }

  /**
   * Format citation in MLA style
   */
  formatMLA(metadata) {
    if (metadata.type === 'web') {
      return `${metadata.authors[0]}. "${metadata.title}." *${metadata.website}*, ${metadata.accessDate}.`;
    } else {
      return `${metadata.authors[0]}. "${metadata.title}." ${metadata.journal || 'Publication'}, ${metadata.year}.`;
    }
  }

  /**
   * Format citation in Chicago style
   */
  formatChicago(metadata) {
    if (metadata.type === 'web') {
      return `${metadata.authors[0]}. "${metadata.title}." Last modified ${metadata.accessDate}. ${metadata.url}.`;
    } else {
      return `${metadata.authors[0]}. "${metadata.title}." ${metadata.journal || 'Publication'} (${metadata.year}).`;
    }
  }

  /**
   * Format citation in IEEE style
   */
  formatIEEE(metadata) {
    if (metadata.type === 'web') {
      return `[1] ${metadata.authors[0]}, "${metadata.title}," ${metadata.website}, ${metadata.accessDate}. [Online]. Available: ${metadata.url}`;
    } else {
      return `[1] ${metadata.authors[0]}, "${metadata.title}," ${metadata.journal || 'Publication'}, ${metadata.year}.`;
    }
  }

  /**
   * Format citation in Harvard style
   */
  formatHarvard(metadata) {
    if (metadata.type === 'web') {
      return `${metadata.authors[0]} (${metadata.year}) '${metadata.title}', ${metadata.website}, [online] ${metadata.url}.`;
    } else {
      return `${metadata.authors[0]} (${metadata.year}) '${metadata.title}', ${metadata.journal || 'Publication'}.`;
    }
  }

  /**
   * Get all citations
   */
  getAllCitations() {
    return this.citations;
  }

  /**
   * Get citation by ID
   */
  getCitation(id) {
    return this.citations.find(citation => citation.id === id);
  }

  /**
   * Update citation style for all citations
   */
  updateCitationStyle(newStyle) {
    this.citations.forEach(citation => {
      citation.style = newStyle;
      citation.formatted = this.formatCitation(citation.source, newStyle);
    });
  }

  /**
   * Generate bibliography
   */
  generateBibliography(style = this.defaultStyle) {
    const styleCitations = this.citations.filter(c => c.style === style);

    if (styleCitations.length === 0) {
      return 'No citations available.';
    }

    return styleCitations
      .sort((a, b) => a.source.localeCompare(b.source))
      .map((citation, index) => `${index + 1}. ${citation.formatted}`)
      .join('\n');
  }

  /**
   * Validate citation
   */
  validateCitation(citation) {
    const required = ['id', 'source', 'style', 'formatted', 'createdAt'];
    const missing = required.filter(field => !citation[field]);

    if (missing.length > 0) {
      throw new Error(`Missing required citation fields: ${missing.join(', ')}`);
    }

    if (!this.supportedStyles.includes(citation.style)) {
      throw new Error(`Unsupported citation style: ${citation.style}`);
    }

    return true;
  }

  /**
   * Export citations to different formats
   */
  exportCitations(format = 'json') {
    switch (format) {
      case 'json':
        return JSON.stringify(this.citations, null, 2);
      case 'bibtex':
        return this.exportToBibTeX();
      case 'csv':
        return this.exportToCSV();
      default:
        return this.exportCitations('json');
    }
  }

  /**
   * Export citations to BibTeX format
   */
  exportToBibTeX() {
    return this.citations
      .map(citation => {
        const meta = citation.metadata;
        return `@article{${citation.id},
  title={${meta.title}},
  author={${meta.authors.join(' and ')}},
  year={${meta.year}},
  url={${meta.url || ''}}
}`;
      })
      .join('\n\n');
  }

  /**
   * Export citations to CSV format
   */
  exportToCSV() {
    const headers = ['ID', 'Source', 'Style', 'Formatted', 'Created At'];
    const rows = this.citations.map(citation => [
      citation.id,
      citation.source,
      citation.style,
      citation.formatted.replace(/"/g, '""'),
      citation.createdAt
    ]);

    return [headers, ...rows]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n');
  }

  /**
   * Clear all citations
   */
  clearCitations() {
    this.citations = [];
    console.log('🧹 All citations cleared');
  }

  /**
   * Get citation statistics
   */
  getStatistics() {
    const styleCount = {};
    this.citations.forEach(citation => {
      styleCount[citation.style] = (styleCount[citation.style] || 0) + 1;
    });

    return {
      total: this.citations.length,
      styles: styleCount,
      averageLength: this.citations.reduce((sum, c) => sum + c.source.length, 0) / this.citations.length
    };
  }
}