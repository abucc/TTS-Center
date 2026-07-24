const fs = require('fs');
const http = require('http');
const path = require('path');

const port = Number(process.env.PORT || 3003);
const root = process.env.STATIC_ROOT || '/app';
const upstream = new URL(process.env.API_UPSTREAM || 'http://voice-hub-gateway:9000');

const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg',
};

function send(res, status, body, headers = {}) {
  res.writeHead(status, headers);
  res.end(body);
}

function proxyApi(req, res) {
  const requestUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const targetPath = requestUrl.pathname.replace(/^\/api\/?/, '/') + requestUrl.search;
  const headers = { ...req.headers, host: upstream.host };
  delete headers.connection;

  const proxyReq = http.request(
    {
      hostname: upstream.hostname,
      port: upstream.port || 80,
      protocol: upstream.protocol,
      method: req.method,
      path: targetPath,
      headers,
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on('error', (error) => {
    send(res, 502, JSON.stringify({ detail: `API proxy failed: ${error.message}` }), {
      'content-type': 'application/json; charset=utf-8',
    });
  });

  req.pipe(proxyReq);
}

function serveStatic(req, res) {
  const requestUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const decodedPath = decodeURIComponent(requestUrl.pathname);
  const safePath = path.normalize(decodedPath).replace(/^(\.\.[/\\])+/, '');
  let filePath = path.join(root, safePath);

  if (!filePath.startsWith(root)) {
    return send(res, 403, 'Forbidden');
  }

  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(root, 'index.html');
  }

  const ext = path.extname(filePath);
  const headers = { 'content-type': mimeTypes[ext] || 'application/octet-stream' };
  if (path.basename(filePath) === 'index.html') {
    headers['cache-control'] = 'no-store';
  }

  fs.createReadStream(filePath)
    .on('error', () => send(res, 404, 'Not found'))
    .on('open', () => res.writeHead(200, headers))
    .pipe(res);
}

http
  .createServer((req, res) => {
    if (req.url && (req.url === '/api' || req.url.startsWith('/api/'))) {
      proxyApi(req, res);
      return;
    }
    serveStatic(req, res);
  })
  .listen(port, '0.0.0.0', () => {
    console.log(`Voice hub frontend listening on ${port}`);
  });
