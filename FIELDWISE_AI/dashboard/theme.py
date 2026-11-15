"""KAIRO design system: dark glass UI, gradient accents, modern widgets."""

import streamlit as st

ACCENT = "#34d399"
ACCENT_2 = "#22d3ee"
ACCENT_3 = "#a78bfa"
WARN = "#fbbf24"
BAD = "#f87171"

PLOT_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#b6c2d3"),
    margin=dict(l=8, r=8, t=36, b=8),
    legend=dict(orientation="h", y=1.14, x=0),
    xaxis=dict(gridcolor="rgba(148,163,184,.10)", zeroline=False),
    yaxis=dict(gridcolor="rgba(148,163,184,.10)", zeroline=False),
)

def plot_layout(**overrides) -> dict:
    """Base chart layout with per-chart overrides; axis dicts are merged."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PLOT_LAYOUT.items()}
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key].update(value)
        else:
            out[key] = value
    return out


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root{
  --bg:#060a11; --card:rgba(15,23,38,.62); --card-solid:#0b111c; --line:rgba(148,163,184,.14);
  --line-strong:rgba(148,163,184,.26); --text:#e6edf6; --muted:#8b9ab0; --dim:#5f6f86;
  --a1:#34d399; --a2:#22d3ee; --a3:#a78bfa; --warn:#fbbf24; --bad:#f87171;
  --grad:linear-gradient(135deg,#34d399 0%,#22d3ee 55%,#a78bfa 120%);
}
html,body,[class*="css"],.stApp{font-family:'Inter',system-ui,sans-serif;}
.stApp{
  background:
    radial-gradient(900px 520px at 8% -8%,rgba(52,211,153,.16),transparent 62%),
    radial-gradient(800px 480px at 98% 2%,rgba(34,211,238,.12),transparent 58%),
    radial-gradient(700px 500px at 60% 110%,rgba(167,139,250,.10),transparent 60%),
    var(--bg);
  color:var(--text);
}
/* chrome we do not need */
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="collapsedControl"]{display:none!important;}
header[data-testid="stHeader"]{background:transparent;height:0;}
.block-container{max-width:1180px;padding-top:1.1rem;padding-bottom:4rem;}
h1,h2,h3,h4{letter-spacing:-.02em;color:var(--text);}
[data-testid="stHeaderActionElements"]{display:none!important;}

/* top bar */
.topbar{display:flex;align-items:center;gap:.7rem;padding:.2rem 0;}
.logo{width:38px;height:38px;border-radius:12px;background:var(--grad);display:grid;place-items:center;
  font-weight:900;color:#04210f;font-size:1.1rem;box-shadow:0 8px 28px rgba(52,211,153,.35);}
.wordmark{font-weight:900;font-size:1.35rem;letter-spacing:.08em;background:var(--grad);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;line-height:1;}
.wordsub{color:var(--dim);font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;margin-top:2px;white-space:nowrap;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(var(--min,220px),1fr));gap:1rem;margin:.2rem 0 .6rem;}
.grid .card{height:100%;}
.grid.g4{grid-template-columns:repeat(4,minmax(0,1fr));}
@media (max-width:1000px){.grid.g4{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media (max-width:480px){.grid.g4{grid-template-columns:1fr;}}
.grid.g3{grid-template-columns:repeat(3,minmax(0,1fr));}
@media (max-width:900px){.grid.g3{grid-template-columns:1fr;}}
/* equal-height cards across a row of columns */
div[data-testid="stColumn"]:has(.card) [data-testid="stVerticalBlock"],
div[data-testid="stColumn"]:has(.card) [data-testid="stElementContainer"],
div[data-testid="stColumn"]:has(.card) [data-testid="stMarkdown"],
div[data-testid="stColumn"]:has(.card) [data-testid="stMarkdownContainer"],
div[data-testid="stColumn"]:has(.card) [data-testid="stMarkdown"] > div{height:100%;}
div[data-testid="stColumn"]:has(.card) [data-testid="stElementContainer"]{flex:1 1 auto;}
.card{box-sizing:border-box;height:100%;}
/* navigation bar */
div[data-testid="stSegmentedControl"]{width:100%;}
div[data-testid="stSegmentedControl"] > div{flex-wrap:wrap;gap:.4rem;}
.farmchip{display:inline-flex;align-items:center;gap:.5rem;padding:.42rem .8rem;border-radius:999px;
  background:var(--card);border:1px solid var(--line);font-size:.8rem;color:var(--muted);white-space:nowrap;}
.farmchip b{color:var(--text);font-weight:600;}
.dot{width:8px;height:8px;border-radius:50%;background:var(--a1);box-shadow:0 0 10px var(--a1);display:inline-block;}
.dot.off{background:var(--dim);box-shadow:none;}

/* hero */
.hero{position:relative;overflow:hidden;padding:3.2rem 2.4rem;border-radius:28px;margin:1.2rem 0 1.4rem;
  background:linear-gradient(135deg,rgba(52,211,153,.13),rgba(34,211,238,.07) 45%,rgba(167,139,250,.10));
  border:1px solid var(--line);}
.hero::after{content:"";position:absolute;right:-90px;top:-90px;width:340px;height:340px;border-radius:50%;
  background:radial-gradient(circle,rgba(52,211,153,.30),transparent 68%);filter:blur(8px);}
.eyebrow{display:inline-flex;align-items:center;gap:.5rem;padding:.3rem .8rem;border-radius:999px;font-size:.72rem;
  font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#6ee7b7;background:rgba(52,211,153,.10);
  border:1px solid rgba(52,211,153,.30);}
.hero h1{font-size:clamp(2rem,5vw,3.4rem);font-weight:900;line-height:1.05;letter-spacing:-.04em;margin:1rem 0 .9rem;
  max-width:760px;}
.hero h1 em{font-style:normal;background:var(--grad);-webkit-background-clip:text;background-clip:text;
  -webkit-text-fill-color:transparent;}
.hero p{color:#aab8cb;font-size:1.08rem;max-width:620px;line-height:1.6;margin:0;}

/* generic card + section */
.card{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:1.2rem 1.3rem;
  backdrop-filter:blur(12px);transition:border-color .2s,transform .2s,box-shadow .2s;}
.card.hover:hover{border-color:rgba(52,211,153,.45);transform:translateY(-3px);box-shadow:0 18px 50px rgba(0,0,0,.35);}
.kicker{color:#6ee7b7;font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;}
.sec-title{font-size:1.7rem;font-weight:800;letter-spacing:-.03em;margin:.2rem 0 .3rem;}
.sec-sub{color:var(--muted);font-size:.95rem;margin-bottom:1rem;max-width:720px;}

.stat{display:flex;gap:.9rem;align-items:flex-start;}
.stat .ico{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;font-size:1.25rem;
  background:rgba(52,211,153,.10);border:1px solid rgba(52,211,153,.25);flex:none;}
.stat .lbl{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;}
.stat .val{font-size:1.7rem;font-weight:800;letter-spacing:-.03em;line-height:1.15;}
.stat .sub{color:var(--dim);font-size:.78rem;margin-top:2px;}

.step-num{width:34px;height:34px;border-radius:11px;background:var(--grad);color:#04210f;font-weight:800;
  display:grid;place-items:center;margin-bottom:.7rem;}
.card h4{margin:.1rem 0 .35rem;font-size:1.05rem;}
.card p.t{color:var(--muted);font-size:.9rem;line-height:1.55;margin:0;}

/* tags */
.tag{display:inline-flex;align-items:center;gap:.35rem;padding:.2rem .65rem;border-radius:999px;font-size:.72rem;
  font-weight:600;border:1px solid transparent;margin:.15rem .3rem .15rem 0;}
.tag.green{background:rgba(52,211,153,.12);color:#6ee7b7;border-color:rgba(52,211,153,.32);}
.tag.cyan{background:rgba(34,211,238,.11);color:#67e8f9;border-color:rgba(34,211,238,.30);}
.tag.amber{background:rgba(251,191,36,.11);color:#fcd34d;border-color:rgba(251,191,36,.32);}
.tag.red{background:rgba(248,113,113,.11);color:#fca5a5;border-color:rgba(248,113,113,.32);}
.tag.violet{background:rgba(167,139,250,.12);color:#c4b5fd;border-color:rgba(167,139,250,.32);}
.tag.gray{background:rgba(148,163,184,.10);color:#cbd5e1;border-color:rgba(148,163,184,.25);}

/* score ring */
.ring{width:92px;height:92px;border-radius:50%;position:relative;display:grid;place-items:center;flex:none;
  background:conic-gradient(var(--c,#34d399) calc(var(--v,0)*1%),rgba(148,163,184,.14) 0);}
.ring::before{content:"";position:absolute;inset:8px;border-radius:50%;background:var(--card-solid);}
.ring .n{position:relative;font-weight:800;font-size:1.3rem;letter-spacing:-.03em;line-height:1;text-align:center;}
.ring .n small{display:block;color:var(--dim);font-size:.58rem;font-weight:600;letter-spacing:.08em;margin-top:3px;}
.ring.sm{width:62px;height:62px;}.ring.sm::before{inset:6px;}.ring.sm .n{font-size:.95rem;}.ring.sm .n small{display:none;}

/* crop sequence */
.seq{display:flex;flex-wrap:wrap;align-items:stretch;gap:.5rem;margin:.55rem 0 .4rem;}
.step{flex:1 1 150px;min-width:140px;padding:.75rem .9rem;border-radius:14px;background:rgba(255,255,255,.035);
  border:1px solid var(--line);}
.step .se{color:var(--dim);font-size:.64rem;text-transform:uppercase;letter-spacing:.12em;font-weight:700;}
.step .cn{font-weight:700;font-size:1.05rem;margin:2px 0;}
.step .sc{font-size:.78rem;color:var(--muted);}
.step .sc b{color:#6ee7b7;}
.arrow{align-self:center;color:var(--dim);font-size:1.2rem;}

/* score bars */
.bar{display:grid;grid-template-columns:96px 1fr 38px;gap:.6rem;align-items:center;margin:.38rem 0;font-size:.82rem;}
.bar .nm{color:var(--muted);text-transform:capitalize;}
.bar .track{height:7px;border-radius:99px;background:rgba(148,163,184,.14);overflow:hidden;}
.bar .track i{display:block;height:100%;border-radius:99px;background:var(--grad);}
.bar .track i.mid{background:linear-gradient(90deg,#fbbf24,#fde68a);}
.bar .track i.low{background:linear-gradient(90deg,#f87171,#fca5a5);}
.bar b{text-align:right;font-weight:700;}

/* banners */
.banner{display:flex;gap:.7rem;align-items:flex-start;padding:.85rem 1rem;border-radius:14px;font-size:.88rem;
  margin:.5rem 0 1rem;background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.28);color:#fde68a;line-height:1.5;}
.banner.info{background:rgba(34,211,238,.06);border-color:rgba(34,211,238,.26);color:#a5f3fc;}
.banner.ok{background:rgba(52,211,153,.07);border-color:rgba(52,211,153,.28);color:#a7f3d0;}
.empty{text-align:center;padding:3rem 1rem;}
.empty .big{font-size:2.6rem;margin-bottom:.4rem;}
.empty h3{margin:.2rem 0;}
.empty p{color:var(--muted);}

.bubble{padding:1.1rem 1.3rem;border-radius:18px 18px 18px 6px;background:rgba(34,211,238,.06);
  border:1px solid rgba(34,211,238,.24);line-height:1.7;color:#d6e4f2;white-space:pre-wrap;}
.footer{color:var(--dim);font-size:.76rem;text-align:center;margin-top:3rem;}

/* ---------- Streamlit widgets ---------- */
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important;border-radius:20px;
  background:var(--card);backdrop-filter:blur(12px);}
div[data-testid="stButton"] button,div[data-testid="stDownloadButton"] button,div[data-testid="stFormSubmitButton"] button{
  border-radius:13px;font-weight:700;padding:.6rem 1.3rem;border:1px solid var(--line-strong);
  background:rgba(255,255,255,.04);color:var(--text);transition:all .18s;}
div[data-testid="stButton"] button:hover,div[data-testid="stDownloadButton"] button:hover{border-color:var(--a1);color:#fff;transform:translateY(-1px);}
button[kind="primary"],button[data-testid="stBaseButton-primary"]{
  background:var(--grad)!important;color:#04210f!important;border:none!important;box-shadow:0 10px 30px rgba(52,211,153,.30);}
button[kind="primary"]:hover,button[data-testid="stBaseButton-primary"]:hover{filter:brightness(1.08);transform:translateY(-1px);}
div[data-testid="stSegmentedControl"] button,div[data-testid="stButtonGroup"] button{
  border-radius:999px!important;border:1px solid var(--line)!important;background:rgba(255,255,255,.03)!important;
  color:var(--muted)!important;font-weight:600;transition:all .15s;}
div[data-testid="stSegmentedControl"] button:hover,div[data-testid="stButtonGroup"] button:hover{
  border-color:rgba(52,211,153,.5)!important;color:var(--text)!important;}
div[data-testid="stSegmentedControl"] button[aria-checked="true"],div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
div[data-testid="stButtonGroup"] button[aria-checked="true"],div[data-testid="stButtonGroup"] button[aria-pressed="true"],
button[data-testid="stBaseButton-pillsActive"],button[data-testid="stBaseButton-segmented_controlActive"]{
  background:linear-gradient(135deg,rgba(52,211,153,.28),rgba(34,211,238,.22))!important;
  border-color:rgba(52,211,153,.7)!important;color:#ecfdf5!important;box-shadow:0 0 0 1px rgba(52,211,153,.25) inset;}
div[data-baseweb="input"],div[data-baseweb="select"]>div,div[data-baseweb="base-input"],textarea{
  background:rgba(255,255,255,.04)!important;border-radius:12px!important;border-color:var(--line)!important;}
label[data-testid="stWidgetLabel"] p{color:var(--muted);font-size:.8rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;}
div[data-testid="stSlider"] [role="slider"]{background:var(--a1)!important;box-shadow:0 0 0 4px rgba(52,211,153,.25);}
button[data-baseweb="tab"]{font-weight:600;color:var(--muted);}
button[data-baseweb="tab"][aria-selected="true"]{color:#ecfdf5;}
div[data-baseweb="tab-highlight"]{background:var(--grad)!important;height:3px!important;border-radius:3px;}
div[data-baseweb="tab-border"]{background:var(--line)!important;}
details,div[data-testid="stExpander"]{border-radius:16px!important;border-color:var(--line)!important;background:rgba(255,255,255,.02);}
div[data-testid="stExpander"] summary p{font-weight:600;}
div[data-testid="stDataFrame"]{border-radius:16px;overflow:hidden;border:1px solid var(--line);}
div[data-testid="stAlert"]{border-radius:14px;}

@media (max-width:720px){
  .hero{padding:2rem 1.3rem;border-radius:22px;}
  .ring{width:72px;height:72px;}.ring::before{inset:7px;}.ring .n{font-size:1.05rem;}
  .bar{grid-template-columns:78px 1fr 34px;}
  .step{flex:1 1 100%;}.arrow{display:none;}
  .block-container{padding-left:1rem;padding-right:1rem;}
}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
