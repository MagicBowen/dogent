/**
 * Memory Manager
 *
 * Manages temporary notes and memory storage for the document writing process.
 * Handles .memory.md file for storing thoughts, ideas, and temporary information.
 */

import { promises as fs } from 'fs';
import path from 'path';

export class MemoryManager {
  constructor(workingDirectory) {
    this.workingDirectory = workingDirectory;
    this.memoryPath = path.join(workingDirectory, '.memory.md');
    this.notes = [];
    this.categories = {
      research: '📚 Research Notes',
      ideas: '💡 Ideas',
      todos: '✅ Tasks',
      sources: '🔗 Sources',
      thoughts: '💭 Thoughts',
      temp: '📝 Temporary Notes'
    };
  }

  /**
   * Initialize memory file
   */
  async initialize() {
    try {
      // Create memory file if it doesn't exist
      const exists = await this.fileExists(this.memoryPath);
      if (!exists) {
        await this.createMemoryFile();
      }

      // Load existing notes
      await this.loadNotes();

      console.log('🧠 Memory manager initialized');
      return true;
    } catch (error) {
      console.error('❌ Failed to initialize memory manager:', error.message);
      return false;
    }
  }

  /**
   * Create initial memory file
   */
  async createMemoryFile() {
    const template = `# Document Writing Memory

This file contains temporary notes, thoughts, and research information for the current document writing session.

## Categories

${Object.values(this.categories).map(cat => `- ${cat}`).join('\n')}

---

*This file is automatically managed by the Document Writing Agent*
*Last updated: ${new Date().toISOString()}*
`;

    await fs.writeFile(this.memoryPath, template, 'utf8');
  }

  /**
   * Add a note to memory
   */
  async addNote(title, content, category = 'temp') {
    try {
      await this.initialize();

      const note = {
        id: this.generateNoteId(),
        title: title,
        content: content,
        category: category,
        timestamp: new Date().toISOString(),
        tags: this.extractTags(content)
      };

      this.notes.push(note);
      await this.appendNoteToFile(note);

      console.log(`💭 Note added: ${title}`);
      return note;

    } catch (error) {
      throw new Error(`Failed to add note: ${error.message}`);
    }
  }

  /**
   * Generate unique note ID
   */
  generateNoteId() {
    return `note_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
  }

  /**
   * Extract tags from content
   */
  extractTags(content) {
    const tagPattern = /#(\w+)/g;
    const tags = [];
    let match;

    while ((match = tagPattern.exec(content)) !== null) {
      tags.push(match[1]);
    }

    return tags;
  }

  /**
   * Append note to memory file
   */
  async appendNoteToFile(note) {
    const categoryHeader = this.categories[note.category] || '📝 Notes';
    const noteContent = `### ${note.title}

**Category:** ${categoryHeader}
**Time:** ${new Date(note.timestamp).toLocaleString()}
**Tags:** ${note.tags.length > 0 ? note.tags.map(tag => `#${tag}`).join(' ') : 'none'}

${note.content}

---

`;

    await fs.appendFile(this.memoryPath, noteContent, 'utf8');
  }

  /**
   * Load existing notes from memory file
   */
  async loadNotes() {
    try {
      const content = await fs.readFile(this.memoryPath, 'utf8');
      // Parse existing notes (simplified parsing)
      // In a more complex implementation, would use proper markdown parsing

      this.notes = []; // Reset notes
      console.log(`📖 Loaded ${this.notes.length} notes from memory`);

    } catch (error) {
      console.warn('⚠️  Could not load existing notes:', error.message);
      this.notes = [];
    }
  }

  /**
   * Get notes by category
   */
  getNotesByCategory(category) {
    return this.notes.filter(note => note.category === category);
  }

  /**
   * Get notes by tags
   */
  getNotesByTags(tags) {
    return this.notes.filter(note =>
      tags.some(tag => note.tags.includes(tag))
    );
  }

  /**
   * Search notes
   */
  searchNotes(query) {
    const lowerQuery = query.toLowerCase();

    return this.notes.filter(note =>
      note.title.toLowerCase().includes(lowerQuery) ||
      note.content.toLowerCase().includes(lowerQuery) ||
      note.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
    );
  }

  /**
   * Get recent notes
   */
  getRecentNotes(limit = 10) {
    return this.notes
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, limit);
  }

  /**
   * Delete note by ID
   */
  async deleteNote(noteId) {
    try {
      const index = this.notes.findIndex(note => note.id === noteId);

      if (index !== -1) {
        this.notes.splice(index, 1);
        await this.rebuildMemoryFile();
        console.log(`🗑️  Note deleted: ${noteId}`);
        return true;
      }

      return false;
    } catch (error) {
      throw new Error(`Failed to delete note: ${error.message}`);
    }
  }

  /**
   * Rebuild memory file from notes array
   */
  async rebuildMemoryFile() {
    const template = `# Document Writing Memory

This file contains temporary notes, thoughts, and research information for the current document writing session.

## Categories

${Object.values(this.categories).map(cat => `- ${cat}`).join('\n')}

---

`;

    let content = template;

    // Group notes by category
    const groupedNotes = {};
    this.notes.forEach(note => {
      if (!groupedNotes[note.category]) {
        groupedNotes[note.category] = [];
      }
      groupedNotes[note.category].push(note);
    });

    // Add notes by category
    for (const [category, notes] of Object.entries(groupedNotes)) {
      if (notes.length > 0) {
        const categoryHeader = this.categories[category] || '📝 Notes';
        content += `\n## ${categoryHeader}\n\n`;

        notes.forEach(note => {
          content += `### ${note.title}

**Time:** ${new Date(note.timestamp).toLocaleString()}
**Tags:** ${note.tags.length > 0 ? note.tags.map(tag => `#${tag}`).join(' ') : 'none'}

${note.content}

---

`;
        });
      }
    }

    content += `\n*Last updated: ${new Date().toISOString()}*\n`;

    await fs.writeFile(this.memoryPath, content, 'utf8');
  }

  /**
   * Clear memory file
   */
  async clearMemory() {
    try {
      await this.createMemoryFile();
      this.notes = [];
      console.log('🧹 Memory cleared');
      return true;
    } catch (error) {
      throw new Error(`Failed to clear memory: ${error.message}`);
    }
  }

  /**
   * Export notes
   */
  async exportNotes(format = 'markdown') {
    switch (format) {
      case 'markdown':
        return this.exportAsMarkdown();
      case 'json':
        return this.exportAsJSON();
      case 'txt':
        return this.exportAsText();
      default:
        return this.exportAsMarkdown();
    }
  }

  /**
   * Export notes as markdown
   */
  async exportAsMarkdown() {
    const content = await fs.readFile(this.memoryPath, 'utf8');
    return content;
  }

  /**
   * Export notes as JSON
   */
  exportAsJSON() {
    return JSON.stringify(this.notes, null, 2);
  }

  /**
   * Export notes as plain text
   */
  exportAsText() {
    return this.notes.map(note =>
      `${note.title}\n${'-'.repeat(note.title.length)}\n${note.content}\n\nTags: ${note.tags.join(', ')}\n`
    ).join('\n');
  }

  /**
   * Get memory statistics
   */
  getStatistics() {
    const categoryStats = {};
    const tagStats = {};

    this.notes.forEach(note => {
      // Category statistics
      categoryStats[note.category] = (categoryStats[note.category] || 0) + 1;

      // Tag statistics
      note.tags.forEach(tag => {
        tagStats[tag] = (tagStats[tag] || 0) + 1;
      });
    });

    return {
      totalNotes: this.notes.length,
      categoryStats,
      tagStats,
      latestNote: this.notes.length > 0 ?
        new Date(Math.max(...this.notes.map(n => new Date(n.timestamp)))) : null
    };
  }

  /**
   * Add research note
   */
  async addResearchNote(topic, findings, sources = []) {
    const content = `**Topic:** ${topic}

**Findings:**
${findings}

**Sources:**
${sources.map(source => `- ${source}`).join('\n')}

**Next Steps:**
- [ ] Verify key findings
- [ ] Cross-reference with other sources
- [ ] Incorporate into document
`;

    return await this.addNote(`Research: ${topic}`, content, 'research');
  }

  /**
   * Add idea note
   */
  async addIdea(title, description, category = 'ideas') {
    const content = `**Description:**
${description}

**Potential Sections:**
- Introduction hook
- Supporting arguments
- Examples and case studies
- Conclusion points

**Related Topics:**
- Consider exploring related concepts
- Look for supporting evidence
- Plan visual elements
`;

    return await this.addNote(title, content, category);
  }

  /**
   * Add todo note
   */
  async addTodo(task, priority = 'medium') {
    const priorityIndicators = {
      high: '🔴',
      medium: '🟡',
      low: '🟢'
    };

    const content = `**Status:** Pending
**Priority:** ${priorityIndicators[priority] || priorityIndicators.medium} ${priority}

**Description:**
${task}

**Subtasks:**
- [ ] Break down into smaller steps
- [ ] Gather necessary resources
- [ ] Complete the task
- [ ] Review and refine
`;

    return await this.addNote(`TODO: ${task}`, content, 'todos');
  }

  /**
   * Add source note
   */
  async addSource(title, url, summary) {
    const content = `**URL:** ${url}

**Summary:**
${summary}

**Key Points:**
- Extract main arguments
- Note supporting data
- Identify relevance to document

**Citation Info:**
- Author: [To be determined]
- Publication date: [To be determined]
- Publisher: [To be determined]
`;

    return await this.addNote(`Source: ${title}`, content, 'sources');
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