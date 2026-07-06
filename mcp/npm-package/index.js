#!/usr/bin/env node
/**
 * AgentServices MCP Server — Node.js wrapper
 * Spawns the Python MCP server that exposes AgentServices APIs as MCP tools
 */
const { spawn } = require('child_process');
const path = require('path');

const serverPath = path.join(__dirname, 'server_wrapper.py');

const py = spawn('python3', [serverPath], {
  stdio: ['inherit', 'inherit', 'inherit']
});

py.on('error', (err) => {
  console.error('Failed to start AgentServices MCP server:', err.message);
  console.error('Make sure Python 3 and the mcp package are installed:');
  console.error('  pip install mcp httpx');
  process.exit(1);
});

py.on('exit', (code) => {
  process.exit(code || 0);
});
