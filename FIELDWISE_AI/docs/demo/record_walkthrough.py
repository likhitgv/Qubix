"""Record a captioned walkthrough of the running KAIRO app, Home page to About page, as a video under 30 s.

record : drives headless Chrome (or Edge) over the DevTools protocol with a visible cursor through all
         eight pages and saves the raw screen frames plus a timeline of what happened when.
compose: cuts out the loading pauses, fits each page into its time slot, burns in English captions,
         a progress bar and the AI-use mark, and writes an H.264 MP4 and a matching .srt file.

Run (KAIRO must already be running):
  py -3.11 docs/demo/record_walkthrough.py --url http://localhost:8501/
  py -3.11 docs/demo/record_walkthrough.py --compose-only        # re-compose from the last raw recording

Needs: websockets, av (PyAV), pillow, numpy. No ffmpeg install is needed (PyAV bundles it).
Note: the run builds one recommendation, so KAIRO saves one plan to its local SQLite file.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import bisect
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import av
import numpy as np
import websockets
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

# ----------------------------------------------------------------- the walkthrough (edit captions here)
FIELD = {"district": "Dharwad", "soil": "Red soil"}   # water stays "Rainfed" (the default)

PAGES = [  # (nav label, caption, seconds in the final video)
    ("Home", "KAIRO: crop plans from NASA weather records", 3.1),
    ("Your field", "Add your field: district, soil type and water source", 7.4),
    ("Recommendation", "Get the best two-season crop plan, with the reasons", 5.4),
    ("Weather", "See NASA POWER rainfall and temperature for the area", 3.4),
    ("Map", "NASA weather grid points cover all of India", 3.0),
    ("Rotation health", "Check rotation health across crop families", 2.5),
    ("Summary", "Read a plain-language summary of the plan", 2.5),
    ("About", "Decision support: check with a local agronomist", 2.5),
]
HEADERS = {  # text that proves a page has rendered
    "Home": "Plan your next crop with NASA weather records",
    "Your field": "Four short questions",
    "Recommendation": "Recommended for this season",
    "Weather": "NASA estimates for the area",
    "Map": "Where KAIRO has weather data",
    "Rotation health": "How varied each option is",
    "Summary": "Plain-language summary",
    "About": "About KAIRO",
}
AI_MARK = "AI-assisted: built with Claude  ·  Weather data: NASA POWER"

# ----------------------------------------------------------------- geometry and colours
VW, VH, DPR = 1280, 624, 1.5          # browser viewport in CSS px -> 1920 x 936 device px
OUT_W, OUT_H, FPS = 1920, 1080, 30
SHOT_H = int(VH * DPR)                 # 936
BAND_H = OUT_H - SHOT_H                # 144 px caption band under the screen
FOREST, WHEAT, CREAM, SAGE = (31, 77, 43), (227, 168, 43), (255, 252, 243), (187, 204, 178)
XFADE = 0.18                           # seconds of cross-fade when the page changes

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# Page helpers injected into the app: a drawn cursor (headless Chrome has none), click ripple,
# element lookup and eased scrolling of Streamlit's scroll container.
HELPERS_JS = r"""
(() => {
  if (window.__kairoDemo) return true;
  window.__kairoDemo = true;
  const c = document.createElement('div');
  c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M5 2.5 L5 19.5 L9.6 15.2 L12.8 21.8 L15.6 20.5 L12.5 14.1 L18.8 14.1 Z" fill="#1d1d1b" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, {position:'fixed', left:'-6px', top:'-3px', zIndex:2147483647, pointerEvents:'none',
    filter:'drop-shadow(0 2px 3px rgba(0,0,0,.35))', transform:'translate(900px,420px)'});
  document.body.appendChild(c);
  window.__cur = [900, 420];
  const ease = k => k < .5 ? 4*k*k*k : 1 - Math.pow(-2*k + 2, 3) / 2;
  window.__move = (x, y, ms) => new Promise(res => {
    const [x0, y0] = window.__cur, t0 = performance.now();
    const step = now => {
      const k = Math.min(1, (now - t0) / ms), e = ease(k);
      const cx = x0 + (x - x0) * e, cy = y0 + (y - y0) * e;
      c.style.transform = `translate(${cx}px,${cy}px)`; window.__cur = [cx, cy];
      k < 1 ? requestAnimationFrame(step) : res(true);
    };
    requestAnimationFrame(step);
  });
  window.__ripple = (x, y) => {
    const r = document.createElement('div');
    Object.assign(r.style, {position:'fixed', left:(x-20)+'px', top:(y-20)+'px', width:'40px', height:'40px',
      borderRadius:'50%', background:'rgba(227,168,43,.55)', zIndex:2147483646, pointerEvents:'none',
      transform:'scale(.3)', opacity:'1', transition:'transform .5s ease-out, opacity .5s ease-out'});
    document.body.appendChild(r);
    requestAnimationFrame(() => requestAnimationFrame(() => { r.style.transform = 'scale(1.5)'; r.style.opacity = '0'; }));
    setTimeout(() => r.remove(), 700);
  };
  window.__scroller = () => {
    const cands = [...document.querySelectorAll('[data-testid="stMain"], [data-testid="stAppViewContainer"], section.main, .main')];
    for (const s of cands) {
      const oy = getComputedStyle(s).overflowY;
      if (s.scrollHeight > s.clientHeight + 4 && (oy === 'auto' || oy === 'scroll')) return s;
    }
    return document.scrollingElement;
  };
  window.__scrollTo = (top, ms) => new Promise(res => {
    const s = window.__scroller(), y0 = s.scrollTop, t0 = performance.now();
    const target = Math.max(0, Math.min(top, s.scrollHeight - s.clientHeight));
    if (ms <= 0) { s.scrollTop = target; return res(s.scrollTop); }
    const step = now => {
      const k = Math.min(1, (now - t0) / ms), e = k < .5 ? 2*k*k : 1 - Math.pow(-2*k + 2, 2) / 2;
      s.scrollTop = y0 + (target - y0) * e;
      k < 1 ? requestAnimationFrame(step) : res(s.scrollTop);
    };
    requestAnimationFrame(step);
  });
  window.__scrollTop = () => window.__scroller().scrollTop;
  // Find an element; returns its centre in viewport CSS px plus the scroll offset needed to bring it into view.
  window.__find = (sel, text, opts) => {
    opts = opts || {};
    let els = [...document.querySelectorAll(sel)].filter(e => e.getClientRects().length > 0);
    if (text !== null && text !== undefined) {
      els = els.filter(e => opts.contains ? e.innerText.includes(text) : e.innerText.trim() === text);
    }
    const e = els[opts.index || 0];
    if (!e) return null;
    const r = e.getBoundingClientRect(), vh = window.innerHeight;
    return {x: r.left + r.width / 2, y: r.top + r.height / 2, top: r.top, bottom: r.bottom, vh: vh,
            scroll: window.__scrollTop()};
  };
  window.__idle = () => {
    const sw = document.querySelector('[data-testid="stStatusWidget"]');
    const running = sw && /running|stop/i.test(sw.innerText || '');
    return !running && !document.querySelector('[data-stale="true"]') && !!document.querySelector('[data-testid="stApp"]');
  };
  return true;
})()
"""


# ----------------------------------------------------------------- DevTools protocol client
class CDP:
    def __init__(self, ws):
        self.ws, self.next_id, self.pending, self.handlers = ws, 0, {}, {}

    async def reader(self) -> None:
        async for raw in self.ws:
            msg = json.loads(raw)
            if "id" in msg:
                fut = self.pending.pop(msg["id"], None)
                if fut and not fut.done():
                    fut.set_result(msg)
            elif msg.get("method") in self.handlers:
                self.handlers[msg["method"]](msg.get("params", {}))

    async def send(self, method: str, **params):
        self.next_id += 1
        fut = asyncio.get_running_loop().create_future()
        self.pending[self.next_id] = fut
        await self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        msg = await asyncio.wait_for(fut, 60)
        if "error" in msg:
            raise RuntimeError(f"{method}: {msg['error']}")
        return msg.get("result", {})

    async def js(self, expr: str, await_promise: bool = True):
        res = await self.send("Runtime.evaluate", expression=expr, awaitPromise=await_promise, returnByValue=True)
        if "exceptionDetails" in res:
            raise RuntimeError(f"JS error: {res['exceptionDetails']}")
        return res.get("result", {}).get("value")


class Session:
    """High-level actions: cursor moves, clicks, typing, scrolling, waiting for Streamlit."""

    def __init__(self, cdp: CDP, raw: Path):
        self.cdp, self.raw = cdp, raw
        self.frames: list[tuple[float, str]] = []
        self.segments: list[dict] = []
        self._seg = None
        cdp.handlers["Page.screencastFrame"] = self._on_frame

    def _on_frame(self, p: dict) -> None:
        ts = p.get("metadata", {}).get("timestamp") or time.time()
        name = f"f{len(self.frames):05d}.jpg"
        (self.raw / name).write_bytes(base64.b64decode(p["data"]))
        self.frames.append((ts, name))
        asyncio.ensure_future(self.cdp.send("Page.screencastFrameAck", sessionId=p["sessionId"]))

    # segments ------------------------------------------------------------
    def start(self, page: int) -> None:
        self._seg = {"page": page, "t0": time.time()}

    def stop(self) -> None:
        if self._seg:
            self._seg["t1"] = time.time()
            self.segments.append(self._seg)
            self._seg = None

    # waiting -------------------------------------------------------------
    async def idle(self, contains: str | None = None, settle: float = 0.35, timeout: float = 40) -> None:
        await asyncio.sleep(0.45)
        end = time.time() + timeout
        while time.time() < end:
            ok = await self.cdp.js("window.__idle()", False)
            if ok and contains:
                ok = await self.cdp.js(f"document.body.innerText.includes({json.dumps(contains)})", False)
            if ok:
                await asyncio.sleep(settle)
                if await self.cdp.js("window.__idle()", False):
                    return
            await asyncio.sleep(0.15)
        raise TimeoutError(f"KAIRO did not finish rendering ({contains!r})")

    # pointer -------------------------------------------------------------
    async def find(self, sel: str, text: str | None, **opts) -> dict:
        for _ in range(60):
            box = await self.cdp.js(f"window.__find({json.dumps(sel)}, {json.dumps(text)}, {json.dumps(opts)})", False)
            if box:
                return box
            await asyncio.sleep(0.2)
        raise LookupError(f"Element not found: {sel} {text!r}")

    async def scroll_to(self, top: float, ms: int = 600) -> None:
        await self.cdp.js(f"window.__scrollTo({top}, {ms})")

    async def bring_into_view(self, sel: str, text: str | None, ms: int = 500, margin: float = 90, **opts) -> dict:
        box = await self.find(sel, text, **opts)
        if box["top"] < margin or box["bottom"] > box["vh"] - margin:
            await self.scroll_to(box["scroll"] + box["top"] - box["vh"] * 0.35, ms)
            box = await self.find(sel, text, **opts)
        return box

    async def move(self, x: float, y: float, ms: int = 550) -> None:
        await self.cdp.js(f"window.__move({x}, {y}, {ms})")
        await self.cdp.send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)

    async def click(self, sel: str, text: str | None, move_ms: int = 550, pause: float = 0.12, **opts) -> None:
        box = await self.bring_into_view(sel, text, **opts)
        await self.move(box["x"], box["y"], move_ms)
        await asyncio.sleep(pause)
        await self.cdp.js(f"window.__ripple({box['x']}, {box['y']})", False)
        for kind in ("mousePressed", "mouseReleased"):
            await self.cdp.send("Input.dispatchMouseEvent", type=kind, x=box["x"], y=box["y"], button="left", clickCount=1)

    async def type(self, text: str, delay: float = 0.07) -> None:
        for ch in text:
            await self.cdp.send("Input.insertText", text=ch)
            await asyncio.sleep(delay)

    async def key_enter(self) -> None:
        base = dict(key="Enter", code="Enter", windowsVirtualKeyCode=13, nativeVirtualKeyCode=13)
        await self.cdp.send("Input.dispatchKeyEvent", type="keyDown", text="\r", **base)
        await self.cdp.send("Input.dispatchKeyEvent", type="keyUp", **base)

    async def nav(self, label: str) -> None:
        """Click a page in KAIRO's top navigation (the first segmented control)."""
        await self.scroll_to(0, 380)
        await self.click('[data-testid="stButtonGroup"]:first-of-type button, [data-testid="stButtonGroup"] button',
                         label, move_ms=520)


# ----------------------------------------------------------------- the scripted journey
NAV_SEL = '[data-testid="stButtonGroup"] button'


async def journey(s: Session) -> None:
    j = s.cdp.js
    # Off camera: open the app on Home with the cursor parked.
    await s.idle("KAIRO")
    await j(HELPERS_JS, False)
    await s.click(NAV_SEL, "Home", move_ms=10)
    await s.idle(HEADERS["Home"], settle=0.8)
    await s.move(900, 470, 10)
    await asyncio.sleep(0.4)

    # 1 Home -> click the call to action
    s.start(0)
    await asyncio.sleep(0.9)
    await s.click("button", "Add your field details", move_ms=900, pause=0.25)
    await asyncio.sleep(0.15)
    s.stop()
    await s.idle(HEADERS["Your field"], settle=1.6)   # the map preview needs a moment to draw

    # 2 Your field: district, soil, water (Rainfed is already chosen), then Get recommendation
    s.start(1)
    await asyncio.sleep(0.3)
    district_box = 'input[aria-label="District"]'
    await s.click(district_box, None, move_ms=650)
    await asyncio.sleep(0.2)
    await j(f"document.querySelector({json.dumps(district_box)}).select()", False)
    await s.type(FIELD["district"][:5])
    await asyncio.sleep(0.35)
    try:
        await s.click('[role="option"]', FIELD["district"], move_ms=380, pause=0.1)
    except LookupError:
        await s.key_enter()
    s.stop()
    await s.idle(None, settle=1.6)
    value = await j(f"document.querySelector({json.dumps(district_box)}).value", False)
    if value != FIELD["district"]:
        raise RuntimeError(f"District not selected (box shows {value!r})")
    s.start(1)
    await asyncio.sleep(0.2)
    await s.click(NAV_SEL, FIELD["soil"], move_ms=650, pause=0.15)
    s.stop()
    await s.idle(None, settle=0.5)
    s.start(1)
    box = await s.bring_into_view(NAV_SEL, "Rainfed", ms=650)
    await s.move(box["x"], box["y"], 450)
    await asyncio.sleep(0.35)
    await s.click("button", "Get recommendation", move_ms=600, pause=0.2)
    await asyncio.sleep(0.12)
    s.stop()
    await s.idle(HEADERS["Recommendation"], settle=0.6)
    await s.scroll_to(0, 0)
    await asyncio.sleep(0.25)

    # 3 Recommendation: best option, then scroll to the alternatives and the weather behind it
    s.start(2)
    await s.move(700, 300, 700)
    await asyncio.sleep(1.0)
    alt = await s.find("h3", "Two alternatives", contains=True)
    await s.scroll_to(alt["scroll"] + alt["top"] - 40, 1300)
    await asyncio.sleep(1.0)
    await s.scroll_to(0, 420)
    await s.click(NAV_SEL, "Weather", move_ms=520)
    await asyncio.sleep(0.1)
    s.stop()
    await s.idle(HEADERS["Weather"], settle=0.9)

    # 4 Weather records
    s.start(3)
    await s.move(800, 360, 600)
    await asyncio.sleep(0.4)
    await s.scroll_to(250, 900)
    await asyncio.sleep(0.9)
    await s.scroll_to(0, 380)
    await s.click(NAV_SEL, "Map", move_ms=480)
    await asyncio.sleep(0.1)
    s.stop()
    await s.idle(HEADERS["Map"], settle=2.4)          # grid layer and map tiles

    # 5 Map of NASA grid coverage
    s.start(4)
    await s.move(760, 420, 700)
    await asyncio.sleep(1.2)
    await s.click(NAV_SEL, "Rotation health", move_ms=520)
    await asyncio.sleep(0.1)
    s.stop()
    await s.idle(HEADERS["Rotation health"], settle=0.6)

    # 6 Rotation health
    s.start(5)
    await s.move(640, 330, 500)
    await asyncio.sleep(0.6)
    await s.click(NAV_SEL, "Summary", move_ms=480)
    await asyncio.sleep(0.1)
    s.stop()
    await s.idle(HEADERS["Summary"], settle=0.6)

    # 7 Plain-language summary
    s.start(6)
    await s.move(620, 330, 500)
    await asyncio.sleep(0.6)
    await s.click(NAV_SEL, "About", move_ms=480)
    await asyncio.sleep(0.1)
    s.stop()
    await s.idle(HEADERS["About"], settle=0.6)

    # 8 About: what it is, limits, use of AI
    s.start(7)
    await s.move(700, 360, 500)
    await asyncio.sleep(0.3)
    await s.scroll_to(330, 1000)
    await asyncio.sleep(0.9)
    s.stop()


# ----------------------------------------------------------------- recording
def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def record(url: str, raw: Path) -> None:
    exe = next((p for p in CHROME_PATHS if Path(p).is_file()), None)
    if not exe:
        raise SystemExit("Chrome or Edge not found.")
    if raw.exists():
        shutil.rmtree(raw)
    raw.mkdir(parents=True)
    profile = Path(tempfile.mkdtemp(prefix="kairo_demo_chrome_"))
    port = _free_port()
    proc = subprocess.Popen([
        exe, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
        f"--window-size={VW},{VH}", "--hide-scrollbars", "--mute-audio", "--no-first-run",
        "--no-default-browser-check", "--disable-extensions", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as resp:
                    pages = [t for t in json.load(resp) if t.get("type") == "page"]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]
                    break
            except OSError:
                pass
            await asyncio.sleep(0.1)
        if not ws_url:
            raise SystemExit("Could not connect to the browser.")
        async with websockets.connect(ws_url, max_size=None, ping_interval=None) as ws:
            cdp = CDP(ws)
            reader = asyncio.create_task(cdp.reader())
            s = Session(cdp, raw)
            await cdp.send("Page.enable")
            await cdp.send("Runtime.enable")
            await cdp.send("Emulation.setDeviceMetricsOverride", width=VW, height=VH, deviceScaleFactor=DPR, mobile=False)
            await cdp.send("Emulation.setFocusEmulationEnabled", enabled=True)
            await cdp.send("Page.navigate", url=url)
            await asyncio.sleep(2.0)
            await cdp.js("new Promise(r => { const f = () => document.querySelector('[data-testid=\"stApp\"]') ? r(1) : setTimeout(f, 100); f(); })")
            await cdp.js(HELPERS_JS, False)
            await cdp.send("Page.startScreencast", format="jpeg", quality=92,
                           maxWidth=int(VW * DPR), maxHeight=int(VH * DPR), everyNthFrame=1)
            try:
                await journey(s)
            except Exception:
                shot = await cdp.send("Page.captureScreenshot", format="png")
                (raw / "error.png").write_bytes(base64.b64decode(shot["data"]))
                print(f"failed; screenshot at {raw / 'error.png'}")
                raise
            await asyncio.sleep(0.3)
            await cdp.send("Page.stopScreencast")
            reader.cancel()
        (raw / "timeline.json").write_text(json.dumps({"frames": s.frames, "segments": s.segments}, indent=1))
        print(f"recorded {len(s.frames)} frames, {len(s.segments)} segments")
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


# ----------------------------------------------------------------- composing
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    file = {"sans": "calibri.ttf", "sansb": "calibrib.ttf", "serifb": "georgiab.ttf"}[name]
    return ImageFont.truetype(f"C:/Windows/Fonts/{file}", size)


def _band(page: int) -> np.ndarray:
    """Caption band for one page: caption, step label, AI-use mark."""
    img = Image.new("RGB", (OUT_W, BAND_H), FOREST)
    d = ImageDraw.Draw(img)
    caption = PAGES[page][1]
    f = _font("sansb", 50)
    d.text(((OUT_W - d.textlength(caption, font=f)) / 2, 30), caption, font=f, fill=CREAM)
    small = _font("sans", 24)
    step = f"Step {page + 1} of {len(PAGES)}  ·  {PAGES[page][0]}"
    d.text((40, BAND_H - 40), step, font=small, fill=SAGE)
    d.text((OUT_W - 40 - d.textlength(AI_MARK, font=small), BAND_H - 40), AI_MARK, font=small, fill=SAGE)
    kf = _font("serifb", 30)
    d.text((40, 30), "KAIRO", font=kf, fill=WHEAT)
    return np.asarray(img)


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def compose(raw: Path, out_mp4: Path) -> None:
    data = json.loads((raw / "timeline.json").read_text())
    frames = data["frames"]
    stamps = [f[0] for f in frames]
    cache: dict[str, np.ndarray] = {}

    def frame_at(t: float) -> np.ndarray:
        i = max(0, bisect.bisect_right(stamps, t) - 1)
        name = frames[i][1]
        if name not in cache:
            img = Image.open(raw / name).convert("RGB")
            if img.size != (OUT_W, SHOT_H):
                img = img.resize((OUT_W, SHOT_H), Image.LANCZOS)
            cache[name] = np.asarray(img)
            if len(cache) > 400:
                cache.pop(next(iter(cache)))
        return cache[name]

    # Map output time -> (page, raw time). Each page's segments share its slot, at one speed.
    plan = []  # (out_start, out_end, page, raw_t0, speed)
    t_out = 0.0
    for page, (_, _, secs) in enumerate(PAGES):
        segs = [g for g in data["segments"] if g["page"] == page]
        raw_total = sum(g["t1"] - g["t0"] for g in segs)
        speed = raw_total / secs
        for g in segs:
            dur = (g["t1"] - g["t0"]) / speed
            plan.append((t_out, t_out + dur, page, g["t0"], speed))
            t_out += dur
        print(f"  {PAGES[page][0]:<16} raw {raw_total:5.2f}s -> {secs:4.1f}s  (x{speed:.2f})")
    total = t_out
    n_frames = int(round(total * FPS))
    bands = [_band(p) for p in range(len(PAGES))]
    page_start = {p: next(a for a, _, pg, _, _ in plan if pg == p) for p in range(len(PAGES))}

    def shot(t: float) -> tuple[np.ndarray, int]:
        for a, b, page, r0, speed in plan:
            if t < b or (a, b) == plan[-1][:2]:
                return frame_at(r0 + (min(t, b) - a) * speed), page
        raise ValueError(t)

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(out_mp4), mode="w", options={"movflags": "+faststart"})
    stream = container.add_stream("libx264", rate=FPS)
    stream.width, stream.height, stream.pix_fmt = OUT_W, OUT_H, "yuv420p"
    stream.options = {"crf": "19", "preset": "medium", "profile": "high", "tune": "stillimage"}
    canvas = np.zeros((OUT_H, OUT_W, 3), np.uint8)
    for k in range(n_frames):
        t = (k + 0.5) / FPS
        img, page = shot(t)
        since = t - page_start[page]
        if page > 0 and since < XFADE:                      # soft cut between pages
            prev, _ = shot(page_start[page] - 1e-3)
            a = since / XFADE
            img = (prev.astype(np.float32) * (1 - a) + img.astype(np.float32) * a).astype(np.uint8)
        canvas[:SHOT_H] = img
        canvas[SHOT_H:] = bands[page]
        prog = int(OUT_W * (k + 1) / n_frames)              # journey progress bar
        canvas[SHOT_H:SHOT_H + 5, :prog] = WHEAT
        frame = av.VideoFrame.from_ndarray(canvas, format="rgb24")
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()

    srt = []
    for i, p in enumerate(range(len(PAGES)), 1):
        a = page_start[p]
        b = page_start[p + 1] if p + 1 < len(PAGES) else total
        srt.append(f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{PAGES[p][1]}\n")
    out_mp4.with_suffix(".srt").write_text("\n".join(srt), encoding="utf-8")
    print(f"video: {out_mp4} ({n_frames / FPS:.2f}s, {out_mp4.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8501/")
    ap.add_argument("--raw", type=Path, default=Path(tempfile.gettempdir()) / "kairo_walkthrough_raw")
    ap.add_argument("--out", type=Path, default=HERE / "KAIRO_Walkthrough_30s.mp4")
    ap.add_argument("--compose-only", action="store_true")
    args = ap.parse_args()
    total = sum(p[2] for p in PAGES)
    if total > 30:
        raise SystemExit(f"Page slots add up to {total}s; Space Apps allows 30 s at most.")
    if not args.compose_only:
        asyncio.run(record(args.url, args.raw))
    compose(args.raw, args.out)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
