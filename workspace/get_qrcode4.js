const http = require('http');
const fs = require('fs');

async function main() {
  // 创建单个 SSE 连接
  const req = http.request({
    hostname: 'localhost', port: 18060, path: '/mcp', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' }
  }, res => {
    let buffer = '';
    res.on('data', chunk => {
      buffer += chunk;
      console.log('收到数据块:', chunk.toString());
    });
    res.on('end', () => {
      console.log('\n=== 完整响应 ===');
      console.log(buffer);
      
      // 尝试解析所有 data: 行
      const lines = buffer.split('\n');
      for (const line of lines) {
        if (line.startsWith('data:')) {
          try {
            const json = JSON.parse(line.slice(5).trim());
            console.log('\n解析到:', JSON.stringify(json, null, 2));
            
            // 检查是否有图片
            if (json.result?.content) {
              for (const c of json.result.content) {
                if (c.type === 'image' && c.data) {
                  fs.writeFileSync('D:/.openclaw/workspace/qrcode.png', Buffer.from(c.data, 'base64'));
                  console.log('\n二维码已保存到 qrcode.png');
                }
              }
            }
          } catch(e) {}
        }
      }
    });
  });
  req.on('error', e => console.error('错误:', e));
  
  // 发送初始化请求
  console.log('发送初始化请求...');
  req.write(JSON.stringify({jsonrpc:'2.0',id:0,method:'initialize',params:{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'test',version:'1.0'}}}));
  req.end();
}

main();