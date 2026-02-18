#!/usr/bin/env python3
"""
Export ArchiMate diagrams dari format Grafico (coArchi v1) ke PNG
Format: folder-based XML (model/diagrams/*.xml, model/business/*.xml, dll)
"""

import xml.etree.ElementTree as ET
import os
import sys
import re

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    os.system("pip install Pillow -q")
    from PIL import Image, ImageDraw, ImageFont

ELEMENT_COLORS = {
    "BusinessActor":        ("#FFFFC0", "#8B8B00"),
    "BusinessRole":         ("#FFFFC0", "#8B8B00"),
    "BusinessProcess":      ("#FFFFC0", "#8B8B00"),
    "BusinessFunction":     ("#FFFFC0", "#8B8B00"),
    "BusinessService":      ("#FFFFC0", "#8B8B00"),
    "BusinessObject":       ("#FFFFC0", "#8B8B00"),
    "BusinessEvent":        ("#FFFFC0", "#8B8B00"),
    "BusinessInteraction":  ("#FFFFC0", "#8B8B00"),
    "BusinessCollaboration":("#FFFFC0", "#8B8B00"),
    "BusinessInterface":    ("#FFFFC0", "#8B8B00"),
    "Product":              ("#FFFFC0", "#8B8B00"),
    "ValueStream":          ("#F4A460", "#8B4513"),
    "Capability":           ("#F4A460", "#8B4513"),
    "Resource":             ("#F4A460", "#8B4513"),
    "CourseOfAction":       ("#F4A460", "#8B4513"),
    "ApplicationComponent": ("#C0E0FF", "#00008B"),
    "ApplicationService":   ("#C0E0FF", "#00008B"),
    "ApplicationFunction":  ("#C0E0FF", "#00008B"),
    "DataObject":           ("#C0E0FF", "#00008B"),
    "Node":                 ("#C0FFC0", "#006400"),
    "Device":               ("#C0FFC0", "#006400"),
    "SystemSoftware":       ("#C0FFC0", "#006400"),
    "TechnologyService":    ("#C0FFC0", "#006400"),
    "Artifact":             ("#C0FFC0", "#006400"),
    "Stakeholder":          ("#FFD700", "#8B6914"),
    "Goal":                 ("#FFD700", "#8B6914"),
    "Requirement":          ("#FFD700", "#8B6914"),
    "WorkPackage":          ("#FFB6C1", "#8B0000"),
    "Deliverable":          ("#FFB6C1", "#8B0000"),
    "Grouping":             ("#F5F5F5", "#999999"),
}
DEFAULT_COLOR = ("#F0F0F0", "#555555")

SCALE = 1.5
PADDING = 50
MIN_W = 1200
MIN_H = 800
FONT_SIZE = 12
TITLE_FONT_SIZE = 18


def strip_ns(tag):
    return re.sub(r'\{.*?\}', '', tag)


def get_colors(etype):
    etype_clean = strip_ns(str(etype)).replace("archimate:", "")
    for key, val in ELEMENT_COLORS.items():
        if key.lower() in etype_clean.lower():
            return val
    return DEFAULT_COLOR


def wrap_text(text, max_chars=18):
    words = str(text).split()
    lines, line = [], ""
    for w in words:
        if len(line) + len(w) + 1 <= max_chars:
            line = (line + " " + w).strip()
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines[:4]


def load_fonts():
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, FONT_SIZE), ImageFont.truetype(path, TITLE_FONT_SIZE)
            except Exception:
                pass
    f = ImageFont.load_default()
    return f, f


def parse_grafico(model_folder):
    """Baca format Grafico coArchi v1 — folder-based XML"""
    elements_map = {}
    for subdir in ["business","application","technology","motivation",
                   "strategy","implementation_migration","other","relations"]:
        folder = os.path.join(model_folder, subdir)
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            if not fname.endswith(".xml"):
                continue
            try:
                root = ET.parse(os.path.join(folder, fname)).getroot()
                eid = root.get("id")
                if eid:
                    elements_map[eid] = {
                        "id": eid,
                        "name": root.get("name", ""),
                        "type": root.tag,
                    }
            except Exception as e:
                print(f"  [warn] {fname}: {e}")

    print(f"  Total elemen: {len(elements_map)}")

    diagrams = []
    diagrams_folder = os.path.join(model_folder, "diagrams")
    if not os.path.isdir(diagrams_folder):
        print(f"  [warn] Folder diagrams/ tidak ada di: {model_folder}")
        return diagrams, elements_map

    for fname in sorted(os.listdir(diagrams_folder)):
        if not fname.endswith(".xml"):
            continue
        try:
            root = ET.parse(os.path.join(diagrams_folder, fname)).getroot()
            print(f"  Found diagram: '{root.get('name', fname)}'")
            diagrams.append(root)
        except Exception as e:
            print(f"  [warn] {fname}: {e}")

    return diagrams, elements_map


def collect_nodes(elem, elements_map, offset_x=0, offset_y=0):
    nodes, connections = [], []
    for child in elem:
        tag = strip_ns(child.tag)
        if tag in ("child", "children", "node"):
            bounds = next((b for b in child if strip_ns(b.tag) == "bounds"), None)
            if bounds is not None:
                x = int(float(bounds.get("x", 0))) + offset_x
                y = int(float(bounds.get("y", 0))) + offset_y
                w = int(float(bounds.get("width", 120)))
                h = int(float(bounds.get("height", 55)))
                xsi_type = child.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
                arch_id = child.get("archimateElement", "")
                node_id = child.get("id", "")
                etype = xsi_type
                label = child.get("name", "")
                if arch_id and arch_id in elements_map:
                    if not label:
                        label = elements_map[arch_id].get("name", "")
                    if not etype:
                        etype = elements_map[arch_id].get("type", "")
                nodes.append({"id": node_id, "x": x, "y": y, "w": w, "h": h,
                               "label": label, "type": etype})
                cn, cc = collect_nodes(child, elements_map, x, y)
                nodes.extend(cn)
                connections.extend(cc)
        elif tag in ("sourceConnection", "connection"):
            src = child.get("source", "")
            tgt = child.get("target", "")
            if src and tgt:
                connections.append((src, tgt))
    return nodes, connections


def draw_diagram(diagram, elements_map, output_path, font, bold_font):
    name = diagram.get("name", "Untitled")
    nodes, connections = collect_nodes(diagram, elements_map)

    if not nodes:
        print(f"  [skip] '{name}' — tidak ada elemen visual")
        return False

    min_x = min(n["x"] for n in nodes)
    min_y = min(n["y"] for n in nodes)
    max_x = max(n["x"] + n["w"] for n in nodes)
    max_y = max(n["y"] + n["h"] for n in nodes)

    canvas_w = max(int((max_x - min_x) * SCALE) + PADDING * 2, MIN_W)
    canvas_h = max(int((max_y - min_y) * SCALE) + PADDING * 2 + 60, MIN_H)

    img = Image.new("RGB", (canvas_w, canvas_h), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (canvas_w, 50)], fill="#2C3E50")
    draw.text((PADDING, 14), name, fill="#FFFFFF", font=bold_font)

    ox, oy = -min_x, -min_y
    id_map = {n["id"]: n for n in nodes if n.get("id")}

    for src_id, tgt_id in connections:
        src = id_map.get(src_id)
        tgt = id_map.get(tgt_id)
        if src and tgt:
            sx = int((src["x"] + src["w"]/2 + ox) * SCALE) + PADDING
            sy = int((src["y"] + src["h"]/2 + oy) * SCALE) + PADDING + 60
            tx = int((tgt["x"] + tgt["w"]/2 + ox) * SCALE) + PADDING
            ty = int((tgt["y"] + tgt["h"]/2 + oy) * SCALE) + PADDING + 60
            draw.line([(sx, sy), (tx, ty)], fill="#7F8C8D", width=2)
            dx, dy = tx-sx, ty-sy
            length = max((dx**2+dy**2)**0.5, 1)
            al = 10
            ax2 = tx - al*dx/length
            ay2 = ty - al*dy/length
            px = -dy/length*5
            py = dx/length*5
            draw.polygon([(tx,ty),(int(ax2+px),int(ay2+py)),(int(ax2-px),int(ay2-py))], fill="#7F8C8D")

    for n in sorted(nodes, key=lambda n: n["w"]*n["h"], reverse=True):
        x1 = int((n["x"]+ox)*SCALE)+PADDING
        y1 = int((n["y"]+oy)*SCALE)+PADDING+60
        x2 = x1+int(n["w"]*SCALE)
        y2 = y1+int(n["h"]*SCALE)
        fill, border = get_colors(n["type"])
        draw.rectangle([x1,y1,x2,y2], fill=fill, outline=border, width=2)
        label = n["label"] or strip_ns(n["type"]).replace("archimate:","") or "?"
        lines = wrap_text(label, max_chars=max(8, int(n["w"]*SCALE/7)))
        line_h = FONT_SIZE+4
        total_h = len(lines)*line_h
        ty2 = y1+max(4,(y2-y1-total_h)//2)
        for line in lines:
            try:
                bbox = draw.textbbox((0,0), line, font=font)
                tw = bbox[2]-bbox[0]
            except Exception:
                tw = len(line)*7
            draw.text((x1+max(4,(x2-x1-tw)//2), ty2), line, fill="#1a1a1a", font=font)
            ty2 += line_h

    img.save(output_path, "PNG", dpi=(150,150))
    print(f"  ✅ {output_path} ({len(nodes)} elemen)")
    return True


def main():
    model_folder = os.environ.get("MODEL_FOLDER", "model")
    output_folder = os.environ.get("OUTPUT_FOLDER", "exports")

    if not os.path.isdir(model_folder):
        model_folder = "/github/workspace/model"
    if not os.path.isdir(model_folder):
        print(f"ERROR: Folder model tidak ditemukan!")
        sys.exit(1)

    os.makedirs(output_folder, exist_ok=True)
    print(f"📂 Model  : {model_folder}")
    print(f"📁 Output : {output_folder}\n")

    diagrams, elements_map = parse_grafico(model_folder)

    if not diagrams:
        print("❌ Tidak ada diagram ditemukan!")
        sys.exit(1)

    print(f"\n🎨 Export {len(diagrams)} diagram...\n")
    font, bold_font = load_fonts()

    exported = 0
    for diagram in diagrams:
        dname = diagram.get("name", "Untitled")
        safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', dname)
        out = os.path.join(output_folder, f"{safe}.png")
        print(f"→ {dname}")
        if draw_diagram(diagram, elements_map, out, font, bold_font):
            exported += 1

    print(f"\n✅ Selesai! {exported}/{len(diagrams)} diagram di-export")


if __name__ == "__main__":
    main()
