"""
A way for people to touch the building without a box on the ground.

The simulator can only be written to, never read from, so nobody can click the
simulated tower and have it reach us. And a physical sensor in the plaza is the
single riskiest part of the whole project to get approved.

This is the third option: a page on your phone with one big button. Point a
phone at the URL, press, and a branch grows on the building.

WHY THIS MIGHT BE THE VERSION THAT ACTUALLY HAPPENS

It removes the object from the plaza entirely. Nothing to trip over, nothing to
power, nothing to steal, nothing to stand beside all evening, no liability for a
thing strangers put their hands on. The crowd already carries the hardware.

It also scales in a way a single box never could: forty people can touch the
building at the same time, and the tree they grow is genuinely theirs.

SECURITY, SUCH AS IT IS

It binds to 127.0.0.1 by default -- your machine only, nothing exposed. Opening
it to a room is a deliberate act (pass a host), and it should stay a decision
somebody makes on purpose rather than a default. It accepts exactly two verbs,
holds no state about anybody, and has nothing worth attacking: the worst a
hostile visitor can do is grow a branch.
"""

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1,user-scalable=no">
<title>King of the Charles</title>
<style>
 html,body{height:100%;margin:0;background:#06070b;color:#e6eaf2;
   font:16px/1.4 -apple-system,system-ui,sans-serif;-webkit-user-select:none;user-select:none;
   -webkit-tap-highlight-color:transparent;overscroll-behavior:none}
 main{height:100%;display:flex;flex-direction:column}
 header{padding:1rem 1rem .4rem;text-align:center}
 h1{margin:0;font-size:1rem;font-weight:600;letter-spacing:.16em}
 header p{margin:.3rem 0 0;font-size:.78rem;color:#6c7484}
 #pick{flex:1;display:grid;grid-template-columns:1fr 1fr;gap:.6rem;padding:.6rem}
 #pick button{border:0;border-radius:14px;color:#fff;font-size:1.15rem;font-weight:600;
   letter-spacing:.04em;cursor:pointer;transition:transform .08s}
 #pick button:active{transform:scale(.96)}
 #row{flex:1;display:none;flex-direction:column;align-items:center;justify-content:center;gap:1rem;padding:1rem}
 #oar{width:min(80vw,22rem);aspect-ratio:1;border-radius:50%;border:0;color:#fff;
   font-size:1.5rem;font-weight:700;letter-spacing:.1em;cursor:pointer;transition:transform .06s}
 #oar:active{transform:scale(.93)}
 #n{font-variant-numeric:tabular-nums;font-size:.9rem;color:#6c7484}
 #back{background:none;border:0;color:#565e6e;font-size:.8rem;text-decoration:underline;cursor:pointer}
</style>
<main>
  <header><h1>KING OF THE CHARLES</h1><p id=sub>pick your crew</p></header>
  <div id=pick></div>
  <div id=row>
    <button id=oar>ROW</button>
    <p id=n>0 strokes</p>
    <button id=back>change crew</button>
  </div>
</main>
<script>
const CREWS=[["HARVARD","#a51c30"],["MIT","#8b929c"],["NORTHEASTERN","#78143c"],["BU","#e07018"]];
let lane=null,n=0;
const pick=document.getElementById('pick'),row=document.getElementById('row'),
      oar=document.getElementById('oar'),sub=document.getElementById('sub');
CREWS.forEach(([name,col],i)=>{
  const b=document.createElement('button');
  b.textContent=name; b.style.background=col;
  b.onclick=()=>{lane=i;n=0;document.getElementById('n').textContent='0 strokes';
    oar.style.background=col;sub.textContent=name;
    pick.style.display='none';row.style.display='flex';};
  pick.appendChild(b);
});
function stroke(){
  if(lane===null)return;
  document.getElementById('n').textContent=(++n)+' strokes';
  if(navigator.vibrate)navigator.vibrate(12);
  fetch('/row?lane='+lane,{method:'POST'}).catch(()=>{});
}
oar.addEventListener('click',stroke);
document.getElementById('back').onclick=()=>{
  lane=null;row.style.display='none';pick.style.display='grid';sub.textContent='pick your crew';};
</script>
"""


class Control:
    """A tiny web control. Never blocks the drawing loop; just collects touches."""

    def __init__(self, host="127.0.0.1", port=8750):
        self.pending = 0          # generic touches waiting to be handed over
        self.total = 0
        self.strokes = [0, 0, 0, 0]   # rowing, per crew, since last asked
        self.rowed = [0, 0, 0, 0]     # rowing, per crew, all evening
        self._lock = threading.Lock()
        self.host, self.port = host, port
        self.url = f"http://{host}:{port}/"
        self._server = None
        try:
            outer = self

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *a):
                    pass          # silence: this shares a terminal with the app

                def do_GET(self):
                    body = PAGE.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def do_POST(self):
                    u = urllib.parse.urlparse(self.path)
                    if u.path == "/touch":
                        with outer._lock:
                            outer.pending += 1
                            outer.total += 1
                        self.send_response(204)
                    elif u.path == "/row":
                        q = urllib.parse.parse_qs(u.query)
                        try:
                            lane = int(q.get("lane", ["-1"])[0])
                        except ValueError:
                            lane = -1
                        if 0 <= lane < 4:
                            with outer._lock:
                                outer.strokes[lane] += 1
                                outer.rowed[lane] += 1
                                outer.pending += 1
                                outer.total += 1
                            self.send_response(204)
                        else:
                            self.send_response(400)
                    else:
                        self.send_response(404)
                    self.end_headers()

            self._server = ThreadingHTTPServer((host, port), Handler)
            threading.Thread(target=self._server.serve_forever, daemon=True).start()
            self.available = True
        except Exception:
            self.available = False

    def take(self):
        """How many people pressed since last asked. Clears the count."""
        with self._lock:
            n, self.pending = self.pending, 0
        return n

    def take_strokes(self):
        """Strokes per crew since last asked. Clears them."""
        with self._lock:
            s, self.strokes = self.strokes, [0, 0, 0, 0]
        return s

    def close(self):
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
