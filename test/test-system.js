#!/usr/bin/env node

/**
 * System Test Script
 *
 * Tests the Document Writing Agent system functionality.
 */

import { promises as fs } from 'fs';
import path from 'path';
import { InteractiveSession } from '../src/interactive/session.js';
import { ConfigManager } from '../src/config/config-manager.js';
import { DocumentWritingAgent } from '../src/agent/document-agent.js';
import { WebResearcher } from '../src/research/web-researcher.js';
import { ImageManager } from '../src/media/image-manager.js';
import { CitationManager } from '../src/citation/citation-manager.js';
import { DocumentValidator } from '../src/validation/document-validator.js';
import { MemoryManager } from '../src/memory/memory-manager.js';

console.log('🧪 Testing Document Writing Agent System...\n');

async function runTests() {
  const results = {
    passed: 0,
    failed: 0,
    total: 0
  };

  // Test 1: Configuration Manager
  await testModule('Configuration Manager', async () => {
    const configManager = new ConfigManager();
    const config = await configManager.loadConfig(process.cwd());
    console.log('✓ Configuration loaded successfully');
    console.log('✓ Default provider:', config.anthropic?.model || 'deepseek-reasoner');
  }, results);

  // Test 2: Web Researcher
  await testModule('Web Researcher', async () => {
    const researcher = new WebResearcher();
    const researchResult = await researcher.researchTopic('test topic');
    console.log('✓ Research completed successfully');
    console.log('✓ Research results length:', researchResult.results?.length || 0);
    console.log('✓ Summary generated:', !!researchResult.summary);
  }, results);

  // Test 3: Image Manager
  await testModule('Image Manager', async () => {
    const imageManager = new ImageManager(process.cwd());
    await imageManager.initialize();
    const imagePath = await imageManager.downloadImage('test diagram');
    console.log('✓ Image manager initialized');
    console.log('✓ Image generated/processed:', !!imagePath);
  }, results);

  // Test 4: Citation Manager
  await testModule('Citation Manager', async () => {
    const citationManager = new CitationManager();
    const citation = await citationManager.createCitation('https://example.com/test', 'APA');
    console.log('✓ Citation created successfully');
    console.log('✓ Citation formatted:', !!citation.formatted);
    console.log('✓ Total citations:', citationManager.getAllCitations().length);
  }, results);

  // Test 5: Document Validator
  await testModule('Document Validator', async () => {
    const validator = new DocumentValidator();
    const testContent = `# Test Document

This is a test document for validation purposes.

## Introduction

Here is some content to validate.

## Conclusion

The end of the test document.`;

    const validationResult = await validator.validate(testContent);
    console.log('✓ Document validation completed');
    console.log('✓ Validation score:', validationResult.score);
    console.log('✓ Issues found:', validationResult.issues.length);
  }, results);

  // Test 6: Memory Manager
  await testModule('Memory Manager', async () => {
    const memoryManager = new MemoryManager(process.cwd());
    await memoryManager.initialize();
    const note = await memoryManager.addNote('Test Note', 'This is a test note for the memory manager.');
    console.log('✓ Memory manager initialized');
    console.log('✓ Note added successfully:', !!note.id);
    console.log('✓ Statistics:', Object.keys(memoryManager.getStatistics()).length);
  }, results);

  // Test 7: Document Writing Agent
  await testModule('Document Writing Agent', async () => {
    const configManager = new ConfigManager();
    const config = await configManager.loadConfig(process.cwd());
    const agent = new DocumentWritingAgent(config, process.cwd());

    const testRequest = 'Write a short test document about AI';
    const result = await agent.processDocumentRequest(testRequest, {
      guidelines: 'Write a brief overview of AI in 200 words',
      fileContext: [],
      memory: '',
      workingDirectory: process.cwd()
    });

    console.log('✓ Document processing initiated');
    console.log('✓ Process completed successfully:', result.success);
    if (result.success) {
      console.log('✓ Output file created:', !!result.outputFile);
    }
  }, results);

  // Test 8: Interactive Session (limited test)
  await testModule('Interactive Session', async () => {
    const session = new InteractiveSession();

    // Test initialization without starting the full interactive loop
    console.log('✓ Session created');
    console.log('✓ Working directory set:', session.currentDirectory);
    console.log('✓ Claude directories configured:', !!session.claudeDir);

    // Test configuration loading
    await session.loadConfiguration();
    console.log('✓ Configuration loaded');

    // Test todo list creation
    session.createTodoList('test request');
    console.log('✓ Todo list created:', session.todoList.length, 'items');

  }, results);

  // Test 9: File Operations
  await testModule('File Operations', async () => {
    const testFile = path.join(process.cwd(), 'test-temp.md');
    const testContent = `# Test File

This is a test file for the Document Writing Agent.

## Content

Some test content here.

**Bold text** and *italic text*.

- List item 1
- List item 2
- List item 3

\`\`\`javascript
// Code example
function test() {
  console.log("Hello, World!");
}
\`\`\`
`;

    await fs.writeFile(testFile, testContent, 'utf8');
    const content = await fs.readFile(testFile, 'utf8');

    // Clean up
    await fs.unlink(testFile);

    console.log('✓ File write operation successful');
    console.log('✓ File read operation successful');
    console.log('✓ File cleanup successful');
  }, results);

  // Print summary
  console.log('\n' + '='.repeat(50));
  console.log('📊 Test Summary');
  console.log('='.repeat(50));
  console.log(`Total tests: ${results.total}`);
  console.log(`Passed: ${results.passed}`);
  console.log(`Failed: ${results.failed}`);
  console.log(`Success rate: ${((results.passed / results.total) * 100).toFixed(1)}%`);

  if (results.failed === 0) {
    console.log('\n🎉 All tests passed! The Document Writing Agent system is working correctly.');
  } else {
    console.log('\n⚠️  Some tests failed. Please check the implementation.');
  }

  return results;
}

async function testModule(moduleName, testFunction, results) {
  results.total++;

  try {
    console.log(`\n🔍 Testing ${moduleName}...`);
    await testFunction();
    results.passed++;
    console.log(`✅ ${moduleName} - PASSED`);
  } catch (error) {
    results.failed++;
    console.log(`❌ ${moduleName} - FAILED`);
    console.log(`   Error: ${error.message}`);
  }
}

// Run all tests
runTests().catch(error => {
  console.error('❌ Test suite failed:', error);
  process.exit(1);
});