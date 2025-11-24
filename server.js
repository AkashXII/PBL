// server.js
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const http = require('http');
const WebSocket = require('ws');

const app = express();
app.use(cors());
app.use(express.json());

// file upload (in-memory)
const upload = multer({ storage: multer.memoryStorage() });

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

/**
 * Peer registry:
 * peerId -> { ws, meta: { name, lat, lon, tags }, lastSeen }
 */
const peers = new Map();

/**
 * Task tracking
 * taskId -> { sentTo: [peerId], responses: {peerId: response}, createdAt }
 */
const tasks = new Map();

/* -------------------------
   WebSocket message format
   All messages are JSON with a `type` field.
   Types from peer -> server:
     - register: { type:'register', peerId, meta:{name,lat,lon,tags} }
     - heartbeat: { type:'heartbeat', peerId }
     - taskResult: { type:'taskResult', peerId, taskId, result }
   Types from server -> peer:
     - task: { type:'task', taskId, task:{...}, file:{name,mime,size,dataBase64} }
     - info: { type:'info', message: '...' }
   ------------------------- */

wss.on('connection', (ws, req) => {
  // optional: get IP
  const ip = (req.socket && req.socket.remoteAddress) || null;

  ws.isAlive = true;

  ws.on('pong', () => { ws.isAlive = true; });

  ws.on('message', message => {
    try {
      const msg = JSON.parse(message.toString());

      if (msg.type === 'register') {
        // register the peer
        const { peerId, meta } = msg;
        if (!peerId) return ws.send(JSON.stringify({ type: 'error', message: 'peerId required' }));

        peers.set(peerId, {
          ws,
          meta: meta || {},
          lastSeen: Date.now(),
          ip
        });

        ws.peerId = peerId;

        ws.send(JSON.stringify({ type: 'info', message: 'registered', peerId }));
        console.log(`Peer registered: ${peerId}`, meta || {});
      } else if (msg.type === 'heartbeat') {
        const { peerId } = msg;
        const entry = peers.get(peerId);
        if (entry) entry.lastSeen = Date.now();
      } else if (msg.type === 'taskResult') {
        const { peerId, taskId, result } = msg;
        const t = tasks.get(taskId);
        if (t) {
          t.responses[peerId] = result;
          console.log(`Task result from ${peerId} for ${taskId}:`, result);
        }
      } else {
        ws.send(JSON.stringify({ type: 'error', message: 'unknown type' }));
      }
    } catch (err) {
      console.error('Invalid WS message', err);
      ws.send(JSON.stringify({ type: 'error', message: 'invalid message' }));
    }
  });

  ws.on('close', () => {
    // cleanup peer record
    if (ws.peerId && peers.has(ws.peerId)) {
      console.log('Peer disconnected:', ws.peerId);
      peers.delete(ws.peerId);
    }
  });
});

// simple ping/pong to catch dead connections
setInterval(() => {
  wss.clients.forEach(ws => {
    if (!ws.isAlive) {
      if (ws.peerId && peers.has(ws.peerId)) peers.delete(ws.peerId);
      return ws.terminate();
    }
    ws.isAlive = false;
    ws.ping();
  });
}, 30000);

/* -------------------------
   Utility: Haversine distance (km)
   ------------------------- */
function haversineKm(lat1, lon1, lat2, lon2) {
  if ([lat1, lon1, lat2, lon2].some(v => typeof v !== 'number')) return Infinity;
  const R = 6371; // km
  const toRad = v => (v * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

/* -------------------------
   REST API
   ------------------------- */

/**
 * GET /peers
 * optional query params:
 *   lat, lon, radiusKm  -> filter by proximity if meta has lat/lon
 *
 * returns list of peers with meta and lastSeen
 */
app.get('/peers', (req, res) => {
  const lat = req.query.lat ? parseFloat(req.query.lat) : null;
  const lon = req.query.lon ? parseFloat(req.query.lon) : null;
  const radiusKm = req.query.radiusKm ? parseFloat(req.query.radiusKm) : null;

  const now = Date.now();
  const list = [];

  for (const [peerId, entry] of peers.entries()) {
    const { meta, lastSeen, ip } = entry;
    const ageSec = (now - lastSeen) / 1000;
    let distanceKm = null;
    if (lat !== null && lon !== null && meta && typeof meta.lat === 'number' && typeof meta.lon === 'number') {
      distanceKm = haversineKm(lat, lon, meta.lat, meta.lon);
    }
    list.push({
      peerId,
      meta,
      lastSeen,
      ageSec,
      ip,
      distanceKm
    });
  }

  let filtered = list;
  if (radiusKm !== null && lat !== null && lon !== null) {
    filtered = list.filter(p => p.distanceKm !== null && p.distanceKm <= radiusKm);
  }

  // sort by lastSeen (most recent first)
  filtered.sort((a,b) => a.lastSeen - b.lastSeen ? b.lastSeen - a.lastSeen : 0);
  res.json({ count: filtered.length, peers: filtered });
});

/**
 * POST /task
 * multipart/form-data:
 *   - file (optional) : the file to be distributed (task input)
 *   - peers: optional JSON array of peerIds to send to; if absent, broadcast to all
 *   - task: JSON string describing the task { type: "processFile", action: "wordcount" ...}
 *
 * The endpoint will:
 *  - create a taskId
 *  - send a {type:'task', taskId, task, file:{...}} message to selected peers via websocket
 *  - wait up to timeoutSeconds for responses via ws messages and return collected results
 */
app.post('/task', upload.single('file'), async (req, res) => {
  try {
    const task = req.body.task ? JSON.parse(req.body.task) : { type: 'generic' };
    let targetPeers = null;
    if (req.body.peers) {
      try { targetPeers = JSON.parse(req.body.peers); } catch(e) { targetPeers = null; }
    }

    // choose peers
    let selected = [];
    for (const [peerId, entry] of peers.entries()) {
      selected.push(peerId);
    }
    if (Array.isArray(targetPeers) && targetPeers.length) {
      selected = selected.filter(id => targetPeers.includes(id));
    }

    if (!selected.length) {
      return res.status(400).json({ message: 'No peers available' });
    }

    const file = req.file ? {
      name: req.file.originalname,
      mime: req.file.mimetype,
      size: req.file.size,
      dataBase64: req.file.buffer.toString('base64')
    } : null;

    const taskId = uuidv4();
    tasks.set(taskId, { sentTo: selected.slice(), responses: {}, createdAt: Date.now() });

    // send to each selected peer
    for (const peerId of selected) {
      const entry = peers.get(peerId);
      if (!entry || !entry.ws || entry.ws.readyState !== WebSocket.OPEN) continue;

      const msg = {
        type: 'task',
        taskId,
        task,
        file: file ? { name: file.name, mime: file.mime, size: file.size, dataBase64: file.dataBase64 } : null
      };

      try {
        entry.ws.send(JSON.stringify(msg));
      } catch (e) {
        console.warn('failed to send to', peerId, e);
      }
    }

    // wait for responses up to timeout
    const timeoutSeconds = parseInt(req.query.timeoutSeconds || '12', 10);
    const pollIntervalMs = 300;
    const deadline = Date.now() + (timeoutSeconds * 1000);

    while (Date.now() < deadline) {
      const t = tasks.get(taskId);
      const responded = Object.keys(t.responses).length;
      if (responded >= selected.length) break;
      await new Promise(r => setTimeout(r, pollIntervalMs));
    }

    const final = tasks.get(taskId);
    // optionally you could remove task after some time
    // tasks.delete(taskId);

    res.json({
      taskId,
      sentTo: selected,
      responses: final.responses,
      missing: final.sentTo.filter(id => !(id in final.responses))
    });
  } catch (err) {
    console.error('task error', err);
    res.status(500).json({ message: 'internal error' });
  }
});

/**
 * POST /register
 * alternative HTTP registration: (optionally peers can register via HTTP instead of ws)
 * body: { peerId, meta:{name,lat,lon,tags}}
 */
app.post('/register', (req, res) => {
  const { peerId, meta } = req.body;
  if (!peerId) return res.status(400).json({ message: 'peerId required' });

  peers.set(peerId, {
    ws: null,
    meta: meta || {},
    lastSeen: Date.now(),
    ip: null
  });

  res.json({ ok: true });
});

/* -------------------------
   start server
   ------------------------- */
const PORT = process.env.PORT ? parseInt(process.env.PORT) : 9000;
server.listen(PORT, () => {
  console.log(`HTTP + WS server running on http://localhost:${PORT}`);
});
