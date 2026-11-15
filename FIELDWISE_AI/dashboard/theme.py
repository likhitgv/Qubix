"""KAIRO design system: calm, warm, readable. Earth tones, one green for actions.

Palette (contrast checked against the paper background):
  paper   #F6F2EA   page background (warm off-white)
  surface #FFFFFF   cards and inputs
  line    #E2DACB   borders
  ink     #2B2A26   text            (about 12:1 on paper)
  muted   #66604F   secondary text  (about 5.5:1 on paper)
  green   #2F6B3A   primary action  (white text about 6.4:1)
  clay    #A4673A   soil / secondary accent
  water   #3F7387   water / weather accent
  amber   #FBF3E0 / #5E4413 / #C98B2B   gentle caution
"""

import streamlit as st

GREEN = "#2F6B3A"
GREEN_SOFT = "#E3EDDC"
CLAY = "#A4673A"
WATER = "#3F7387"
SAND = "#D8BE7A"
INK = "#2B2A26"

# Kept for chart code that imports these names.
ACCENT = GREEN
ACCENT_2 = WATER
ACCENT_3 = CLAY

PLOT_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Source Sans 3, system-ui, sans-serif", color="#3A382F", size=13),
    margin=dict(l=8, r=8, t=30, b=8),
    legend=dict(orientation="h", y=1.12, x=0),
    xaxis=dict(gridcolor="#E9E2D3", zeroline=False, linecolor="#D8CFBC"),
    yaxis=dict(gridcolor="#E9E2D3", zeroline=False, linecolor="#D8CFBC"),
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
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&family=Source+Serif+4:wght@500;600;700&display=swap');
:root{
  --paper:#F6F2EA; --surface:#FFFFFF; --line:#E2DACB; --line-strong:#CFC5B0;
  --ink:#2B2A26; --muted:#66604F; --green:#2F6B3A; --green-dark:#25562F; --green-soft:#E3EDDC;
  --clay:#A4673A; --water:#3F7387; --amber-bg:#FBF3E0; --amber-ink:#5E4413; --amber-line:#C98B2B;
  --serif:'Source Serif 4',Georgia,serif; --sans:'Source Sans 3',system-ui,sans-serif;
}
html,body,[class*="css"],.stApp{font-family:var(--sans);}
.stApp{background:var(--paper);color:var(--ink);font-size:17px;line-height:1.55;}

/* hide Streamlit chrome we do not use */
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="collapsedControl"]{display:none!important;}
header[data-testid="stHeader"]{background:transparent;height:0;}
.block-container{max-width:1040px;padding-top:1.4rem;padding-bottom:4rem;}
[data-testid="stHeaderActionElements"]{display:none!important;}

h1,h2,h3,h4,h5{font-family:var(--serif);color:var(--ink);letter-spacing:-.01em;font-weight:600;}
h5{font-size:1.15rem;margin:.2rem 0 .6rem;}
a{color:var(--green);}

/* brand */
.brand{display:flex;align-items:baseline;gap:.8rem;flex-wrap:wrap;}
.wordmark{font-family:var(--serif);font-weight:700;font-size:1.55rem;color:var(--green);letter-spacing:.04em;}
.tagline{color:var(--muted);font-size:.92rem;}
.fieldnote{color:var(--muted);font-size:.9rem;text-align:right;}
.fieldnote b{color:var(--ink);font-weight:600;}

/* navigation: plain underlined text, not buttons */
.st-key-page [data-testid="stSegmentedControl"] > div,.st-key-page div[role="radiogroup"]{gap:.2rem 1.4rem!important;flex-wrap:wrap;}
.st-key-page button{border:none!important;background:transparent!important;border-radius:0!important;
  border-bottom:2px solid transparent!important;padding:.35rem .1rem!important;color:var(--muted)!important;
  font-weight:500;box-shadow:none!important;}
.st-key-page button:hover{color:var(--ink)!important;border-bottom-color:var(--line-strong)!important;}
.st-key-page button[aria-checked="true"],.st-key-page button[aria-pressed="true"],
.st-key-page button[data-testid="stBaseButton-segmented_controlActive"]{
  color:var(--green)!important;border-bottom-color:var(--green)!important;font-weight:700;background:transparent!important;}
.st-key-page{border-bottom:1px solid var(--line);margin-bottom:1.4rem;}

/* page titles */
.page-title{font-family:var(--serif);font-size:2.15rem;font-weight:600;line-height:1.2;margin:.2rem 0 .35rem;}
.page-sub{color:var(--muted);font-size:1.05rem;max-width:660px;margin-bottom:1.4rem;}

/* guided steps */
.step{display:flex;gap:.8rem;align-items:flex-start;margin:1.6rem 0 .5rem;}
.step .n{flex:none;width:30px;height:30px;border-radius:50%;border:1.5px solid var(--green);color:var(--green);
  font-weight:700;display:grid;place-items:center;font-size:.95rem;margin-top:.1rem;}
.step h3{margin:0;font-size:1.3rem;line-height:1.25;}
.step p{margin:.15rem 0 0;color:var(--muted);font-size:.95rem;}
.step-body{margin-left:2.4rem;}

/* surfaces */
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1.1rem 1.25rem;}
.panel h4{margin:0 0 .3rem;font-size:1.05rem;}
.panel p{margin:0;color:var(--muted);font-size:.95rem;}

/* recommendation */
.eyebrow{font-size:.8rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--green);}
.reco{background:var(--surface);border:1px solid var(--line-strong);border-left:6px solid var(--green);
  border-radius:10px;padding:1.6rem 1.8rem;margin:.4rem 0 1.2rem;}
.reco .plan{font-family:var(--serif);font-size:2.1rem;font-weight:600;line-height:1.25;margin:.35rem 0 .2rem;}
.reco .plan span{color:var(--muted);font-size:1.15rem;font-weight:500;}
.reco .fit{color:var(--muted);margin-bottom:1rem;}
.reco h4{font-size:1.05rem;margin:1.1rem 0 .35rem;}
.reco ul{margin:.1rem 0 0 1.1rem;padding:0;}
.reco li{margin:.25rem 0;}
.keep{background:var(--amber-bg);border-left:4px solid var(--amber-line);border-radius:6px;padding:.7rem 1rem;
  color:var(--amber-ink);margin-top:1rem;}
.keep b{font-weight:700;}
.alt{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1.1rem 1.25rem;height:100%;}
.alt .t{font-family:var(--serif);font-size:1.3rem;font-weight:600;line-height:1.3;margin:.25rem 0 .2rem;}
.alt .m{color:var(--muted);font-size:.95rem;}
.weather{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.9rem;margin:.2rem 0 1.2rem;}
.weather > div{border-top:2px solid var(--line-strong);padding-top:.5rem;}
.weather .k{color:var(--muted);font-size:.88rem;}
.weather .v{font-family:var(--serif);font-size:1.5rem;font-weight:600;}
.weather .s{color:var(--muted);font-size:.88rem;}

/* score bars (inside "How this was calculated") */
.bar{display:grid;grid-template-columns:100px 1fr 34px;gap:.6rem;align-items:center;margin:.35rem 0;font-size:.92rem;}
.bar .nm{color:var(--muted);text-transform:capitalize;}
.bar .track{height:8px;border-radius:4px;background:#ECE5D6;overflow:hidden;}
.bar .track i{display:block;height:100%;background:var(--green);}
.bar .track i.mid{background:#C79A3B;}
.bar .track i.low{background:#B5543F;}
.bar b{text-align:right;font-weight:600;}

/* notes */
.note{color:var(--muted);font-size:.93rem;border-left:3px solid var(--line-strong);padding:.15rem 0 .15rem .8rem;margin:.6rem 0;}
.note.caution{background:var(--amber-bg);border-left-color:var(--amber-line);color:var(--amber-ink);
  padding:.55rem .9rem;border-radius:0 6px 6px 0;}
.note.good{border-left-color:var(--green);}
.empty{text-align:center;padding:2.2rem 1rem;}
.empty h3{margin:.2rem 0;}
.empty p{color:var(--muted);}
.bubble{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1.2rem 1.4rem;
  line-height:1.7;white-space:pre-wrap;}
.tagline-pill{display:inline-block;font-size:.8rem;color:var(--muted);}
.source{color:var(--muted);font-size:.84rem;border-top:1px solid var(--line);margin-top:2.4rem;padding-top:.8rem;}

/* grid helpers */
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(var(--min,220px),1fr));gap:1rem;margin:.2rem 0 .6rem;}
.grid.g3{grid-template-columns:repeat(3,minmax(0,1fr));}
.grid.g2{grid-template-columns:repeat(2,minmax(0,1fr));}
@media (max-width:760px){.grid.g3,.grid.g2{grid-template-columns:1fr;}}

/* ---------- Streamlit widgets ---------- */
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important;border-radius:10px;background:var(--surface);}
/* primary action: the only rounded, filled button */
button[kind="primary"],button[data-testid="stBaseButton-primary"]{
  background:var(--green)!important;color:#fff!important;border:1px solid var(--green)!important;border-radius:8px!important;
  font-weight:600;padding:.65rem 1.6rem;box-shadow:none;}
button[kind="primary"]:hover,button[data-testid="stBaseButton-primary"]:hover{background:var(--green-dark)!important;}
/* secondary buttons: plain outline */
div[data-testid="stButton"] button:not([kind="primary"]),div[data-testid="stDownloadButton"] button{
  background:var(--surface);color:var(--ink);border:1px solid var(--line-strong);border-radius:8px;font-weight:600;box-shadow:none;}
div[data-testid="stButton"] button:not([kind="primary"]):hover,div[data-testid="stDownloadButton"] button:hover{
  border-color:var(--green);color:var(--green);}
/* option groups wrap onto several rows instead of scrolling sideways */
div[data-testid="stButtonGroup"] > div{flex-wrap:wrap!important;overflow:visible!important;gap:.45rem!important;}
.st-key-page div[data-testid="stButtonGroup"] > div{gap:.2rem 1.4rem!important;}
/* option buttons (pills / segmented): square-ish, not capsules */
div[data-testid="stPills"] button,div[data-testid="stButtonGroup"] button,
div[data-testid="stSegmentedControl"] button{border-radius:8px;border:1px solid var(--line-strong);background:var(--surface);
  color:var(--ink);font-weight:500;box-shadow:none;}
div[data-testid="stPills"] button:hover,div[data-testid="stButtonGroup"] button:hover,
div[data-testid="stSegmentedControl"] button:hover{border-color:var(--green);}
button[data-testid="stBaseButton-pillsActive"],button[data-testid="stBaseButton-segmented_controlActive"]{
  background:var(--green-soft)!important;border-color:var(--green)!important;color:#1E4B28!important;font-weight:700;}
div[data-baseweb="input"],div[data-baseweb="select"]>div,div[data-baseweb="base-input"],textarea{
  background:var(--surface)!important;border-radius:8px!important;border-color:var(--line-strong)!important;}
label[data-testid="stWidgetLabel"] p{color:var(--ink);font-size:.95rem;font-weight:600;}
div[data-testid="stSlider"] [role="slider"]{background:var(--green)!important;}
button[data-baseweb="tab"]{font-weight:600;color:var(--muted);}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--green);}
div[data-baseweb="tab-highlight"]{background:var(--green)!important;height:3px!important;}
div[data-baseweb="tab-border"]{background:var(--line)!important;}
details,div[data-testid="stExpander"]{border-radius:8px!important;border-color:var(--line)!important;background:var(--surface);}
div[data-testid="stExpander"] summary p{font-weight:600;color:var(--ink);}
div[data-testid="stDataFrame"]{border-radius:8px;overflow:hidden;border:1px solid var(--line);}
div[data-testid="stAlert"]{border-radius:8px;}
div[data-testid="stCaptionContainer"]{color:var(--muted);}
button:focus-visible{outline:3px solid #8DB38F!important;outline-offset:2px;}

@media (max-width:720px){
  .stApp{font-size:16px;}
  .page-title{font-size:1.7rem;}
  .reco{padding:1.2rem 1.1rem;}.reco .plan{font-size:1.6rem;}
  .step-body{margin-left:0;}
  .bar{grid-template-columns:84px 1fr 30px;}
  .block-container{padding-left:1rem;padding-right:1rem;}
  .fieldnote{text-align:left;}
}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
