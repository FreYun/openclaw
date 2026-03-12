const http = require('http');
const fs = require('fs');

const call = (id, method, params) => new Promise((resolve, reject) => {
  const req = http.request({
    hostname: 'localhost', port: 18060, path: '/mcp', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' }
  }, res => {
    let data = '';
    res.on('data', c => data += c);
    res.on('end', () => {
      // SSE 格式：找 data: 开头的行
      const lines = data.split('\n');
      for (const line of lines) {
        if (line.startsWith('data:')) {
          try { resolve(JSON.parse(line.slice(5).trim())); return; }
          catch(e) {}
        }
      }
      // 非 SSE 格式
      try { resolve(JSON.parse(data)); } catch(e) { resolve({raw: data}); }
    });
  });
  req.on('error', reject);
  req.write(JSON.stringify({jsonrpc:'2.0',id,method,params}));
  req.end();
});

async function main() {
  console.log('初始化...');
  await call(0, 'initialize', {protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'test',version:'1.0.0'}});
  
  console.log('发送 initialized...');
  await call(null, 'notifications/initialized', {});
  
  console.log('获取登录二维码...');
  const r = await call(1, 'tools/call', {name:'get_login_qrcode',arguments:{}});
  
  if (r.result?.content) {
    for (const c of r.result.content) {
      if (c.type === 'image' && c.data) {
        console.log('找到图片，长度:', c.data.length);
        fs.writeFileSync('D:/.openclaw/workspace/qrcode.png', Buffer.from(c.data, 'base64'));
        console.log('已保存到 qrcode.png');
      }
      if (c.type === 'text') console.log('文本:', c.text);
    }
  } else {
    console.log('响应:', JSON.stringify(r, null, 2));
  }
}
main().catch(e => console.error('错误:', e));