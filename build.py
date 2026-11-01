import re
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).parent
FONTS = ROOT / "fonts"
OUT = ROOT / "assets"

PAPER = "#ECE8DF"
INK = "#15140F"
MUTE = "#8A8578"
SIGNAL = "#FF4A1C"

FONT_FILES = {
    "anek": "AnekLatin-VF.ttf",
    "guj": "AnekGujarati-VF-subset.ttf",
    "mono": "MartianMono-VF.ttf",
}
_faces = {}


def hb_font(name, wght, wdth):
    if name not in _faces:
        blob = hb.Blob.from_file_path(str(FONTS / FONT_FILES[name]))
        _faces[name] = hb.Face(blob)
    font = hb.Font(_faces[name])
    font.set_variations({"wght": wght, "wdth": wdth})
    return font


class Doc:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.defs = {}
        self.body = []

    def glyph(self, font, key, gid):
        gkey = f"{key}-{gid}"
        if gkey not in self.defs:
            pen = SVGPathPen(None, ntos=lambda v: f"{v:.0f}")
            font.draw_glyph_with_pen(gid, pen)
            self.defs[gkey] = pen.getCommands()
        return gkey

    def text(self, s, x, y, size, name="anek", wght=400, wdth=100,
             track=0, anchor="start", attrs="", measure_only=False):
        font = hb_font(name, wght, wdth)
        upem = _faces[name].upem
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(font, buf, {"kern": True, "liga": True})
        track_u = track * upem / size
        uses, pen_x = [], 0
        key = f"{name}{wght}w{wdth}"
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            if info.codepoint == 0:
                print("MISSING GLYPH in", name, repr(s))
            gkey = self.glyph(font, key, info.codepoint)
            if self.defs[gkey]:
                uses.append(
                    f'<use href="#{gkey}" x="{pen_x + pos.x_offset:.0f}" y="{-pos.y_offset:.0f}"/>')
            pen_x += pos.x_advance + track_u
        width = (pen_x - track_u) * size / upem
        if measure_only:
            return width
        if anchor == "end":
            x -= width
        elif anchor == "middle":
            x -= width / 2
        s_ = size / upem
        self.body.append(
            f'<g transform="translate({x:.1f} {y:.1f}) scale({s_:.5f} {-s_:.5f})" {attrs}>'
            + "".join(uses) + "</g>")
        return width

    def raw(self, svg):
        self.body.append(svg)

    def save(self, fname, style="", title=""):
        defs = "".join(f'<path id="{k}" d="{d}" pathLength="100"/>'
                       for k, d in self.defs.items() if d)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
               f'width="{self.w}" height="{self.h}" role="img" aria-label="{title}">'
               f'<title>{title}</title><style>{style}</style><defs>{defs}</defs>'
               + "".join(self.body) + "</svg>")
        OUT.mkdir(exist_ok=True)
        (OUT / fname).write_text(svg, encoding="utf-8")
        print(fname, f"{len(svg) / 1024:.0f} KB")


def frame(d, label_left, label_right):
    w, h = d.w, d.h
    d.raw(f'<rect width="{w}" height="{h}" fill="{PAPER}"/>')
    d.raw(f'<rect x="16.5" y="16.5" width="{w - 33}" height="{h - 33}" fill="none" '
          f'stroke="{INK}" stroke-width="1"/>')
    for cx, cy in ((16.5, 16.5), (w - 16.5, 16.5), (16.5, h - 16.5), (w - 16.5, h - 16.5)):
        d.raw(f'<path d="M{cx - 6} {cy}H{cx + 6}M{cx} {cy - 6}V{cy + 6}" stroke="{INK}"/>')
    d.text(label_left, 40, 46, 11, "mono", 500, 100, 1.2, attrs=f'fill="{INK}"')
    d.text(label_right, w - 40, 46, 11, "mono", 500, 100, 1.2, "end", attrs=f'fill="{MUTE}"')


def hero():
    d = Doc(1280, 600)
    frame(d, "INDEX 027 — PRINCE PATEL", "PRINCEPATEL.DEV")

    # code texture panel, real source from SuperBrowser
    code = re.sub(r"\s+", " ", (ROOT / "texture.txt").read_text(encoding="utf-8"))
    cols, lines = 62, []
    for i in range(0, cols * 30, cols):
        lines.append(code[i:i + cols])
    px, pw = 840, 400
    d.raw(f'<clipPath id="cp"><rect x="{px}" y="70" width="{pw}" height="420"/></clipPath>')
    d.raw(f'<rect x="{px}" y="70" width="{pw}" height="420" fill="{INK}"/>')
    d.raw('<g clip-path="url(#cp)"><g class="scroll"><g id="blk">')
    for i, ln in enumerate(lines):
        d.text(ln, px + 14, 92 + i * 14, 9.6, "mono", 300, 100, 0, attrs=f'fill="{PAPER}" opacity=".22"')
    d.raw('</g><use href="#blk" y="420"/></g></g>')
    d.text("પ્રિન્સ", px + pw / 2, 330, 190, "guj", 700, 100, 0, "middle",
           attrs=f'fill="{SIGNAL}" class="guj"')
    d.text("SRC: SUPERBROWSER/SERVICES/AI_SERVICE.PY", px + 14, 478, 9, "mono", 500, 100, 0.8,
           attrs=f'fill="{PAPER}" opacity=".7"')

    d.text("PRINCE", 34, 290, 300, "anek", 800, 75, -4, attrs=f'fill="{INK}" class="rise"')
    w = d.text("PATEL", 34, 510, 300, "anek", 800, 75, -4,
               attrs=f'fill="none" stroke="{INK}" stroke-width="5" class="draw"')
    d.raw(f'<rect class="cur" x="{34 + w + 14:.0f}" y="318" width="36" height="192" fill="{SIGNAL}"/>')

    d.raw(f'<path d="M40 548.5H{d.w - 40}" stroke="{INK}"/>')
    items = ["DESIGNS THE INTERFACE", "WRITES THE BACKEND", "WIRES IN THE AI", "SHIPS THE WHOLE THING"]
    for i, t in enumerate(items):
        x = 40 + i * 300
        d.raw(f'<rect x="{x}" y="563" width="7" height="7" fill="{SIGNAL}"/>')
        d.text(t, x + 16, 571, 10.5, "mono", 600, 100, 1, attrs=f'fill="{INK}"')

    style = (
        "@keyframes up{to{transform:translateY(-420px)}}"
        ".scroll{animation:up 60s linear infinite}"
        "@keyframes draw{from{stroke-dashoffset:100}to{stroke-dashoffset:0}}"
        f"@keyframes fill{{to{{fill:{INK}}}}}"
        ".draw use{stroke-dasharray:100;stroke-dashoffset:100;"
        "animation:draw 2.4s .4s cubic-bezier(.6,0,.2,1) forwards,fill .6s 2.6s forwards}"
        "@keyframes blink{50%{opacity:0}}"
        ".cur{animation:blink 1.1s steps(1) infinite}"
        "@keyframes rise{from{opacity:0;transform:translateY(24px)}}"
        ".rise{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}"
        "@keyframes pop{from{opacity:0}}"
        ".guj{animation:pop 1.2s 1.2s both}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}"
        f".draw use{{stroke-dasharray:none;fill:{INK}}}}}"
    )
    d.save("hero.svg", style, "Prince Patel")


PROJECTS = [
    ("01", "SuperBrowser", ["AI desktop browser: multi-engine search,", "community insights and persona-driven", "answers in one window."],
     "ELECTRON · REACT 19 · VITE · FASTAPI · GROQ"),
    ("02", "LabAttendance", ["Turnkey Windows lab attendance server", "with a faculty dashboard and a", "student photo check-in client."],
     "PYTHON · WINDOWS · LAN SERVER"),
    ("03", "Doc2JSON", ["Turns PDF, DOCX and text into structured", "JSON for AI training data, with OCR", "for the images and diagrams."],
     "PYTHON · PYMUPDF · PDFPLUMBER · MISTRAL · TESSERACT"),
    ("04", "princepatel.dev", ["A portfolio with a 3D avatar that", "listens and talks back, served", "from the edge."],
     "REACT · THREE.JS · WHISPER · CLOUDFLARE WORKERS"),
]


def card(num, name, desc, stack):
    d = Doc(620, 340)
    frame(d, f"PROJECT {num}", "VIEW REPO")
    d.text(num, 590 - 4, 300, 150, "anek", 800, 75, -2, "end",
           attrs=f'fill="none" stroke="{MUTE}" stroke-width="5" opacity=".45"')
    d.text(name, 38, 128, 64, "anek", 800, 75, -1, attrs=f'fill="{INK}"')
    d.raw(f'<rect x="40" y="146" width="44" height="6" fill="{SIGNAL}"/>')
    for i, ln in enumerate(desc):
        d.text(ln, 40, 196 + i * 28, 21, "anek", 400, 100, 0, attrs=f'fill="{INK}"')
    d.raw(f'<path d="M40 286.5H580" stroke="{INK}"/>')
    d.text(stack, 40, 306, 10, "mono", 600, 100, 0.8, attrs=f'fill="{INK}"')
    d.save(f"p{num}.svg", "", name)


def footer():
    d = Doc(1280, 150)
    frame(d, "END OF INDEX", "© PRINCE PATEL")
    d.text("Got something hard to build?", 40, 112, 52, "anek", 700, 75, -0.5, attrs=f'fill="{INK}"')
    d.text("PRINCEPATEL.DEV", 1240, 108, 18, "mono", 700, 100, 1, "end", attrs=f'fill="{SIGNAL}"')
    d.save("footer.svg", "", "Got something hard to build? princepatel.dev")


if __name__ == "__main__":
    hero()
    for p in PROJECTS:
        card(*p)
    footer()
