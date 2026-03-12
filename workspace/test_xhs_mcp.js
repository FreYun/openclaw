// 测试小红书 MCP - 获取登录二维码并保存到文件
const http = require('http');

const callMcp = (method, params = {}) => {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost',
      port: 18060,
      path: '/mcp',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
      }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          // 尝试解析 SSE 格式
          const lines = data.split('\n');
          let jsonStr = '';
          for (const line of lines) {
            if (line.startsWith('data:')) {
              jsonStr = line.substring(5).trim();
            }
          }
          if (!jsonStr) jsonStr = data;
          resolve(JSON.parse(jsonStr));
        } catch (e) {
          resolve({ raw: data });
        }
      });
    });
    req.on('error', reject);
    req.write(JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }));
    req.end();
  });
};

const fs = require('fs');

async function main() {
  // 初始化
  console.log('初始化 MCP 会话...');
  await callMcp('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'test', version: '1.0.0' }
  });
  
  // 发送 initialized 通知
  await callMcp('notifications/initialized');
  
  // 获取登录二维码
  console.log('获取登录二维码...');
  const result = await callMcp('tools/call', {
    name: 'get_login_qrcode',
    arguments: {}
  });
  
  console.log('响应:', JSON.stringify(result, null, 2));
  
  // 提取图片数据
  if (result.result && result.result.content) {
    for (const item of result.result.content) {
      if (item.type === 'image' && item.data) {
        console.log('\n找到图片数据！长度:', item.data.length);
        const buffer = Buffer.from(item.data, 'base64');
        fs.writeFileSync('D:\\.openclaw\\workspace\\qrcode.png', buffer);
        console.log('二维码已保存到 D:\\.openclaw\\workspace\\qrcode.png');
      }
      if (item.type === 'text') {
        console.log('\n文本消息:', item.text);
      }
    }
  }
  
  // 检查登录状态
  console.log('\n检查登录状态...');
  const status = await callMcp('tools/call', {
    name: 'check_login_status',
    arguments: {}
  });
  console.log('登录状态:', JSON.stringify(status, null, 2));
}

main().catch(console.error);