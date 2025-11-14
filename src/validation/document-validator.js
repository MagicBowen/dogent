/**
 * Document Validator
 *
 * Validates document content for accuracy, consistency, and quality.
 * Performs fact-checking, grammar checking, and style validation.
 */

export class DocumentValidator {
  constructor() {
    this.validationRules = {
      grammar: true,
      spelling: true,
      consistency: true,
      facts: true,
      structure: true,
      readability: true
    };
  }

  /**
   * Validate document content
   */
  async validate(content, validationPlan = {}) {
    console.log('🔍 Validating document content...');

    const results = {
      overall: true,
      score: 0,
      issues: [],
      suggestions: [],
      checks: {}
    };

    try {
      // Apply validation rules based on plan
      const rules = { ...this.validationRules, ...validationPlan };

      for (const [rule, enabled] of Object.entries(rules)) {
        if (enabled) {
          const result = await this.performValidation(rule, content);
          results.checks[rule] = result;

          // Collect issues and suggestions
          if (!result.passed) {
            results.overall = false;
            results.issues.push(...result.issues);
          }

          results.suggestions.push(...result.suggestions);
        }
      }

      // Calculate overall score
      results.score = this.calculateScore(results.checks);

      console.log(`✅ Validation completed. Score: ${results.score}/100`);

      return results;

    } catch (error) {
      throw new Error(`Validation failed: ${error.message}`);
    }
  }

  /**
   * Perform specific validation rule
   */
  async performValidation(rule, content) {
    switch (rule) {
      case 'grammar':
        return await this.checkGrammar(content);
      case 'spelling':
        return await this.checkSpelling(content);
      case 'consistency':
        return await this.checkConsistency(content);
      case 'facts':
        return await this.checkFacts(content);
      case 'structure':
        return await this.checkStructure(content);
      case 'readability':
        return await this.checkReadability(content);
      default:
        return { passed: true, issues: [], suggestions: [] };
    }
  }

  /**
   * Check grammar
   */
  async checkGrammar(content) {
    const issues = [];
    const suggestions = [];

    // Simulate grammar checking
    // In real implementation, would use grammar checking APIs

    const grammarPatterns = [
      { pattern: /\b(a)\s+([aeiou])/gi, message: 'Use "an" before vowels' },
      { pattern: /\b(it\'s)\s+(not|never)\b/gi, message: 'Use "its" for possessive, "it\'s" for "it is"' },
      { pattern: /\b(there|their|they\'re)\b/gi, message: 'Check usage of there/their/they\'re' }
    ];

    for (const { pattern, message } of grammarPatterns) {
      const matches = content.match(pattern);
      if (matches) {
        issues.push({
          type: 'grammar',
          message: message,
          occurrences: matches.length,
          severity: 'medium'
        });
      }
    }

    suggestions.push('Consider using a grammar checker like Grammarly for thorough review');

    return {
      passed: issues.length === 0,
      issues,
      suggestions
    };
  }

  /**
   * Check spelling
   */
  async checkSpelling(content) {
    const issues = [];
    const suggestions = [];

    // Simulate spell checking
    const commonMisspellings = {
      'occured': 'occurred',
      'seperate': 'separate',
      'recieve': 'receive',
      'definately': 'definitely',
      'neccessary': 'necessary',
      'accomodate': 'accommodate'
    };

    for (const [incorrect, correct] of Object.entries(commonMisspellings)) {
      const regex = new RegExp(`\\b${incorrect}\\b`, 'gi');
      const matches = content.match(regex);

      if (matches) {
        issues.push({
          type: 'spelling',
          message: `Misspelled word: "${incorrect}" should be "${correct}"`,
          occurrences: matches.length,
          severity: 'low'
        });
      }
    }

    suggestions.push('Run spell check with dictionary specific to your domain');

    return {
      passed: issues.length === 0,
      issues,
      suggestions
    };
  }

  /**
   * Check consistency
   */
  async checkConsistency(content) {
    const issues = [];
    const suggestions = [];

    // Check term consistency
    const terms = this.extractTerms(content);
    const inconsistentTerms = this.findInconsistentTerms(terms);

    for (const term of inconsistentTerms) {
      issues.push({
        type: 'consistency',
        message: `Inconsistent term usage: "${term.variants.join('", "')}"`,
        occurrences: term.count,
        severity: 'medium'
      });
    }

    // Check heading consistency
    const headings = this.extractHeadings(content);
    const headingIssues = this.checkHeadingConsistency(headings);

    issues.push(...headingIssues);

    // Check formatting consistency
    const formattingIssues = this.checkFormattingConsistency(content);
    issues.push(...formattingIssues);

    if (issues.length === 0) {
      suggestions.push('Document shows good consistency throughout');
    }

    return {
      passed: issues.length === 0,
      issues,
      suggestions
    };
  }

  /**
   * Extract terms from content
   */
  extractTerms(content) {
    const words = content.toLowerCase().match(/\b[a-z]+\b/g) || [];
    const termCount = {};

    words.forEach(word => {
      if (word.length > 6) { // Focus on longer terms
        termCount[word] = (termCount[word] || 0) + 1;
      }
    });

    return termCount;
  }

  /**
   * Find potentially inconsistent terms
   */
  findInconsistentTerms(terms) {
    const inconsistent = [];

    // Simple similarity check
    const termList = Object.keys(terms);

    for (let i = 0; i < termList.length; i++) {
      for (let j = i + 1; j < termList.length; j++) {
        const term1 = termList[i];
        const term2 = termList[j];

        if (this.areTermsSimilar(term1, term2) && Math.abs(term1.length - term2.length) <= 2) {
          inconsistent.push({
            variants: [term1, term2],
            count: terms[term1] + terms[term2]
          });
        }
      }
    }

    return inconsistent;
  }

  /**
   * Check if terms are similar (possible variants)
   */
  areTermsSimilar(term1, term2) {
    const similarity = this.calculateSimilarity(term1, term2);
    return similarity > 0.7 && similarity < 1.0;
  }

  /**
   * Calculate similarity between two strings
   */
  calculateSimilarity(str1, str2) {
    const longer = str1.length > str2.length ? str1 : str2;
    const shorter = str1.length > str2.length ? str2 : str1;

    if (longer.length === 0) return 1.0;

    const editDistance = this.levenshteinDistance(longer, shorter);
    return (longer.length - editDistance) / longer.length;
  }

  /**
   * Calculate Levenshtein distance
   */
  levenshteinDistance(str1, str2) {
    const matrix = [];

    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }

    return matrix[str2.length][str1.length];
  }

  /**
   * Extract headings from content
   */
  extractHeadings(content) {
    const headingRegex = /^(#{1,6})\s+(.+)$/gm;
    const headings = [];
    let match;

    while ((match = headingRegex.exec(content)) !== null) {
      headings.push({
        level: match[1].length,
        text: match[2].trim()
      });
    }

    return headings;
  }

  /**
   * Check heading consistency
   */
  checkHeadingConsistency(headings) {
    const issues = [];

    // Check for skipped heading levels
    for (let i = 1; i < headings.length; i++) {
      const current = headings[i];
      const previous = headings[i - 1];

      if (current.level > previous.level + 1) {
        issues.push({
          type: 'structure',
          message: `Skipped heading level: from H${previous.level} to H${current.level}`,
          severity: 'medium'
        });
      }
    }

    return issues;
  }

  /**
   * Check formatting consistency
   */
  checkFormattingConsistency(content) {
    const issues = [];

    // Check for consistent bullet points
    const bulletPatterns = [
      /^-\s+/gm,
      /^\*\s+/gm,
      /^\+\s+/gm
    ];

    const bulletCounts = bulletPatterns.map(pattern => (content.match(pattern) || []).length);
    const totalBullets = bulletCounts.reduce((sum, count) => sum + count, 0);

    if (totalBullets > 0) {
      const dominantPattern = bulletCounts.indexOf(Math.max(...bulletCounts));
      const otherPatterns = bulletCounts.filter((_, index) => index !== dominantPattern).reduce((sum, count) => sum + count, 0);

      if (otherPatterns > totalBullets * 0.1) { // More than 10% inconsistent
        issues.push({
          type: 'formatting',
          message: 'Inconsistent bullet point formatting detected',
          severity: 'low'
        });
      }
    }

    return issues;
  }

  /**
   * Check facts (simulated)
   */
  async checkFacts(content) {
    const issues = [];
    const suggestions = [];

    // Look for statements that might need verification
    const factPatterns = [
      /\b(\d{4})\b/g, // Years
      /\b(\d+)%\b/g, // Percentages
      /\b(\$?\d+(?:,\d{3})*(?:\.\d{2})?)\b/g, // Numbers/currency
      /\b(according to|research shows|studies indicate)\b/gi // Research claims
    ];

    for (const pattern of factPatterns) {
      const matches = content.match(pattern);
      if (matches && matches.length > 5) { // If many matches, flag for review
        suggestions.push(`Consider verifying ${matches.length} factual statements`);
      }
    }

    // Look for potentially outdated information
    const yearRegex = /\b(19|20)\d{2}\b/g;
    const years = content.match(yearRegex) || [];
    const currentYear = new Date().getFullYear();
    const oldYears = years.filter(year => parseInt(year) < currentYear - 5);

    if (oldYears.length > 0) {
      suggestions.push(`Some references are from ${Math.min(...oldYears)} - consider updating`);
    }

    return {
      passed: issues.length === 0,
      issues,
      suggestions
    };
  }

  /**
   * Check document structure
   */
  async checkStructure(content) {
    const issues = [];
    const suggestions = [];

    // Check for basic structure
    const hasTitle = /^#\s+.+$/m.test(content);
    const hasSections = /^#{2,}\s+.+$/m.test(content);
    const hasConclusion = /\b(conclusion|summary|final|wrap.?up)\b/i.test(content);

    if (!hasTitle) {
      issues.push({
        type: 'structure',
        message: 'Document missing main title',
        severity: 'high'
      });
    }

    if (!hasSections) {
      suggestions.push('Consider adding section headings for better organization');
    }

    if (!hasConclusion && content.length > 1000) {
      suggestions.push('Consider adding a conclusion section');
    }

    // Check paragraph length
    const paragraphs = content.split(/\n\n+/);
    const longParagraphs = paragraphs.filter(p => p.length > 500);

    if (longParagraphs.length > 0) {
      suggestions.push(`${longParagraphs.length} paragraphs are quite long - consider breaking them up`);
    }

    return {
      passed: issues.length === 0,
      issues,
      suggestions
    };
  }

  /**
   * Check readability
   */
  async checkReadability(content) {
    const issues = [];
    const suggestions = [];

    // Calculate basic readability metrics
    const words = content.split(/\s+/).length;
    const sentences = content.split(/[.!?]+/).length;
    const avgWordsPerSentence = words / sentences;

    // Check sentence length
    if (avgWordsPerSentence > 25) {
      suggestions.push('Average sentence length is quite long - consider shorter sentences');
    } else if (avgWordsPerSentence < 10) {
      suggestions.push('Average sentence length is quite short - consider more complex sentences');
    }

    // Check for passive voice (simple detection)
    const passivePatterns = [
      /\b(is|are|was|were|be|been|being)\s+\w+ed\b/gi,
      /\bby\s+\w+ing\b/gi
    ];

    let passiveCount = 0;
    for (const pattern of passivePatterns) {
      passiveCount += (content.match(pattern) || []).length;
    }

    const passivePercentage = (passiveCount / sentences) * 100;
    if (passivePercentage > 30) {
      suggestions.push(`High passive voice usage (${passivePercentage.toFixed(1)}%) - consider active voice`);
    }

    return {
      passed: issues.length === 0,
      issues,
      suggestions
    };
  }

  /**
   * Calculate overall validation score
   */
  calculateScore(checks) {
    const weights = {
      grammar: 20,
      spelling: 15,
      consistency: 20,
      facts: 20,
      structure: 15,
      readability: 10
    };

    let totalScore = 0;
    let totalWeight = 0;

    for (const [check, result] of Object.entries(checks)) {
      const weight = weights[check] || 10;
      totalWeight += weight;

      if (result.passed) {
        totalScore += weight;
      } else {
        // Partial score based on number of issues
        const issuePenalty = Math.min(result.issues.length * 2, weight);
        totalScore += Math.max(0, weight - issuePenalty);
      }
    }

    return totalWeight > 0 ? Math.round((totalScore / totalWeight) * 100) : 0;
  }
}