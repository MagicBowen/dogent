#!/usr/bin/env node

/**
 * CLI Test Script
 */

import { InteractiveSession } from '../src/interactive/session.js';

async function testCLI() {
  try {
    console.log('🧪 Testing CLI Entry Point...\n');

    const session = new InteractiveSession();

    // Test basic initialization
    console.log('✓ Session created');
    console.log('✓ Working directory:', session.currentDirectory);
    console.log('✓ Session ID:', session.sessionId);

    // Test configuration loading
    await session.loadConfiguration();
    console.log('✓ Configuration loaded');

    // Test command recognition
    console.log('✓ Commands available:', session.commands?.size || 0);

    console.log('\n✅ CLI test completed successfully!');

  } catch (error) {
    console.error('❌ CLI test failed:', error.message);
    process.exit(1);
  }
}

testCLI();