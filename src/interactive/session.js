/**
 * Interactive Session Manager
 *
 * Handles the main interactive CLI session for document writing.
 * Supports file references, todo list display, and Claude Code-like interaction.
 */

import readline from 'readline';
import chalk from 'chalk';
import inquirer from 'inquirer';
import { promises as fs } from 'fs';
import path from 'path';
import { homedir } from 'os';
import { glob } from 'glob';
import { DocumentWritingAgent } from '../agent/document-agent.js';
import { ConfigManager } from '../config/config-manager.js';
import { FileUtils } from '../utils/file-utils.js';

export class InteractiveSession {
  constructor() {
    this.rl = null;
    this.currentDirectory = process.cwd();
    this.sessionId = Date.now().toString(36);
    this.thinkingEnabled = true;
    this.fileContext = new Set();
    this.todoList = [];
    this.agent = null;
    this.configManager = new ConfigManager();
    this.docGuildConfig = null;
    this.memoryContent = '';
    this.isRunning = false;

    // Claude Code directory structure support
    this.claudeDir = path.join(this.currentDirectory, '.claude');
    this.agentsDir = path.join(this.claudeDir, 'agents');
    this.commandsDir = path.join(this.claudeDir, 'commands');
    this.skillsDir = path.join(this.claudeDir, 'skills');
    this.mcpDir = path.join(this.claudeDir, 'mcp');
  }

  /**
   * Start the interactive session
   */
  async start() {
    try {
      console.log(chalk.blue.bold('🤖 Document Writing Agent'));
      console.log(chalk.blue('='.repeat(50)));
      console.log(chalk.gray(`Session ID: ${this.sessionId}`));
      console.log(chalk.gray(`Working Directory: ${this.currentDirectory}`));
      console.log(chalk.blue('='.repeat(50)));

      // Load configuration and initialize agent
      await this.loadConfiguration();
      await this.initializeAgent();

      // Check for document guidelines
      await this.loadDocumentGuidelines();

      // Setup Claude Code directory support
      await this.setupClaudeCodeSupport();

      // Initialize readline interface
      this.setupReadline();

      this.isRunning = true;

      console.log(chalk.green('\n✅ Ready! Type your request or use /init, /config, /help, or /exit'));
      console.log(chalk.gray('💡 Use @ followed by filename to reference files (autocomplete available)'));

      // Start the input loop
      this.startInputLoop();

    } catch (error) {
      console.error(chalk.red('❌ Failed to start session:'), error.message);
      throw error;
    }
  }

  /**
   * Load configuration from local file or environment variables
   */
  async loadConfiguration() {
    try {
      // Try to load local config first
      const localConfigPath = path.join(this.currentDirectory, '.doc-agent.json');

      if (await this.fileExists(localConfigPath)) {
        const configData = await fs.readFile(localConfigPath, 'utf8');
        this.config = JSON.parse(configData);
        console.log(chalk.green('✓ Local configuration loaded'));
      } else {
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
        console.log(chalk.yellow('⚠️  Using environment variables (no local config found)'));
      }
    } catch (error) {
      console.log(chalk.red('⚠️  Failed to load configuration, using defaults'));
      this.config = {};
    }
  }

  /**
   * Initialize the document writing agent
   */
  async initializeAgent() {
    try {
      this.agent = new DocumentWritingAgent(this.config, this.currentDirectory);
      console.log(chalk.green('✓ Document Writing Agent initialized'));
    } catch (error) {
      console.log(chalk.red('✗ Failed to initialize agent:'), error.message);
      throw error;
    }
  }

  /**
   * Load document guidelines if they exist
   */
  async loadDocumentGuidelines() {
    const docGuildPath = path.join(this.currentDirectory, '.doc-guild.md');

    if (await this.fileExists(docGuildPath)) {
      const content = await fs.readFile(docGuildPath, 'utf8');
      this.docGuildConfig = content;
      console.log(chalk.green('✓ Document guidelines loaded from .doc-guild.md'));
    } else {
      console.log(chalk.yellow('⚠️  No .doc-guild.md found. Use /init to create document guidelines.'));
    }
  }

  /**
   * Setup Claude Code directory structure support
   */
  async setupClaudeCodeSupport() {
    const directories = [this.claudeDir, this.agentsDir, this.commandsDir, this.skillsDir, this.mcpDir];

    for (const dir of directories) {
      if (await this.fileExists(dir)) {
        console.log(chalk.green(`✓ Found ${path.relative(this.currentDirectory, dir)} directory`));
      }
    }

    // Load memory if it exists
    const memoryPath = path.join(this.currentDirectory, '.memory.md');
    if (await this.fileExists(memoryPath)) {
      this.memoryContent = await fs.readFile(memoryPath, 'utf8');
      console.log(chalk.green('✓ Memory loaded from .memory.md'));
    }
  }

  /**
   * Setup readline interface with autocomplete
   */
  setupReadline() {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      completer: this.completer.bind(this)
    });

    this.rl.on('close', () => {
      this.handleExit();
    });
  }

  /**
   * Autocomplete completer for file references and commands
   */
  async completer(line) {
    const hits = [];
    const commands = ['/init', '/config', '/exit', '/help'];

    if (line.startsWith('@')) {
      // File reference completion
      const searchPattern = line.slice(1) + '*';
      try {
        const files = await glob(searchPattern, {
          cwd: this.currentDirectory,
          ignore: ['node_modules/**', '.git/**']
        });

        for (const file of files) {
          hits.push('@' + file);
        }
      } catch (error) {
        // Ignore glob errors
      }
    } else if (line.startsWith('/')) {
      // Command completion
      for (const cmd of commands) {
        if (cmd.startsWith(line)) {
          hits.push(cmd);
        }
      }
    }

    return [hits, line];
  }

  /**
   * Start the main input loop
   */
  async startInputLoop() {
    const prompt = chalk.cyan('📝 doc> ');

    this.rl.setPrompt(prompt);
    this.rl.prompt();

    this.rl.on('line', async (input) => {
      await this.handleInput(input.trim());
      if (this.isRunning) {
        this.rl.prompt();
      }
    });
  }

  /**
   * Handle user input
   */
  async handleInput(input) {
    if (!input) return;

    try {
      // Handle commands
      if (input.startsWith('/')) {
        await this.handleCommand(input);
        return;
      }

      // Handle file references
      if (input.includes('@')) {
        input = await this.processFileReferences(input);
      }

      // Handle natural language requests
      await this.handleNaturalLanguage(input);

    } catch (error) {
      console.log(chalk.red('❌ Error:'), error.message);
    }
  }

  /**
   * Handle slash commands
   */
  async handleCommand(command) {
    const [cmd, ...args] = command.split(' ');

    switch (cmd) {
      case '/init':
        await this.handleInit();
        break;
      case '/config':
        await this.handleLocalConfig();
        break;
      case '/exit':
        await this.handleExit();
        break;
      case '/help':
        await this.handleHelp();
        break;
      default:
        console.log(chalk.red(`❌ Unknown command: ${cmd}`));
        console.log(chalk.yellow('Available commands: /init, /config, /help, /exit'));
    }
  }

  /**
   * Handle /init command - create document guidelines template
   */
  async handleInit() {
    try {
      const docGuildPath = path.join(this.currentDirectory, '.doc-guild.md');

      if (await this.fileExists(docGuildPath)) {
        const { overwrite } = await inquirer.prompt([
          {
            type: 'confirm',
            name: 'overwrite',
            message: '.doc-guild.md already exists. Overwrite?',
            default: false
          }
        ]);

        if (!overwrite) {
          console.log(chalk.yellow('Operation cancelled.'));
          return;
        }
      }

      const template = this.generateDocGuildTemplate();
      await fs.writeFile(docGuildPath, template, 'utf8');

      console.log(chalk.green('✅ .doc-guild.md created successfully!'));
      console.log(chalk.blue('Please edit the file to specify your document requirements.'));

      // Reload the guidelines
      await this.loadDocumentGuidelines();

    } catch (error) {
      console.log(chalk.red('❌ Failed to create .doc-guild.md:'), error.message);
    }
  }

  /**
   * Handle /config command - create local configuration
   */
  async handleLocalConfig() {
    try {
      const configPath = path.join(this.currentDirectory, '.doc-agent.json');

      if (await this.fileExists(configPath)) {
        const { overwrite } = await inquirer.prompt([
          {
            type: 'confirm',
            name: 'overwrite',
            message: '.doc-agent.json already exists. Overwrite?',
            default: false
          }
        ]);

        if (!overwrite) {
          console.log(chalk.yellow('Operation cancelled.'));
          return;
        }
      }

      const config = await this.createLocalConfig();
      await fs.writeFile(configPath, JSON.stringify(config, null, 2), 'utf8');

      console.log(chalk.green('✅ .doc-agent.json created successfully!'));
      console.log(chalk.blue('Configuration file uses environment variables for security'));

      // Reload configuration
      await this.loadConfiguration();

    } catch (error) {
      console.log(chalk.red('❌ Failed to create .doc-agent.json:'), error.message);
    }
  }

  /**
   * Handle /help command
   */
  async handleHelp() {
    console.log(chalk.blue.bold('\n📖 Document Writing Agent Help\n'));

    console.log(chalk.cyan('Commands:'));
    console.log('  /init     - Create document guidelines template (.doc-guild.md)');
    console.log('  /config   - Create local configuration file (.doc-agent.json)');
    console.log('  /help     - Show this help message');
    console.log('  /exit     - Exit the interactive session\n');

    console.log(chalk.cyan('File References:'));
    console.log('  @filename - Reference a file in the current directory');
    console.log('  Use Tab for autocomplete when typing @filename\n');

    console.log(chalk.cyan('Natural Language:'));
    console.log('  Simply type your document writing request in natural language');
    console.log('  Example: "Write a technical blog post about machine learning"\n');

    if (this.docGuildConfig) {
      console.log(chalk.green('✓ Document guidelines loaded (.doc-guild.md)'));
    } else {
      console.log(chalk.yellow('⚠️  No document guidelines found. Use /init to create them.'));
    }
  }

  /**
   * Handle /exit command
   */
  async handleExit() {
    console.log(chalk.blue('\n👋 Goodbye!'));
    this.isRunning = false;

    if (this.rl) {
      this.rl.close();
    }

    // Clean up memory file if it's empty
    await this.cleanupMemory();

    process.exit(0);
  }

  /**
   * Handle natural language document writing requests
   */
  async handleNaturalLanguage(input) {
    try {
      console.log(chalk.gray('🤔 Processing your request...'));

      if (this.thinkingEnabled) {
        this.showThinking('Analyzing document request and planning workflow');
      }

      // Create a todo list for the task
      this.createTodoList(input);
      this.displayTodoList();

      // Process the request through the agent
      const result = await this.agent.processDocumentRequest(input, {
        guidelines: this.docGuildConfig,
        fileContext: Array.from(this.fileContext),
        memory: this.memoryContent,
        workingDirectory: this.currentDirectory
      });

      if (result.success) {
        console.log(chalk.green('✅ Document processing completed!'));

        if (result.outputFile) {
          console.log(chalk.blue(`📄 Document saved to: ${result.outputFile}`));
        }

        if (result.citations && result.citations.length > 0) {
          console.log(chalk.blue(`🔗 Citations added: ${result.citations.length}`));
        }

      } else {
        console.log(chalk.red('❌ Document processing failed:'), result.error);
      }

    } catch (error) {
      console.log(chalk.red('❌ Error processing request:'), error.message);
    }
  }

  /**
   * Process file references in input
   */
  async processFileReferences(input) {
    const fileRefPattern = /@([^@\s]+)/g;
    const matches = [...input.matchAll(fileRefPattern)];

    for (const match of matches) {
      const filename = match[1];
      const filePath = path.join(this.currentDirectory, filename);

      if (await this.fileExists(filePath)) {
        const content = await fs.readFile(filePath, 'utf8');
        this.fileContext.add(filename);

        // Replace reference with content marker for the agent
        input = input.replace(match[0], `[FILE:${filename}]`);

        console.log(chalk.green(`✓ Referenced file: ${filename}`));
      } else {
        console.log(chalk.red(`❌ File not found: ${filename}`));
      }
    }

    return input;
  }

  /**
   * Show thinking process
   */
  showThinking(message) {
    console.log(chalk.gray(`🤔 ${message}`));
  }

  /**
   * Create and display todo list for document writing
   */
  createTodoList(request) {
    this.todoList = [
      { id: 1, task: 'Analyze document requirements and guidelines', status: 'completed' },
      { id: 2, task: 'Research topic and gather information', status: 'pending' },
      { id: 3, task: 'Create document outline and structure', status: 'pending' },
      { id: 4, task: 'Write document content section by section', status: 'pending' },
      { id: 5, task: 'Download and insert relevant images', status: 'pending' },
      { id: 6, task: 'Add citations and references', status: 'pending' },
      { id: 7, task: 'Validate facts and check consistency', status: 'pending' },
      { id: 8, task: 'Polish and refine language', status: 'pending' },
      { id: 9, task: 'Final review and formatting', status: 'pending' }
    ];
  }

  /**
   * Display current todo list
   */
  displayTodoList() {
    console.log(chalk.blue.bold('\n📋 Document Writing Todo List:'));
    console.log(chalk.blue('-'.repeat(40)));

    for (const item of this.todoList) {
      const status = item.status === 'completed' ? '✅' : '⏳';
      const color = item.status === 'completed' ? chalk.green : chalk.yellow;
      console.log(`${color(status)} ${item.id}. ${item.task}`);
    }

    console.log('');
  }

  /**
   * Generate document guidelines template
   */
  generateDocGuildTemplate() {
    return `# Document Writing Guidelines

## Document Configuration

### Document Type
<!-- Choose one: blog_post, technical_article, research_paper, tutorial, documentation, report -->
document_type: blog_post

### Document Length
<!-- Choose one: short (< 1000 words), medium (1000-3000 words), long (> 3000 words) -->
target_length: medium

### Target Audience
<!-- Describe your target audience -->
target_audience: Technical professionals and developers

### Tone and Style
<!-- Choose one: professional, casual, academic, technical, creative -->
tone: professional
style: Clear, informative, and engaging

### Language
<!-- Primary language for the document -->
language: zh-CN

### Output Format
<!-- Choose one: markdown, html, pdf -->
output_format: markdown

## Content Requirements

### Key Topics
<!-- List the main topics to cover -->
- Introduction to the topic
- Key concepts and principles
- Practical examples and use cases
- Best practices and recommendations
- Conclusion and next steps

### Structure Requirements
<!-- Specify document structure -->
- Clear title and abstract
- Logical section organization
- Proper headings and subheadings
- Code examples where relevant
- Visual elements (diagrams, images)

### Research Requirements
<!-- Specify research depth and sources -->
- Include current industry trends
- Reference authoritative sources
- Provide statistical data when relevant
- Include expert opinions or quotes

### Visual Elements
<!-- Specify requirements for images, diagrams, etc. -->
- Include relevant diagrams and charts
- Add screenshots for technical tutorials
- Use infographics for data visualization
- All images should be stored in ./images/

## Quality Standards

### Accuracy Requirements
- All facts must be verified and cited
- Technical information must be current and accurate
- Include proper references and citations
- No speculative or unverified claims

### Style Guidelines
- Use consistent terminology throughout
- Maintain professional tone
- Ensure logical flow and readability
- Follow proper grammar and syntax

### Citation Style
<!-- Choose citation style -->
citation_style: APA

## Additional Requirements

<!-- Add any specific requirements or constraints -->
special_requirements:
  - Include practical examples
  - Provide actionable insights
  - Consider international audience
  - Ensure accessibility compliance

## Directory Structure

<!-- Output directories -->
images_directory: ./images/
sources_directory: ./sources/
output_directory: ./output/
`;
  }

  /**
   * Create local configuration
   */
  async createLocalConfig() {
    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'baseURL',
        message: 'API Base URL:',
        default: 'https://api.deepseek.com/anthropic'
      },
      {
        type: 'input',
        name: 'auth_token',
        message: 'Auth Token (or leave empty to use environment variable):',
        default: ''
      },
      {
        type: 'input',
        name: 'model',
        message: 'Default Model:',
        default: 'deepseek-reasoner'
      },
      {
        type: 'input',
        name: 'small_fast_model',
        message: 'Small Fast Model:',
        default: 'deepseek-chat'
      },
      {
        type: 'input',
        name: 'timeout',
        message: 'API Timeout (ms):',
        default: '600000'
      }
    ]);

    return {
      anthropic: {
        ...answers,
        disable_nonessential_traffic: true
      }
    };
  }

  
  /**
   * Clean up memory file if empty
   */
  async cleanupMemory() {
    const memoryPath = path.join(this.currentDirectory, '.memory.md');

    try {
      if (await this.fileExists(memoryPath)) {
        const content = await fs.readFile(memoryPath, 'utf8');
        if (!content.trim()) {
          await fs.unlink(memoryPath);
        }
      }
    } catch (error) {
      // Ignore cleanup errors
    }
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