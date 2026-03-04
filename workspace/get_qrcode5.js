const http = require('http');
const fs = require('fs');

async function main() {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost', port: 18060, path: '/mcp', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' }
    }, res => {
      let buffer = '';
      res.on('data', chunk => buffer += chunk);
      res.on('end', () => {
        console.log('完整响应:\n', buffer);
        const lines = buffer.split('\n');
        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const json = JSON.parse(line.slice(5).trim());
              if (json.result?.content) {
                for (const c of json.result.content) {
                  if (c.type === 'image' && c.data) {
                    fs.writeFileSync('D:/.openclaw/workspace/qrcode.png', Buffer.from(c.data, 'base64'));
                    console.log('\n✅ 二维码已保存到 D:/.openclaw/workspace/qrcode.png');
                  }
                  if (c.type === 'text') console.log('文本:', c.text);
                }
              }
            } catch(e) {}
          }
        }
        resolve();
      });
    });
    req.on('error', reject);
    
    // 发送批量请求：initialize + initialized + tools/call
    console.log('发送批量请求...');
    const batch = [
      {jsonrpc:'2.0',id:0,method:'initialize',params:{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'test',version:'1.0'}}},
      {jsonrpc:'2.0',method:'notifications/initialized'},
      {jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'get_login_qrcode',arguments:{}}}
    ];
    req.write(JSON.stringify(batch));
    req.end();
  });
}

main().catch(e => console.error('错误:', e));