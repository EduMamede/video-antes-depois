"""Gera o vídeo vertical de antes e depois (1080x1920) a partir de um config.json.

Uso:
  python motor/gerar.py CAMINHO/config.json paciente|publico [PASTA_DE_SAIDA]

- paciente: vai para a própria paciente no WhatsApp, como fechamento do tratamento
            (parabéns + assinatura, sem chamada para agendar).
- publico:  post do Instagram (chamada para agendar + avisos). Só sai se a paciente autorizou.

Depois, dentro de PASTA_DE_SAIDA/composition:
  npx hyperframes check
  npx hyperframes render --quality high --output ../video.mp4

Regras que este script segue:
- As fotos são copiadas byte a byte: sem filtro, retoque, recorte ou ajuste.
- O "mistério" é só um quadro por cima do DEPOIS, que esmaece na revelação.
- Nenhum nome, rosto, medicamento ou preço é inventado ou acrescentado aqui.
"""

import html
import json
import os
import shutil
import statistics
import sys

from PIL import Image, ImageOps

MOTOR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(MOTOR)
E = html.escape

AVISO_RESULTADO = "Resultados podem variar de pessoa para pessoa."
AVISO_AUTORIZACAO = "Imagens publicadas com autorização da paciente."


def sair(msg):
    sys.exit("ERRO: " + msg)


# ---------- cores ----------
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mistura(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb))


def tema(v):
    for k in ("escuro", "destaque", "claro"):
        if k not in v:
            sair(f'faltou "visual.{k}" no config (cor em hexadecimal, ex.: "#1A1612").')
    esc, dst, clr = v["escuro"], v["destaque"], v["claro"]
    return {
        "dark": esc,
        "dark2": v.get("escuro2", mistura(esc, "#000000", 0.3)),
        "dark3": mistura(esc, dst, 0.12),
        "cream": clr,
        "warm": v.get("claro2", mistura(clr, dst, 0.06)),
        "line": mistura(clr, dst, 0.25),
        "bronze": dst,
        "ink": v.get("destaque_texto", mistura(dst, "#000000", 0.3)),
        "text": v.get("texto", mistura(esc, "#000000", 0.2)),
        "muted": mistura(esc, clr, 0.15),
        "dim": mistura(esc, clr, 0.5),
        "soft": mistura(clr, esc, 0.08),
        "foot_dark_line": mistura(esc, clr, 0.2),
        "foot_dark_ink": mistura(esc, clr, 0.68),
        "foot_light_line": mistura(clr, esc, 0.15),
        "foot_light_ink": mistura(clr, esc, 0.65),
    }


# ---------- fotos ----------
def tamanho(path):
    """Tamanho como o navegador mostra (respeita a rotação gravada pelo celular)."""
    im = ImageOps.exif_transpose(Image.open(path))
    return im.size


def metades(path):
    """Numa foto já montada (ANTES | DEPOIS), acha onde fica cada metade pela faixa clara do meio.
    Se não achar a faixa, divide no meio."""
    im = ImageOps.exif_transpose(Image.open(path)).convert("L")
    w, h = im.size
    passo = max(1, min(w, h) // 300)
    my, mx = int(h * 0.1), int(w * 0.1)
    cols = [statistics.mean(im.getpixel((x, y)) for y in range(my, h - my, passo)) for x in range(w)]
    rows = [statistics.mean(im.getpixel((x, y)) for x in range(mx, w - mx, passo)) for y in range(h)]
    claro = lambda v: v > 245
    try:
        left = next(x for x in range(w) if not claro(cols[x]))
        right = next(x for x in range(w - 1, -1, -1) if not claro(cols[x]))
        top = next(y for y in range(h) if not claro(rows[y]))
        bot = next(y for y in range(h - 1, -1, -1) if not claro(rows[y]))
        mid = [x for x in range(int(w * 0.4), int(w * 0.6)) if claro(cols[x])]
        if mid:
            return (w, h), (left, mid[0] - 1), (mid[-1] + 1, right), (top, bot)
    except StopIteration:
        pass
    return (w, h), (0, w // 2 - 1), (w // 2, w - 1), (0, h - 1)


# ---------- composição ----------
class Comp:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.html, self.js, self.audio, self.scenes = [], [], [], []
        self.n = 0

    def uid(self, p):
        self.n += 1
        return f"{p}{self.n}"

    def text(self, x, y, w, txt, cls, style="", rich=False):
        eid = self.uid("t")
        body = txt if rich else E(txt)
        self.html.append(f'<p id="{eid}" class="abs {cls}" style="left:{x}px;top:{y}px;width:{w}px;{style}">{body}</p>')
        return "#" + eid

    def img(self, x, y, w, h, path, alt=""):
        eid = self.uid("i")
        self.html.append(f'<img id="{eid}" class="abs" src="{path}" alt="{E(alt)}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;" />')
        return "#" + eid

    def box(self, x, y, w, h, color):
        eid = self.uid("b")
        self.html.append(f'<div id="{eid}" class="abs" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{color};"></div>')
        return "#" + eid

    def fin(self, sel, t, dy=18, dur=0.5, ease="power3.out", dx=0, scale=None):
        frm, to = {"opacity": 0}, {"opacity": 1, "duration": dur, "ease": ease}
        if dy:
            frm["y"], to["y"] = dy, 0
        if dx:
            frm["x"], to["x"] = dx, 0
        if scale:
            frm["scale"], to["scale"] = scale, 1
        self.js.append(f"tl.fromTo({json.dumps(sel)}, {json.dumps(frm)}, {json.dumps(to)}, {t:.3f});")

    def raw(self, line):
        self.js.append(line)

    def sfx(self, path, t, vol, dur):
        aid = self.uid("sfx")
        self.audio.append(
            f'<audio id="{aid}" src="{path}" data-start="{t:.3f}" data-duration="{dur}" data-track-index="{11 + len(self.audio)}" data-volume="{vol}"></audio>'
        )

    def open_scene(self, t0, t1, bg, cls=""):
        sid = self.uid("s")
        self.scenes.append((sid, t0, t1))
        self.html.append(f'<section id="{sid}" class="scene {cls}"><div class="bg" style="background:{bg}"></div>')

    def close_scene(self):
        self.html.append("</section>")

    def scene_js(self):
        for i, (sid, t0, t1) in enumerate(self.scenes):
            if i == 0:
                self.js.insert(0, f'tl.set("#{sid}", {{opacity: 1}}, 0);')
            else:
                self.js.insert(0, f'tl.to("#{sid}", {{opacity: 1, duration: 0.5, ease: "power1.inOut"}}, {t0:.3f});')
            if i < len(self.scenes) - 1:
                self.js.insert(0, f'tl.to("#{sid}", {{opacity: 0, duration: 0.35, ease: "power1.in"}}, {t1:.3f});')

    def eyebrow(self, y, txt, color, t, size=24):
        eid = self.uid("eb")
        line = f'<span style="display:block;width:64px;height:2px;background:{color};"></span>'
        self.html.append(
            f'<div id="{eid}" class="abs" style="left:0;top:{y}px;width:{self.W}px;display:flex;align-items:center;justify-content:center;gap:22px;">'
            f'{line}<span class="lbl" style="font-size:{size}px;line-height:{size + 6}px;letter-spacing:{size * 0.24:.1f}px;color:{color};">{E(txt)}</span>{line}</div>'
        )
        self.fin("#" + eid, t, dy=0, dur=0.6)


class Video:
    def __init__(self, cfg, base, versao):
        self.cfg, self.base, self.versao = cfg, base, versao
        self.cl = cfg["clinica"]
        self.caso = cfg["caso"]
        self.T = tema(cfg.get("visual", {}))
        self.c = Comp(1080, 1920)
        self.files = {}  # destino em assets -> origem
        # música: "padrao" (a que vem com a ferramenta), false (sem música) ou o caminho de outra música
        m = cfg.get("musica", "padrao")
        if m == "padrao":
            self.musica = os.path.join(MOTOR, "musica", "padrao.mp3")
        elif m:
            self.musica = self.p(m)
        else:
            self.musica = None
        marcas = os.path.splitext(self.musica)[0] + ".batidas.json" if self.musica else ""
        if marcas and os.path.exists(marcas) and "bpm" not in cfg:
            b = json.load(open(marcas, encoding="utf-8"))["batidas"]
            passo = b[-1] - b[-2]
            self.beats = b + [b[-1] + passo * (i + 1) for i in range(400)]
        else:
            bpm = float(cfg.get("bpm", 110))
            self.beats = [i * 60.0 / bpm for i in range(600)]

    def p(self, rel):
        path = rel if os.path.isabs(rel) else os.path.join(self.base, rel)
        if not os.path.exists(path):
            sair(f"não achei o arquivo: {path}")
        return path

    def asset(self, rel_dest, origem):
        self.files[rel_dest] = origem
        return "assets/" + rel_dest

    def beat(self, x):
        return next(i for i, b in enumerate(self.beats) if b >= x - 0.05)

    def footer(self, t, notes, dark=True):
        c, T = self.c, self.T
        line, ink = (T["foot_dark_line"], T["foot_dark_ink"]) if dark else (T["foot_light_line"], T["foot_light_ink"])
        sels = [c.box(60, 1600, 960, 2, line)]
        if self.cl.get("assinatura"):
            sels.append(c.text(60, 1624, 960, self.cl["assinatura"], "lbl", f"font-size:22px;line-height:28px;letter-spacing:2px;color:{ink};text-align:center;"))
        for i, note in enumerate(notes):
            sels.append(c.text(60, 1662 + i * 32, 960, note, "sans", f"font-size:22px;line-height:28px;color:{ink};text-align:center;"))
        for s in sels:
            c.fin(s, t, dy=0)

    def logo(self, y, lw, t):
        c = self.c
        if self.cl.get("logo_clara"):
            path = self.p(self.cl["logo_clara"])
            w, h = tamanho(path)
            src = self.asset("marca/logo" + os.path.splitext(path)[1].lower(), path)
            s = c.img((1080 - lw) // 2, y, lw, round(lw * h / w), src, alt=self.cl.get("nome", ""))
        else:
            s = c.text(40, y, 1000, self.cl.get("nome", ""), "serif", f"font-size:96px;line-height:104px;color:{self.T['cream']};text-align:center;")
        c.fin(s, t, dy=0, dur=0.9, ease="power2.out", scale=0.94)

    def capa_misterio(self, cid, x, y, w, h):
        """Quadro que esconde o DEPOIS até a revelação, com o símbolo da clínica (ou um losango) respirando."""
        T = self.T
        yid = self.c.uid("sym")
        sw = max(90, min(190, int(min(w, h) * 0.38)))
        if self.cl.get("simbolo"):
            path = self.p(self.cl["simbolo"])
            src = self.asset("marca/simbolo" + os.path.splitext(path)[1].lower(), path)
            inner = f'<img id="{yid}" src="{src}" alt="" style="width:{sw}px;height:{sw}px;object-fit:contain;display:block;" />'
        else:
            d = int(sw * 0.55)
            inner = f'<div id="{yid}" style="width:{d}px;height:{d}px;transform:rotate(45deg);border:3px solid {T["bronze"]};"></div>'
        div = (f'<div id="{cid}" class="cover" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;">{inner}</div>')
        return div, yid

    def vista(self, n, total_vistas, vista, t0, t1, t_rev, rotulo):
        c, T = self.c, self.T
        BG = self.DARK_BG
        c.open_scene(t0, t1, BG)
        c.eyebrow(150, rotulo.format(n=n + 1, total=total_vistas), T["bronze"], t0 + 0.1)
        s = c.text(40, 196, 1000, vista.get("titulo", ""), "serif", f"font-size:112px;line-height:124px;color:{T['cream']};text-align:center;", rich=True)
        c.fin(s, t0 + 0.2, dy=24, dur=0.7)
        PY, MAXW, MAXH = 470, 1000, 1060
        sid, cid = c.uid("shot"), c.uid("cover")

        if "foto" in vista:  # uma foto já montada: ANTES | DEPOIS
            path = self.p(vista["foto"])
            (iw, ih), (al, ar), (dl, dr), (top, bot) = metades(path)
            k = min(MAXW / iw, MAXH / ih)
            W, H = round(iw * k), round(ih * k)
            X = (1080 - W) // 2
            src = self.asset(f"fotos/vista{n + 1}{os.path.splitext(path)[1].lower()}", path)
            acx, dcx = X + (al + ar) / 2 * k, X + (dl + dr) / 2 * k
            cx0, cx1 = int(dl * k) - 1, int(-(-dr * k // 1)) + 1
            cy0, cy1 = int(top * k) - 1, int(-(-bot * k // 1)) + 1
            cover, yid = self.capa_misterio(cid, cx0, cy0, cx1 - cx0, cy1 - cy0)
            c.html.append(
                f'<div id="{sid}" class="shot" style="left:{X}px;top:{PY}px;width:{W}px;height:{H}px;">'
                f'<img src="{src}" alt="Antes e depois, vista {n + 1}" style="width:100%;height:100%;" />{cover}</div>'
            )
        else:  # duas fotos separadas
            pa, pd = self.p(vista["antes"]), self.p(vista["depois"])
            GAP, PW = 20, (MAXW - 20) // 2
            sizes = [tamanho(pa), tamanho(pd)]
            hs = [PW * h / w for w, h in sizes]
            k = min(1.0, MAXH / max(hs))
            pw = round(PW * k)
            ws, hs = [pw, pw], [round(h * k) for h in hs]
            H = max(hs)
            W = pw * 2 + GAP
            X = (1080 - W) // 2
            sa = self.asset(f"fotos/vista{n + 1}-antes{os.path.splitext(pa)[1].lower()}", pa)
            sd = self.asset(f"fotos/vista{n + 1}-depois{os.path.splitext(pd)[1].lower()}", pd)
            ya, yd = (H - hs[0]) // 2, (H - hs[1]) // 2
            dx = pw + GAP
            acx, dcx = X + pw / 2, X + dx + pw / 2
            cover, yid = self.capa_misterio(cid, dx - 1, yd - 1, pw + 2, hs[1] + 2)
            c.html.append(
                f'<div id="{sid}" class="shot pair" style="left:{X}px;top:{PY}px;width:{W}px;height:{H}px;">'
                f'<img src="{sa}" alt="Antes, vista {n + 1}" style="position:absolute;left:0;top:{ya}px;width:{pw}px;height:{hs[0]}px;" />'
                f'<img src="{sd}" alt="Depois, vista {n + 1}" style="position:absolute;left:{dx}px;top:{yd}px;width:{pw}px;height:{hs[1]}px;" />'
                f'{cover}</div>'
            )

        la = c.text(round(acx - 200), PY - 58, 400, "Antes", "lbl", f"font-size:30px;line-height:36px;letter-spacing:9px;color:{T['soft']};text-align:center;")
        ld = c.text(round(dcx - 200), PY - 58, 400, "Depois", "lbl", f"font-size:30px;line-height:36px;letter-spacing:9px;color:{T['dim']};text-align:center;")
        for s in (la, ld):
            c.fin(s, t0 + 0.35, dy=0)
        c.fin("#" + sid, t0 + 0.4, dy=30, dur=0.7)
        breath, t_b = 0.9, t0 + 1.1
        reps = max(0, int((t_rev - t_b) // breath) - 1)
        c.raw(f'tl.fromTo("#{yid}", {{scale: 1}}, {{scale: 1.06, duration: {breath}, ease: "sine.inOut", yoyo: true, repeat: {reps}, immediateRender: false}}, {t_b:.3f});')
        c.raw(f'tl.to("#{cid}", {{opacity: 0, duration: 0.7, ease: "power1.inOut"}}, {t_rev:.3f});')
        c.raw(f'tl.to("{ld}", {{color: "{T["bronze"]}", duration: 0.4}}, {t_rev:.3f});')
        c.sfx("assets/sons/revela.ogg", t_rev, 0.3, 0.14)
        self.footer(t0 + 0.3, self.notas)
        c.close_scene()

    def numeros(self, t0, t1, num):
        c, T = self.c, self.T
        pac = self.versao == "paciente"
        c.open_scene(t0, t1, self.LIGHT_BG, "cream")
        rot = num.get("rotulo_paciente" if pac else "rotulo", num.get("rotulo", ""))
        if rot:
            c.eyebrow(160, rot, T["ink"], t0 + 0.15)
        tit = num.get("titulo", ["O que a balança", "<em>não mostra</em>."])
        for i, linha in enumerate(tit[:2]):
            s = c.text(40, 214 + i * 112, 1000, linha, "serif", f"font-size:104px;line-height:112px;color:{T['text']};text-align:center;", rich=True)
            c.fin(s, t0 + 0.3 + i * 0.15, dy=24, dur=0.7)
        linhas = num["linhas"][:4]
        RY = 520
        RH = 250 if len(linhas) <= 3 else 190
        for r, ln_ in enumerate(linhas):
            label, a, b, unit, delta = (list(ln_) + ["", "", "", "", ""])[:5]
            y = RY + r * RH
            tr = t0 + 1.1 + r * 0.9
            ln = c.box(60, y, 960, 2, T["line"])
            c.raw(f'tl.fromTo("{ln}", {{scaleX: 0, transformOrigin: "0% 50%"}}, {{scaleX: 1, duration: 0.6, ease: "power2.out"}}, {tr - 0.2:.3f});')
            s = c.text(60, y + 34, 700, label, "lbl", f"font-size:26px;line-height:32px;letter-spacing:5px;color:{T['muted']};")
            c.fin(s, tr, dy=0)
            s = c.text(60, y + 92, 260, a, "serif", f"font-size:84px;line-height:100px;font-weight:400;color:{T['dim']};")
            c.fin(s, tr + 0.1, dy=12)
            s = c.text(232, y + 112, 80, "→", "sans", f"font-size:52px;line-height:60px;font-weight:300;color:{T['dim']};")
            c.fin(s, tr + 0.3, dy=0, dx=-16)
            vid = c.uid("val")
            c.html.append(
                f'<p id="{vid}" class="abs serif" style="left:316px;top:{y + 74}px;width:420px;font-size:116px;line-height:124px;font-weight:500;color:{T["text"]};">'
                f'{E(b)}<span class="sans" style="font-size:38px;font-weight:400;margin-left:10px;color:{T["muted"]};">{E(unit)}</span></p>'
            )
            c.fin("#" + vid, tr + 0.45, dy=20, dur=0.6)
            if delta:
                pid = c.uid("pill")
                c.html.append(
                    f'<div id="{pid}" class="abs" style="left:700px;top:{y + 112}px;width:320px;height:68px;background:{T["dark"]};display:flex;align-items:center;justify-content:center;">'
                    f'<span class="lbl" style="font-size:32px;letter-spacing:2px;color:{T["bronze"]};text-transform:none;">{E(delta)}</span></div>'
                )
                c.raw(f'tl.fromTo("#{pid}", {{opacity: 0, scale: 0.85}}, {{opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.7)"}}, {tr + 0.75:.3f});')
        ln = c.box(60, RY + len(linhas) * RH, 960, 2, T["line"])
        c.fin(ln, t0 + 1.1 + len(linhas) * 0.9, dy=0)
        fecho = num.get("fecho_paciente" if pac else "fecho", num.get("fecho", []))
        if fecho:
            tp = self.beats[self.beat(t0 + 1.5 + len(linhas) * 0.95)]
            yb = RY + len(linhas) * RH + (30 if len(linhas) >= 3 else 100)
            for i, linha in enumerate(fecho[:2]):
                s = c.text(40, yb + i * 88, 1000, linha, "serif", f"font-size:76px;line-height:88px;color:{T['text']};text-align:center;", rich=True)
                c.fin(s, tp + i * 0.2, dy=20, dur=0.7)
            c.sfx("assets/sons/revela.ogg", tp + 0.2, 0.25, 0.14)
        self.footer(t0 + 0.3, self.notas, dark=False)
        c.close_scene()

    def fechamento(self, to, ending):
        c, T, cl = self.c, self.T, self.cl
        total = round(to + ending, 2)
        c.open_scene(to, total, self.DARK_BG)
        lb = self.beats[self.beat(to + 0.5)]
        self.logo(300, 470, lb)
        c.sfx("assets/sons/sino.ogg", lb, 0.4, 1.48)
        if self.versao == "publico":
            pub = self.caso.get("final_publico", {})
            y = 640
            if pub.get("frase"):
                s = c.text(70, y, 940, pub["frase"], "serif", f"font-size:70px;line-height:84px;font-style:italic;color:{T['cream']};text-align:center;text-wrap:balance;", rich=True)
                c.fin(s, lb + 0.5, dy=20, dur=0.8)
                y = 1000
            if cl.get("nome_linha"):
                c.eyebrow(y, cl["nome_linha"], T["bronze"], lb + 1.0)
            cta = c.uid("cta")
            c.html.append(
                f'<div id="{cta}" class="abs" style="left:150px;top:{y + 110}px;width:780px;height:108px;border:2px solid {T["bronze"]};box-sizing:border-box;display:flex;align-items:center;justify-content:center;opacity:0;">'
                f'<span class="lbl" style="font-size:30px;letter-spacing:4px;color:{T["cream"]};">{E(pub.get("botao", "Agende sua avaliação"))}</span></div>'
            )
            c.raw(f'tl.fromTo("#{cta}", {{opacity: 0, scale: 0.94}}, {{opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.6)"}}, {lb + 1.4:.3f});')
            if pub.get("linha"):
                s = c.text(60, y + 276, 960, pub["linha"], "sans", f"font-size:34px;line-height:42px;font-weight:300;color:{T['soft']};text-align:center;")
                c.fin(s, lb + 1.8, dy=12)
            if cl.get("instagram"):
                s = c.text(60, y + 326, 960, cl["instagram"], "sans", f"font-size:34px;line-height:42px;font-weight:500;letter-spacing:1px;color:{T['bronze']};text-align:center;")
                c.fin(s, lb + 1.95, dy=12)
        else:
            pac = self.caso.get("final_paciente", {})
            s = c.text(40, 640, 1000, pac.get("titulo1", "Parabéns pela sua"), "serif", f"font-size:112px;line-height:120px;color:{T['cream']};text-align:center;", rich=True)
            c.fin(s, lb + 0.5, dy=24, dur=0.8)
            s = c.text(40, 760, 1000, pac.get("titulo2", "<em>jornada</em>."), "serif", f"font-size:112px;line-height:120px;color:{T['cream']};text-align:center;", rich=True)
            c.fin(s, lb + 0.65, dy=24, dur=0.8)
            for i, linha in enumerate([pac.get("periodo", ""), pac.get("agradecimento", "Obrigada pela confiança em cada etapa.")]):
                if linha:
                    s = c.text(90, 950 + i * 52, 900, linha, "sans", f"font-size:36px;line-height:48px;font-weight:300;color:{T['soft']};text-align:center;")
                    c.fin(s, lb + 1.3 + i * 0.3, dy=12)
            s = c.box(508, 1120, 64, 2, T["bronze"])
            c.raw(f'tl.fromTo("{s}", {{scaleX: 0}}, {{scaleX: 1, duration: 0.6, ease: "power2.out"}}, {lb + 2.2:.3f});')
            s = c.text(40, 1160, 1000, pac.get("despedida", "<em>Com carinho,</em>"), "serif", f"font-size:64px;line-height:72px;color:{T['cream']};text-align:center;", rich=True)
            c.fin(s, lb + 2.4, dy=16, dur=0.7)
            s = c.text(40, 1236, 1000, pac.get("assina", cl.get("nome", "")), "serif", f"font-size:88px;line-height:100px;font-weight:400;color:{T['cream']};text-align:center;")
            c.fin(s, lb + 2.6, dy=16, dur=0.7)
        self.footer(lb + 0.4, self.notas)
        c.close_scene()
        return total

    def montar(self):
        T, caso = self.T, self.caso
        pac = self.versao == "paciente"
        self.DARK_BG = f"radial-gradient(130% 70% at 50% 28%, {T['dark3']} 0%, {T['dark']} 55%, {T['dark2']} 100%)"
        self.LIGHT_BG = f"linear-gradient(180deg, {T['cream']} 0%, {T['warm']} 100%)"
        self.notas = [] if pac else [AVISO_RESULTADO, AVISO_AUTORIZACAO]
        metodo = caso.get("metodo", "")
        c = self.c

        # abertura
        i0 = self.beat(3.8)
        c.open_scene(0, self.beats[i0], self.DARK_BG)
        self.logo(500, 560, 0.1)
        rot = caso.get("rotulo_paciente" if pac else "rotulo") or (f"{metodo} · " if metodo else "") + ("sua jornada" if pac else "caso real")
        c.eyebrow(890, rot, T["bronze"], 0.7)
        abertura = caso.get("abertura", ["Não é só", "sobre o <em>peso</em>."])
        for i, linha in enumerate(abertura[:2]):
            s = c.text(40, 960 + i * 128, 1000, linha, "serif", f"font-size:120px;line-height:128px;color:{T['cream']};text-align:center;", rich=True)
            c.fin(s, 0.9 + i * 0.15, dy=28, dur=0.8)
        c.close_scene()

        # vistas, com o mistério
        vistas = caso["vistas"]
        if not 1 <= len(vistas) <= 4:
            sair("use de 1 a 4 vistas no config.")
        PER = 12
        rot_v = caso.get("rotulo_vista_paciente" if pac else "rotulo_vista") or (
            "Sua evolução · {n} de {total}" if pac else (f"{metodo} · " if metodo else "") + "caso real · {n} de {total}")
        for n, v in enumerate(vistas):
            bi = i0 + n * PER
            self.vista(n, len(vistas), v, self.beats[bi], self.beats[bi + PER], self.beats[bi + 5], rot_v)
        bn = i0 + len(vistas) * PER

        # números (opcional)
        num = caso.get("numeros")
        if num and num.get("linhas"):
            NPER = 16
            self.numeros(self.beats[bn], self.beats[bn + NPER], num)
            bn += NPER

        total = self.fechamento(self.beats[bn], 8.0 if pac else 6.5)
        return total

    def escrever(self, outdir, total):
        c, T = self.c, self.T
        c.scene_js()
        v = self.cfg.get("visual", {})
        fontes = {
            "titulo": v.get("fonte_titulo") and self.p(v["fonte_titulo"]) or os.path.join(MOTOR, "fontes", "CormorantGaramond.ttf"),
            "titulo_italico": v.get("fonte_titulo_italico") and self.p(v["fonte_titulo_italico"]) or os.path.join(MOTOR, "fontes", "CormorantGaramond-Italic.ttf"),
            "texto": v.get("fonte_texto") and self.p(v["fonte_texto"]) or os.path.join(MOTOR, "fontes", "Jost.ttf"),
        }
        fsrc = {k: self.asset("fontes/" + k + os.path.splitext(p)[1].lower(), p) for k, p in fontes.items()}
        self.asset("sons/revela.ogg", os.path.join(MOTOR, "sons", "revela.ogg"))
        self.asset("sons/sino.ogg", os.path.join(MOTOR, "sons", "sino.ogg"))
        gsap = os.path.join(RAIZ, "node_modules", "gsap", "dist", "gsap.min.js")
        if not os.path.exists(gsap):
            sair("falta instalar as dependências: rode  npm install  na pasta da ferramenta.")
        self.asset("vendor/gsap.min.js", gsap)
        music = ""
        if self.musica:
            mp = self.musica
            src = self.asset("musica" + os.path.splitext(mp)[1].lower(), mp)
            vol = float(self.cfg.get("volume_musica", 0.4))
            lane = [{"t": 0, "v": 0}, {"t": 0.6, "v": vol}, {"t": round(total - 1.2, 2), "v": vol}, {"t": total, "v": 0}]
            music = (f'<audio id="music" src="{src}" data-start="0" data-duration="{total}" data-track-index="10" data-volume="1" '
                     f"data-automation='{json.dumps({'version': 1, 'lanes': [{'target': 'volume', 'points': lane}]})}'></audio>")
        page = f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={c.W}, height={c.H}" />
    <title>{E(self.cl.get("nome", "Antes e depois"))}</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Titulo"; src: url("{fsrc['titulo']}"); font-weight: 300 700; font-style: normal; }}
      @font-face {{ font-family: "Titulo"; src: url("{fsrc['titulo_italico']}"); font-weight: 300 700; font-style: italic; }}
      @font-face {{ font-family: "Texto"; src: url("{fsrc['texto']}"); font-weight: 100 900; font-style: normal; }}
      body {{ margin: 0; background: {T['dark']}; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: {T['dark']}; }}
      .scene {{ position: absolute; inset: 0; opacity: 0; }}
      .bg {{ position: absolute; inset: 0; }}
      .abs {{ position: absolute; margin: 0; }}
      img.abs {{ display: block; }}
      .serif {{ font-family: "Titulo", serif; font-weight: 300; font-variant-numeric: lining-nums; }}
      .serif em {{ font-style: italic; color: {T['bronze']}; }}
      .cream .serif em {{ color: {T['ink']}; }}
      .sans {{ font-family: "Texto", sans-serif; font-weight: 400; }}
      .lbl {{ font-family: "Texto", sans-serif; font-weight: 500; text-transform: uppercase; margin: 0; }}
      .shot {{ position: absolute; opacity: 0; box-shadow: 0 30px 80px rgba(0, 0, 0, 0.55); }}
      .shot.pair {{ box-shadow: none; }}
      .shot img {{ display: block; }}
      .cover {{ position: absolute; background: {T['dark3']}; box-shadow: inset 0 0 0 2px {T['bronze']}59; display: flex; align-items: center; justify-content: center; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="{c.W}" data-height="{c.H}" data-duration="{total}">
{chr(10).join(c.html)}
      {music}
      {chr(10).join(c.audio)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join('      ' + l for l in c.js)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
        for dest, origem in self.files.items():
            d = os.path.join(outdir, "assets", dest)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copyfile(origem, d)  # cópia byte a byte, sem alterar nada
        with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(page)


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in ("paciente", "publico"):
        sair("uso: python motor/gerar.py CAMINHO/config.json paciente|publico [PASTA_DE_SAIDA]")
    cfg_path, versao = os.path.abspath(sys.argv[1]), sys.argv[2]
    base = os.path.dirname(cfg_path)
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    if versao == "publico" and cfg.get("autorizacao_paciente") is not True:
        sair('a versão pública só sai com a autorização da paciente. Confirme e marque "autorizacao_paciente": true no config.')
    saida = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else os.path.join(base, "saida", versao)
    outdir = os.path.join(saida, "composition")
    os.makedirs(outdir, exist_ok=True)
    for name in ("index.html", "assets"):
        pth = os.path.join(outdir, name)
        if os.path.isdir(pth):
            shutil.rmtree(pth)
        elif os.path.exists(pth):
            os.remove(pth)
    v = Video(cfg, base, versao)
    total = v.montar()
    v.escrever(outdir, total)
    print(f"{versao}: {total:.1f} s -> {outdir}")
    print("Agora, nessa pasta:  npx hyperframes check   e   npx hyperframes render --quality high --output ../video.mp4")


if __name__ == "__main__":
    main()
