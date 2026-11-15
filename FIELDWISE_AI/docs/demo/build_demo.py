"""Build the KAIRO demo: 7-slide deck (PPTX + PDF) and a 28-second captioned video (MP4).

Inputs : docs/demo/screens/*.jpg  (real screenshots of the running app)
Outputs: docs/demo/KAIRO_Demo.pptx   editable slides
         docs/demo/KAIRO_Demo.pdf    same slides for upload / viewing
         docs/demo/KAIRO_Demo_28s.mp4  28-second captioned video, 1920x1080

Run:  py -3.11 docs/demo/build_demo.py
Needs: pillow, opencv-python, numpy, python-pptx.

Edit TEAM below before building, then re-run.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
SCREENS = HERE / "screens"

# ----------------------------------------------------------------- edit me
TEAM = "Qubix"
REPO = "github.com/likhitgv/Qubix"
# -------------------------------------------------------------------------

CREAM, SURFACE, FOREST, WHEAT, INK, MUTED, LINE = (
    "#F8F3E6", "#FFFCF3", "#1F4D2B", "#E3A82B", "#2A2A22", "#5F5A48", "#D2C6A6",
)
W, H = 1920, 1080
AI_MARK = "AI-assisted: built with Claude  ·  Weather data: NASA POWER"

AI_DISCLOSURE = (
    "This project used AI tools. Anthropic's Claude (through Claude Code) helped write and review the code, "
    "tests and documentation and draft the interface; the team directed the work and reviewed the results. "
    "An optional feature can send KAIRO's own computed results to a hosted language model to explain them; its "
    "text is accepted only if every number matches KAIRO's data. Crop and weather data come from the cited sources, not AI."
)

SLIDES = [
    dict(kind="title", title="KAIRO", subtitle="Crop planning from NASA weather records",
         lines=["NASA Space Apps Challenge 2026", "Field Shift: Adapting Farms with NASA Data", TEAM],
         image="2_recommendation.jpg"),
    dict(kind="text", title="The problem",
         bullets=["Seasons are harder to read, and crop choices are made with little local weather evidence.",
                  "National or state averages hide what happens around one field.",
                  "Farmers need advice that is local, simple and honest about what it does not know."]),
    dict(kind="shot", title="Four questions in, one answer out",
         bullets=["Where is your field? A district anywhere in India, or a pin on the map.",
                  "What is your soil type?", "How is the field irrigated?", "What did you grow previously?"],
         image="1_field.jpg"),
    dict(kind="shot", title="A clear recommendation, with reasons",
         bullets=["Best option for the coming kharif and rabi seasons.",
                  "Why it may fit this field, and the one trade-off to keep in mind.",
                  "Two alternatives, and the weather behind the advice.",
                  "Always: check with a local agronomist before planting."],
         image="3_alternatives.jpg"),
    dict(kind="shot", title="Built on NASA data, for all of India",
         bullets=["NASA POWER daily weather: temperature, rainfall, humidity.",
                  "882 grid points across India, daily 2021 to 2026.",
                  "Each field uses its nearest NASA grid cell; past seasons are averaged.",
                  "NASA GPM IMERG rainfall sample used for checking."],
         image="4_map.jpg"),
    dict(kind="shot", title="Transparent, and honest about limits",
         bullets=["Every score can be opened under \u201cHow this was calculated\u201d.",
                  "Tested in five Karnataka districts; six crops; some crop figures still being verified, and flagged.",
                  "NASA POWER is modelled data for a ~56 km area, not a field measurement.",
                  "Decision support only: no yield or savings claims."],
         image="5_calculation.jpg"),
    dict(kind="closing", title="Team, AI use and links",
         lines=[f"Team: {TEAM}", f"Code (public): {REPO}", "Data: NASA POWER (power.larc.nasa.gov), NASA GPM IMERG"],
         disclosure=AI_DISCLOSURE),
]

VIDEO = [  # (seconds, screenshot or None, caption)
    (4.0, None, "KAIRO turns NASA weather records into a crop plan for your field."),
    (5.0, "1_field.jpg", "Four simple questions: where, soil, water and past crops."),
    (8.0, "2_recommendation.jpg", "A best option, why it fits, and the one trade-off to keep in mind."),
    (5.0, "4_map.jpg", "NASA POWER weather for all of India."),
    (3.0, "3_alternatives.jpg", "Two alternatives, plus the weather behind the advice."),
    (3.0, None, "Decision support: check with a local agronomist before planting."),
]


# ----------------------------------------------------------------- fonts / drawing helpers
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = {"serif": "georgia.ttf", "serifb": "georgiab.ttf", "sans": "calibri.ttf", "sansb": "calibrib.ttf"}[name]
    return ImageFont.truetype(f"C:/Windows/Fonts/{path}", size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_block(draw, xy, text, fnt, fill, max_w, gap=1.28) -> int:
    x, y = xy
    for line in wrap(draw, text, fnt, max_w):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * gap)
    return y


def framed(shot: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Screenshot scaled to fit, with a thin border and soft shadow, on a transparent canvas."""
    scale = min(box_w / shot.width, box_h / shot.height)
    img = shot.resize((int(shot.width * scale), int(shot.height * scale)), Image.LANCZOS)
    pad = 28
    canvas = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((pad, pad + 8, pad + img.width, pad + img.height + 8), 14, fill=(40, 30, 10, 90))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(canvas).rounded_rectangle((pad - 2, pad - 2, pad + img.width + 2, pad + img.height + 2), 12, fill=LINE)
    canvas.paste(img.convert("RGBA"), (pad, pad))
    return canvas


def mark(draw: ImageDraw.ImageDraw) -> None:
    f = font("sans", 22)
    draw.text((W - 60 - draw.textlength(AI_MARK, font=f), H - 52), AI_MARK, font=f, fill=MUTED)


def base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 18, H), fill=WHEAT)
    return img, d


# ----------------------------------------------------------------- slide renderer (PNG, used for PDF)
def render_slide(spec: dict) -> Image.Image:
    img, d = base()
    kind = spec["kind"]
    if kind == "title":
        d.text((120, 150), spec["title"], font=font("serifb", 190), fill=FOREST)
        y = text_block(d, (124, 400), spec["subtitle"], font("serif", 54), INK, 840, 1.2)
        d.rectangle((124, y + 20, 324, y + 28), fill=WHEAT)
        y += 70
        for line in spec["lines"]:
            y = text_block(d, (124, y), line, font("sans", 38), MUTED, 840, 1.25) + 12
        shot = framed(Image.open(SCREENS / spec["image"]).convert("RGB"), 740, 640)
        img.paste(shot, (W - shot.width - 60, (H - shot.height) // 2), shot)
    elif kind == "text":
        d.text((120, 110), spec["title"], font=font("serifb", 84), fill=FOREST)
        y = 300
        for b in spec["bullets"]:
            d.ellipse((124, y + 22, 144, y + 42), fill=WHEAT)
            y = text_block(d, (176, y), b, font("sans", 52), INK, W - 380, 1.3) + 46
    elif kind == "shot":
        d.text((120, 70), spec["title"], font=font("serifb", 66), fill=FOREST)
        y = 290
        for b in spec["bullets"]:
            d.ellipse((124, y + 16, 140, y + 32), fill=WHEAT)
            y = text_block(d, (168, y), b, font("sans", 38), INK, 690, 1.3) + 34
        shot = framed(Image.open(SCREENS / spec["image"]).convert("RGB"), 1000, 740)
        img.paste(shot, (W - shot.width - 40, 215), shot)
    elif kind == "closing":
        d.text((120, 90), spec["title"], font=font("serifb", 72), fill=FOREST)
        y = 230
        for line in spec["lines"]:
            y = text_block(d, (124, y), line, font("sans", 42), INK, W - 260) + 14
        d.rectangle((124, y + 20, 324, y + 28), fill=WHEAT)
        d.text((124, y + 70), "Use of AI (disclosure)", font=font("sansb", 40), fill=FOREST)
        text_block(d, (124, y + 130), spec["disclosure"], font("sans", 34), MUTED, W - 260, 1.32)
    mark(d)
    return img


# ----------------------------------------------------------------- PPTX (editable)
def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_.lstrip("#").upper())


def add_text(slide, x, y, w, h, text, size, color, font_name="Calibri", bold=False, align=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size, p.font.bold, p.font.name = Pt(size), bold, font_name
    p.font.color.rgb = rgb(color)
    if align:
        p.alignment = align
    return box


def add_bullets(slide, x, y, w, h, items, size):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "\u2022  " + item
        p.font.size, p.font.name = Pt(size), "Calibri"
        p.font.color.rgb = rgb(INK)
        p.space_after = Pt(14)
    return box


def build_pptx(path: Path) -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    for spec in SLIDES:
        s = prs.slides.add_slide(blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(CREAM)
        bar = s.shapes.add_shape(1, 0, 0, Inches(0.13), prs.slide_height)
        bar.fill.solid()
        bar.fill.fore_color.rgb = rgb(WHEAT)
        bar.line.fill.background()
        kind = spec["kind"]
        if kind == "title":
            add_text(s, 0.8, 1.1, 7, 1.6, spec["title"], 80, FOREST, "Georgia", True)
            add_text(s, 0.85, 2.9, 6.3, 1, spec["subtitle"], 28, INK, "Georgia")
            add_bullets(s, 0.85, 4.0, 6.4, 2.4, spec["lines"], 18)
            s.shapes.add_picture(str(SCREENS / spec["image"]), Inches(7.6), Inches(1.4), width=Inches(5.2))
        elif kind == "text":
            add_text(s, 0.8, 0.7, 11, 1, spec["title"], 44, FOREST, "Georgia", True)
            add_bullets(s, 0.9, 2.0, 11.2, 4.5, spec["bullets"], 28)
        elif kind == "shot":
            add_text(s, 0.8, 0.5, 12, 1, spec["title"], 38, FOREST, "Georgia", True)
            add_bullets(s, 0.85, 1.7, 4.6, 5, spec["bullets"], 20)
            s.shapes.add_picture(str(SCREENS / spec["image"]), Inches(5.7), Inches(1.5), width=Inches(7.2))
        elif kind == "closing":
            add_text(s, 0.8, 0.5, 12, 1, spec["title"], 38, FOREST, "Georgia", True)
            add_bullets(s, 0.85, 1.5, 11.6, 1.8, spec["lines"], 22)
            add_text(s, 0.85, 3.5, 11, 0.5, "Use of AI (disclosure)", 20, FOREST, "Calibri", True)
            add_text(s, 0.85, 4.0, 11.6, 2.8, spec["disclosure"], 16, MUTED)
        add_text(s, 7.2, 7.0, 5.9, 0.35, AI_MARK, 11, MUTED, align=PP_ALIGN.RIGHT)
    prs.save(path)


# ----------------------------------------------------------------- video
def caption_frame(shot_name: str | None, caption: str, zoom: float, first: bool, last: bool) -> np.ndarray:
    img, d = base()
    if shot_name:
        shot = Image.open(SCREENS / shot_name).convert("RGB")
        fr = framed(shot, int(1380 * zoom), int(760 * zoom))
        img.paste(fr, ((W - fr.width) // 2, 40 + (int(760 * 1.06) - fr.height) // 2), fr)
    else:
        title = "KAIRO" if first else "KAIRO"
        d.text((W // 2 - d.textlength(title, font=font("serifb", 200)) // 2, 260), title, font=font("serifb", 200), fill=FOREST)
        sub = "Crop planning from NASA weather records" if first else "Check with a local agronomist"
        d.text((W // 2 - d.textlength(sub, font=font("serif", 60)) // 2, 520), sub, font=font("serif", 60), fill=INK)
        if last:
            line = f"{REPO}   ·   NASA POWER data   ·   AI-assisted: built with Claude"
            d.text((W // 2 - d.textlength(line, font=font("sans", 38)) // 2, 640), line, font=font("sans", 38), fill=MUTED)
    # caption bar
    d.rectangle((0, H - 210, W, H), fill=FOREST)
    f = font("sansb", 52)
    lines = wrap(d, caption, f, W - 240)
    y = H - 210 + (210 - len(lines) * 66) // 2 - 6
    for line in lines:
        d.text(((W - d.textlength(line, font=f)) // 2, y), line, font=f, fill="#FFFCF3")
        y += 66
    d.rectangle((0, H - 214, W, H - 210), fill=WHEAT)
    fm = font("sans", 22)
    d.text((W - 60 - d.textlength(AI_MARK, font=fm), 24), AI_MARK, font=fm, fill=MUTED)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def build_video(path: Path, fps: int = 24) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    if not writer.isOpened():
        raise SystemExit("Could not open the video writer.")
    fade = int(0.5 * fps)
    prev_last = None
    for idx, (secs, shot, caption) in enumerate(VIDEO):
        n = int(secs * fps)
        for i in range(n):
            zoom = 0.94 + 0.06 * (i / max(n - 1, 1))          # slow push-in
            frame = caption_frame(shot, caption, zoom, idx == 0, idx == len(VIDEO) - 1)
            if prev_last is not None and i < fade:             # cross-fade from previous scene
                a = i / fade
                frame = cv2.addWeighted(prev_last, 1 - a, frame, a, 0)
            writer.write(frame)
        prev_last = frame
    writer.release()


def main() -> None:
    for spec in SLIDES:
        img = spec.get("image")
        if img and not (SCREENS / img).is_file():
            raise SystemExit(f"Missing screenshot: {SCREENS / img}")
    pages = [render_slide(s) for s in SLIDES]
    pages[0].save(HERE / "KAIRO_Demo.pdf", save_all=True, append_images=pages[1:], resolution=150.0)
    build_pptx(HERE / "KAIRO_Demo.pptx")
    build_video(HERE / "KAIRO_Demo_28s.mp4")
    total = sum(v[0] for v in VIDEO)
    print(f"slides: {len(SLIDES)} | video: {total:.0f}s")


if __name__ == "__main__":
    main()
