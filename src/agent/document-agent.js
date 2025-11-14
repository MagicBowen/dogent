/**
 * Document Writing Agent
 *
 * Core agent that integrates with Claude Agent SDK for professional document writing.
 * Handles research, writing, validation, and formatting of documents.
 */

import { promises as fs } from 'fs';
import path from 'path';
import { query } from '@anthropic-ai/claude-agent-sdk';
import { z } from 'zod';
import { WebResearcher } from '../research/web-researcher.js';
import { ImageManager } from '../media/image-manager.js';
import { CitationManager } from '../citation/citation-manager.js';
import { DocumentValidator } from '../validation/document-validator.js';
import { MemoryManager } from '../memory/memory-manager.js';

export class DocumentWritingAgent {
  constructor(config, workingDirectory) {
    this.config = config || {};
    this.workingDirectory = workingDirectory;
    this.claudeAgent = null;
    this.researcher = new WebResearcher();
    this.imageManager = new ImageManager(workingDirectory);
    this.citationManager = new CitationManager();
    this.validator = new DocumentValidator();
    this.memoryManager = new MemoryManager(workingDirectory);

    this.systemPrompt = this.createSystemPrompt();
  }

  /**
   * Process a document writing request
   */
  async processDocumentRequest(request, context = {}) {
    try {
      console.log('📝 Starting document writing process...');

      // Parse the request and create a plan
      const plan = await this.createWritingPlan(request, context);

      // Execute the writing plan step by step
      const result = await this.executeWritingPlan(plan, context);

      return {
        success: true,
        outputFile: result.outputFile,
        citations: result.citations,
        images: result.images,
        sections: result.sections
      };

    } catch (error) {
      console.error('❌ Document writing failed:', error.message);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Create a writing plan based on the request
   */
  async createWritingPlan(request, context) {
    const guidelines = context.guidelines || '';
    const fileContext = context.fileContext || [];

    const prompt = `
Based on the following request and guidelines, create a detailed writing plan:

REQUEST: ${request}

GUIDELINES:
${guidelines}

CONTEXT FILES:
${fileContext.map(f => `- ${f}`).join('\n')}

Please create a structured plan with the following sections:
1. Document Analysis - Understanding requirements
2. Research Plan - What information needs to be gathered
3. Structure Plan - Document outline and sections
4. Content Plan - Key points for each section
5. Media Plan - Images and visual elements needed
6. Citation Plan - Sources and references needed
7. Validation Plan - Fact-checking and quality checks

Format your response as JSON with clear sections and actionable items.
`;

    try {
      const response = await this.callClaude(prompt);
      return JSON.parse(response);
    } catch (error) {
      // Fallback to basic plan if JSON parsing fails
      return this.createFallbackPlan(request);
    }
  }

  /**
   * Execute the writing plan
   */
  async executeWritingPlan(plan, context) {
    console.log('📋 Executing writing plan...');

    const results = {
      sections: [],
      images: [],
      citations: [],
      outputFile: null
    };

    // Step 1: Research phase
    if (plan.researchPlan && plan.researchPlan.topics) {
      console.log('🔍 Conducting research...');
      const researchResults = await this.conductResearch(plan.researchPlan);
      plan.researchResults = researchResults;
    }

    // Step 2: Create document structure
    if (plan.structurePlan) {
      console.log('🏗️  Creating document structure...');
      results.sections = plan.structurePlan.sections || [];
    }

    // Step 3: Generate content for each section
    console.log('✍️  Writing content...');
    const content = await this.generateContent(plan, context);

    // Step 4: Handle images and media
    if (plan.mediaPlan && plan.mediaPlan.images) {
      console.log('🖼️  Processing images...');
      results.images = await this.processImages(plan.mediaPlan.images);
    }

    // Step 5: Add citations
    if (plan.citationPlan) {
      console.log('📚 Adding citations...');
      results.citations = await this.processCitations(plan.citationPlan, content);
    }

    // Step 6: Validate content
    if (plan.validationPlan) {
      console.log('✅ Validating content...');
      await this.validateContent(content, plan.validationPlan);
    }

    // Step 7: Final polishing
    console.log('🔧 Final polishing...');
    const finalContent = await this.polishContent(content, context);

    // Step 8: Save document
    results.outputFile = await this.saveDocument(finalContent, context);

    return results;
  }

  /**
   * Conduct research based on research plan
   */
  async conductResearch(researchPlan) {
    const results = {};

    for (const topic of researchPlan.topics || []) {
      try {
        const researchData = await this.researcher.researchTopic(topic);
        results[topic] = researchData;

        // Save research to memory
        await this.memoryManager.addNote(`Research: ${topic}`, researchData.summary);
      } catch (error) {
        console.warn(`⚠️  Research failed for topic: ${topic}`, error.message);
        results[topic] = { error: error.message };
      }
    }

    return results;
  }

  /**
   * Generate content for the document
   */
  async generateContent(plan, context) {
    const prompt = `
Based on the following information, write a comprehensive document:

WRITING PLAN:
${JSON.stringify(plan, null, 2)}

RESEARCH RESULTS:
${JSON.stringify(plan.researchResults || {}, null, 2)}

GUIDELINES:
${context.guidelines || 'No specific guidelines provided.'}

CONTEXT:
${context.fileContext ? context.fileContext.map(f => `- ${f}`).join('\n') : ''}

Please write the complete document following these requirements:
1. Use professional, clear language (${context.guidelines.includes('language: zh-CN') ? 'Chinese' : 'English'})
2. Include proper section structure
3. Incorporate research findings naturally
4. Mark image insertion points with [IMAGE: description]
5. Mark citation points with [CITATION: source]
6. Use markdown formatting
7. Include code blocks, tables, and lists where appropriate

Return the complete document content.
`;

    return await this.callClaude(prompt);
  }

  /**
   * Process images for the document
   */
  async processImages(imageDescriptions) {
    const images = [];

    for (const imageDesc of imageDescriptions) {
      try {
        const imagePath = await this.imageManager.downloadImage(imageDesc);
        images.push({
          description: imageDesc,
          path: imagePath,
          filename: path.basename(imagePath)
        });
      } catch (error) {
        console.warn(`⚠️  Failed to process image: ${imageDesc}`, error.message);
      }
    }

    return images;
  }

  /**
   * Process citations for the document
   */
  async processCitations(citationPlan, content) {
    const citations = [];

    // Extract citation markers from content
    const citationMarkers = content.match(/\[CITATION: ([^\]]+)\]/g) || [];

    for (const marker of citationMarkers) {
      const source = marker.replace('[CITATION: ', '').replace(']', '');

      try {
        const citation = await this.citationManager.createCitation(source);
        citations.push(citation);
      } catch (error) {
        console.warn(`⚠️  Failed to create citation for: ${source}`, error.message);
      }
    }

    return citations;
  }

  /**
   * Validate content quality
   */
  async validateContent(content, validationPlan) {
    return await this.validator.validate(content, validationPlan);
  }

  /**
   * Polish and refine content
   */
  async polishContent(content, context) {
    const prompt = `
Please polish and refine the following document content:

CONTENT:
${content}

REQUIREMENTS:
1. Improve language clarity and flow
2. Ensure consistent tone and style
3. Fix any grammatical errors
4. Improve transitions between sections
5. Enhance readability
6. Maintain all factual information and citations
7. Keep the same structure and formatting

Return the polished content with all improvements applied.
`;

    return await this.callClaude(prompt);
  }

  /**
   * Save the final document
   */
  async saveDocument(content, context) {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    const filename = `document_${timestamp}.md`;
    const outputPath = path.join(this.workingDirectory, filename);

    // Process final content - replace placeholders
    let finalContent = content;

    // Replace image placeholders
    const imagePlaceholders = content.match(/\[IMAGE: ([^\]]+)\]/g) || [];
    for (const placeholder of imagePlaceholders) {
      const description = placeholder.replace('[IMAGE: ', '').replace(']', '');
      finalContent = finalContent.replace(placeholder, `![${description}](./images/${description.toLowerCase().replace(/\s+/g, '_')}.png)`);
    }

    // Add citations section at the end
    const citations = await this.citationManager.getAllCitations();
    if (citations.length > 0) {
      finalContent += '\n\n---\n\n## References\n\n';
      citations.forEach((citation, index) => {
        finalContent += `${index + 1}. ${citation.formatted}\n`;
      });
    }

    await fs.writeFile(outputPath, finalContent, 'utf8');
    console.log(`📄 Document saved to: ${outputPath}`);

    return outputPath;
  }

  /**
   * Call Claude Agent SDK
   */
  async callClaude(prompt) {
    console.log('🤖 Initializing Claude Agent SDK...');

    try {
      // Load configuration from user workspace
      const { ConfigManager } = await import('../config/config-manager.js');
      const configManager = new ConfigManager();
      const config = await configManager.loadConfig(this.workingDirectory);

      // Extract configuration from the anthropic object or direct config
      const apiConfig = config.anthropic || config;

      // Set environment variables for Claude Agent SDK
      // Claude Agent SDK looks for these specific environment variables
      if (apiConfig.baseURL || apiConfig.apiUrl) {
        process.env.ANTHROPIC_BASE_URL = apiConfig.baseURL || apiConfig.apiUrl;
        console.log('🔗 Set API URL:', process.env.ANTHROPIC_BASE_URL);
      }

      if (apiConfig.auth_token || apiConfig.authToken) {
        process.env.ANTHROPIC_AUTH_TOKEN = apiConfig.auth_token || apiConfig.authToken;
        console.log('🔑 Set API token (length:', process.env.ANTHROPIC_AUTH_TOKEN.length, ')');
      }

      // Prepare the full prompt with system instructions
      const fullPrompt = `${this.systemPrompt}\n\n${prompt}`;

      console.log('⚡ Processing request with Claude Agent SDK...');
      console.log('🤖 Using model:', apiConfig.model);

      // Use the query function from Claude Agent SDK with correct parameter format
      const response = query({
        prompt: fullPrompt,
        options: {
          model: apiConfig.model,
          permissionMode: "bypassPermissions", // Bypass permissions for document generation
          maxBudgetUsd: 1.0, // Set a reasonable budget limit
          timeout: apiConfig.timeout || 120000,
          workingDirectory: this.workingDirectory
        }
      });

      console.log('✅ Received response from Claude Agent SDK');

      // Handle streaming response - collect assistant messages
      let fullResponse = '';

      for await (const message of response) {
        if (message.type === 'assistant') {
          // Assistant messages might have content in different formats
          if (message.message && message.message.content) {
            if (typeof message.message.content === 'string') {
              fullResponse += message.message.content;
            } else if (Array.isArray(message.message.content)) {
              for (const block of message.message.content) {
                if (block.type === 'text') {
                  fullResponse += block.text;
                }
              }
            }
          }
        } else if (message.type === 'result' && message.subtype === 'success') {
          // The final result is often in the result message
          if (message.result && typeof message.result === 'string') {
            fullResponse = message.result;
          }
        } else if (message.type === 'error') {
          console.error('❌ Claude Agent SDK error:', message.error);
          throw new Error(`Claude Agent SDK error: ${message.error}`);
        } else if (message.type === 'system' && message.subtype === 'init') {
          console.log(`📋 Session ID: ${message.session_id}`);
          console.log(`🤖 Model: ${message.model}`);
        }
      }

      if (!fullResponse.trim()) {
        throw new Error('No content received from Claude Agent SDK');
      }

      return fullResponse;

    } catch (error) {
      console.error('❌ Claude Agent SDK call failed:', error.message);

      // If API call fails, provide a fallback response
      return `# API Error Fallback

I apologize, but I encountered an error while trying to communicate with the AI model: ${error.message}

Please check your configuration in .doc-agent.json and ensure:
1. Your API token is correctly set in environment variables
2. The API URL is accessible
3. Your model configuration is correct

You can run \`/config\` to recreate your configuration file.

## Next Steps
1. Check your environment variables: ANTHROPIC_AUTH_TOKEN
2. Verify your internet connection
3. Try running the command again
`;
    }
  }

  
  /**
   * Create comprehensive system prompt for the agent
   */
  createSystemPrompt() {
    return `You are an expert Document Writing Agent, a specialized AI assistant for creating professional, well-researched, and high-quality documents. Your capabilities include:

## Core Expertise
- Professional writing and editing across multiple domains
- Comprehensive research and fact-checking
- Document structure and formatting
- Citation management and academic integrity
- Visual content integration
- Quality assurance and validation

## Writing Standards
1. **Clarity and Precision**: Write in clear, concise language appropriate for the target audience
2. **Structural Integrity**: Create logical document flows with proper headings and sections
3. **Research Excellence**: Incorporate current, accurate information from reliable sources
4. **Citation Compliance**: Properly attribute all sources and maintain academic integrity
5. **Visual Integration**: Effectively use images, diagrams, and other visual elements
6. **Quality Assurance**: Ensure factual accuracy, consistency, and professional presentation

## Document Types
- Technical articles and documentation
- Research papers and reports
- Blog posts and web content
- Tutorials and guides
- Business documents and proposals

## Research Process
1. **Topic Analysis**: Understand scope and requirements
2. **Source Evaluation**: Identify authoritative and current sources
3. **Information Synthesis**: Combine multiple sources into coherent narrative
4. **Fact Verification**: Ensure all claims are accurate and verifiable
5. **Citation Management**: Track and properly format all references

## Quality Checklist
- [ ] Content accuracy and factual correctness
- [ ] Logical structure and flow
- [ ] Proper grammar and syntax
- [ ] Consistent tone and style
- [ ] Complete citations and references
- [ ] Appropriate visual elements
- [ ] Target audience alignment
- [ ] Format compliance

## Special Instructions
- Always prioritize accuracy over speculation
- Use primary sources when available
- Consider international and cultural perspectives
- Ensure accessibility and inclusivity
- Maintain professional ethics and integrity

When given a document writing request, analyze the requirements thoroughly, conduct comprehensive research, and produce a high-quality document that meets professional standards.`;
  }

  /**
   * Create fallback plan if main planning fails
   */
  createFallbackPlan(request) {
    return {
      documentAnalysis: {
        type: "general_document",
        estimatedLength: "medium",
        complexity: "intermediate"
      },
      researchPlan: {
        topics: [request],
        sources: 3,
        depth: "basic"
      },
      structurePlan: {
        sections: ["Introduction", "Main Content", "Conclusion"]
      },
      contentPlan: {
        keyPoints: ["Clear explanation", "Relevant examples", "Logical flow"]
      },
      mediaPlan: {
        images: []
      },
      citationPlan: {
        sources: []
      },
      validationPlan: {
        checks: ["readability", "accuracy"]
      }
    };
  }
}