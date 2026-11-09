const http = require('http');

async function main() {
  const list = await new Promise((resolve) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    });
  });

  const page = list.find(t => t.type === 'page' && t.url.includes('8080'));
  if (!page) {
    console.log('No 8080 page found in targets:', list);
    return;
  }
  console.log('Target found:', page.title, page.webSocketDebuggerUrl);

  const WebSocket = require('ws');
  const ws = new WebSocket(page.webSocketDebuggerUrl);

  ws.on('open', () => {
    ws.send(JSON.stringify({
      id: 1,
      method: 'Runtime.evaluate',
      params: {
        expression: `({
          title: document.title,
          canvas: !!document.querySelector('canvas'),
          toolChips: document.querySelectorAll('.tool-chip').length,
          toolbar: !!document.getElementById('toolbar-container'),
          timeline: !!document.getElementById('timeline-bar-root'),
          agent: !!document.getElementById('agent-panel-container'),
          statusText: document.getElementById('status-text')?.textContent
        })`,
        returnByValue: true
      }
    }));
  });

  ws.on('message', (data) => {
    console.log('DOM Evaluation Result:', JSON.stringify(JSON.parse(data.toString()), null, 2));
    ws.close();
  });
}

main().catch(console.error);
