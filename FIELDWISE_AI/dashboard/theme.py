"""KAIRO visual theme: dark glass UI with an emerald/cyan accent."""

import streamlit as st

ACCENT = "#34d399"
ACCENT_2 = "#22d3ee"
WARN = "#fbbf24"
BAD = "#f87171"

PLOT_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#cbd5e1"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", y=1.12),
)

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
.stApp {
  background:
    radial-gradient(1100px 600px at 12% -10%, rgba(52,211,153,.14), transparent 60%),
    radial-gradient(900px 500px at 95% 0%, rgba(34,211,238,.12), transparent 55%),
    #070b12;
  color: #e2e8f0;
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
section[data-testid="stSidebar"] {
  background: rgba(10,15,25,.85);
  border-right: 1px solid rgba(148,163,184,.12);
  backdrop-filter: blur(14px);
}
.block-container { padding-top: 2rem; max-width: 1200px; }

.kairo-brand { font-size: 1.9rem; font-weight: 800; letter-spacing: -.03em;
  background: linear-gradient(90deg, #34d399, #22d3ee); -webkit-background-clip: text;
  -webkit-text-fill-color: transparent; margin: 0; }
.kairo-tag { color: #94a3b8; font-size: .85rem; margin-top: -2px; }

.hero { padding: 2.2rem 2rem; border-radius: 22px; margin-bottom: 1.4rem;
  background: linear-gradient(135deg, rgba(52,211,153,.14), rgba(34,211,238,.08));
  border: 1px solid rgba(148,163,184,.16); }
.hero h1 { font-size: clamp(1.6rem, 4.2vw, 2.4rem); font-weight: 800; letter-spacing: -.035em; margin: 0 0 .5rem; color: #f8fafc; }
.hero p { color: #b6c2d3; font-size: 1.05rem; max-width: 720px; margin: 0; }

.glass { background: rgba(15,23,42,.62); border: 1px solid rgba(148,163,184,.14);
  border-radius: 18px; padding: 1.15rem 1.25rem; backdrop-filter: blur(10px);
  transition: border-color .2s, transform .2s; }
.glass:hover { border-color: rgba(52,211,153,.45); transform: translateY(-2px); }

.metric-label { color: #94a3b8; font-size: .75rem; text-transform: uppercase; letter-spacing: .08em; }
.metric-value { color: #f8fafc; font-size: 1.9rem; font-weight: 700; letter-spacing: -.02em; }
.metric-sub { color: #64748b; font-size: .78rem; }

.pill { display: inline-block; padding: .18rem .6rem; border-radius: 999px; font-size: .72rem;
  font-weight: 600; margin-right: .3rem; border: 1px solid transparent; }
.pill-green { background: rgba(52,211,153,.14); color: #6ee7b7; border-color: rgba(52,211,153,.35); }
.pill-amber { background: rgba(251,191,36,.12); color: #fcd34d; border-color: rgba(251,191,36,.35); }
.pill-red { background: rgba(248,113,113,.12); color: #fca5a5; border-color: rgba(248,113,113,.35); }
.pill-blue { background: rgba(34,211,238,.12); color: #67e8f9; border-color: rgba(34,211,238,.35); }

.rank-badge { width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center;
  justify-content: center; font-weight: 800; color: #04210f;
  background: linear-gradient(135deg, #34d399, #22d3ee); }
.crop-chip { display:inline-block; padding:.5rem .9rem; border-radius:12px; margin:.2rem .4rem .2rem 0;
  background: rgba(30,41,59,.8); border:1px solid rgba(148,163,184,.18); font-weight:600; }
.crop-chip small { display:block; color:#94a3b8; font-weight:500; font-size:.7rem; text-transform:uppercase; letter-spacing:.06em;}

.banner { padding:.8rem 1rem; border-radius:12px; font-size:.88rem; margin:.4rem 0 1rem;
  background: rgba(251,191,36,.08); border:1px solid rgba(251,191,36,.3); color:#fde68a; }
.banner-info { background: rgba(34,211,238,.07); border-color: rgba(34,211,238,.28); color:#a5f3fc; }

div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
  border-radius: 12px; font-weight: 600; border: 1px solid rgba(52,211,153,.5);
  background: linear-gradient(135deg, rgba(52,211,153,.9), rgba(34,211,238,.85)); color: #04210f; }
div[data-testid="stButton"] > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
  filter: brightness(1.08); border-color: #a7f3d0; color:#04210f; }
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str, sub: str = "") -> str:
    return (
        f'<div class="glass"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-sub">{sub}</div></div>'
    )


def pill(text: str, tone: str = "green") -> str:
    return f'<span class="pill pill-{tone}">{text}</span>'


def banner(text: str, info: bool = False) -> None:
    cls = "banner banner-info" if info else "banner"
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)
