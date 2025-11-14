#!/usr/bin/env node

// 测试 Claude Agent SDK 的 query 函数
import { query } from '@anthropic-ai/claude-agent-sdk';

async function testQuery() {
  console.log('🧪 开始测试 Claude Agent SDK query 函数...');

  try {
    console.log('📋 调用 query 函数...');

    // 首先设置环境变量来模拟从配置文件读取
    process.env.ANTHROPIC_BASE_URL = 'https://api.deepseek.com/anthropic';
    process.env.ANTHROPIC_AUTH_TOKEN = 'e7461888606b43079811f279f8dc8f8e.aKyHGmUdjBuZO38f';

    const response = query({
      prompt: 'Hello, please respond with "API works!"',
      options: {
        model: 'claude-3-5-sonnet-20241022',
        permissionMode: 'bypassPermissions',
        maxBudgetUsd: 0.1
      }
    });

    console.log('✅ Query 函数返回类型:', typeof response);
    console.log('🔍 Response details:', {
      isString: typeof response === 'string',
      hasIterator: response && typeof response[Symbol.asyncIterator] === 'function',
      hasContent: response && response.content,
      keys: response ? Object.keys(response) : 'null/undefined'
    });

    if (typeof response === 'string') {
      console.log('📝 响应内容 (字符串):', response);
    } else if (response && typeof response[Symbol.asyncIterator] === 'function') {
      console.log('🌊 处理流式响应...');
      let fullResponse = '';
      for await (const message of response) {
        console.log('📦 收到消息:', message.type);
        if (message.type === 'assistant') {
          console.log('🤖 Assistant 消息结构:', JSON.stringify(message.content, null, 2));
          if (typeof message.content === 'string') {
            fullResponse += message.content;
          } else if (Array.isArray(message.content)) {
            for (const block of message.content) {
              if (block.type === 'text') {
                fullResponse += block.text;
              }
            }
          }
        } else if (message.type === 'error') {
          console.error('❌ 消息错误:', message.error);
          throw new Error(`API Error: ${message.error}`);
        } else if (message.type === 'result' && message.subtype === 'success') {
          console.log('✅ 最终结果:', message.result);
          fullResponse = message.result;
        }
      }
      console.log('📝 完整响应:', fullResponse);
    } else if (response && response.content) {
      console.log('📝 响应内容 (对象):', response.content);
    } else {
      console.log('❌ 未知响应格式:', response);
    }

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    console.error('📋 错误堆栈:', error.stack);
  }
}

testQuery();