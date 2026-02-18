#!/usr/bin/env python3
"""
Export ArchiMate diagrams dari format Grafico (coArchi v1) ke PNG
Dengan simbol relasi ArchiMate yang benar
"""

import xml.etree.ElementTree as ET
import os
import sys
import re
import math

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    os.system("pip install Pillow -q")
    from PIL import Image, ImageDraw, ImageFont

ELEMENT_COLORS = {
    "BusinessActor":         ("#FFFFC0", "#8B8B00"),
    "BusinessRole":          ("#FFFFC0", "#8B8B00"),
    "BusinessProcess":       ("#FFFFC0", "#8B8B00"),
    "BusinessFunction":      ("#FFFFC0", "#8B8B00"),
    "BusinessService":       ("#FFFFC0", "#8B8B00"),
    "BusinessObject":        ("#FFFFC0", "#8B8B00"),
    "BusinessEvent":         ("#FFFFC0", "#8B8B00"),
    "BusinessInteraction":   ("#FFFFC0", "#8B8B00"),
    "BusinessCollaboration": ("#FFFFC0", "#8B8B00"),
    "BusinessInterface":     ("#FFFFC0", "#8B8B00"),
    "Product":               ("#FFFFC0", "#8B8B00"),
    "ValueStream":           ("#FFE0B0", "#8B5000"),
    "Capability":            ("#FFE0B0", "#8B5000"),
    "Resource":              ("#FFE0B0", "#8B5000"),
    "CourseOfAction":        ("#FFE0B0", "#8B5000"),
    "ApplicationComponent":  ("#C0E0FF", "#00008B"),
    "ApplicationService":    ("#C0E0FF", "#00008B"),
    "ApplicationFunction":   ("#C0E0FF", "#00008B"),
    "ApplicationProcess":    ("#C0E0FF", "#00008B"),
    "DataObject":            ("#C0E0FF", "#00008B"),
    "Node":                  ("#C0FFC0", "#006400"),
    "Device":                ("#C0FFC0", "#006400"),
    "SystemSoftware":        ("#C0FFC0", "#006400"),
    "TechnologyService":     ("#C0FFC0", "#006400"),
    "Artifact":              ("#C0FFC0", "#006400"),
    "Stakeholder":           ("#FFD700", "#8B6914"),
    "Goal":                  ("#FFD700", "#8B6914"),
    "Requirement":           ("#FFD700", "#8B6914"),
    "WorkPackage":           ("#FFB6C1", "#8B0000"),
    "Deliverable":           ("#FFB6C1", "#8B0000"),
    "Grouping":              ("#F0F0F0", "#888888"),
}
DEFAULT_COLOR = ("#F5F5F5", "#666666")

SCALE = 1.5
PADDING = 60
MIN_W = 1400
MIN_H = 900
FONT_SIZE = 12
TITLE_FONT_SIZE = 18


def strip_ns(tag):
    return re.sub(r'\{.*?\}', '', tag)


def get_type(xsi_type):
    return xsi_type.split(":")[-1] if ":" in xsi_type else xsi_type


def get_colors(etype):
    etype_clean = get_type(str(etype))
    for key, val in ELEMENT_COLORS.items():
        if key.lower() == etype_clean.lower():
            return val
    for key, val in ELEMENT_COLORS.items():
        if key.lower() in etype_clean.lower():
            return val
    return DEFAULT_COLOR


def load_fonts():
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if os.path.exists(path):
            try:
                return (ImageFont.truetype(path, FONT_SIZE),
                        ImageFont.truetype(path, TITLE_FONT_SIZE))
            except Exception:
                pass
    f = ImageFont.load_default()
    return f, f


def wrap_text(text, max_chars=16):
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


# ─── SIMBOL RELASI ARCHIMATE ──────────────────────────────────────────────────

def draw_arrow_open(draw, tx, ty, dx, dy, length, color, size=12):
    """Panah terbuka → (Triggering, Serving, Association)"""
    ax = tx - size * dx / length
    ay = ty - size * dy / length
    px = -dy / length * 6
    py = dx / length * 6
    draw.line([(tx, ty), (int(ax + px), int(ay + py))], fill=color, width=2)
    draw.line([(tx, ty), (int(ax - px), int(ay - py))], fill=color, width=2)


def draw_arrow_filled(draw, tx, ty, dx, dy, length, color, size=12):
    """Panah solid ▶ (Triggering solid)"""
    ax = tx - size * dx / length
    ay = ty - size * dy / length
    px = -dy / length * 6
    py = dx / length * 6
    draw.polygon(
        [(tx, ty), (int(ax + px), int(ay + py)), (int(ax - px), int(ay - py))],
        fill=color
    )


def draw_arrow_hollow(draw, tx, ty, dx, dy, length, color, size=14):
    """Panah terbuka kosong △ (Realization, Specialization)"""
    ax = tx - size * dx / length
    ay = ty - size * dy / length
    px = -dy / length * 7
    py = dx / length * 7
    draw.polygon(
        [(tx, ty), (int(ax + px), int(ay + py)), (int(ax - px), int(ay - py))],
        fill="#FFFFFF", outline=color, width=2
    )


def draw_diamond_filled(draw, sx, sy, dx, dy, length, color, size=12):
    """Diamond solid ◆ (Composition) — di source"""
    ex = sx + size * dx / length
    ey = sy + size * dy / length
    mx = sx + (size / 2) * dx / length
    my = sy + (size / 2) * dy / length
    px = -dy / length * 6
    py = dx / length * 6
    draw.polygon(
        [(sx, sy), (int(mx + px), int(my + py)),
         (int(ex), int(ey)), (int(mx - px), int(my - py))],
        fill=color
    )


def draw_diamond_hollow(draw, sx, sy, dx, dy, length, color, size=12):
    """Diamond kosong ◇ (Aggregation) — di source"""
    ex = sx + size * dx / length
    ey = sy + size * dy / length
    mx = sx + (size / 2) * dx / length
    my = sy + (size / 2) * dy / length
    px = -dy / length * 6
    py = dx / length * 6
    draw.polygon(
        [(sx, sy), (int(mx + px), int(my + py)),
         (int(ex), int(ey)), (int(mx - px), int(my - py))],
        fill="#FFFFFF", outline=color, width=2
    )


def draw_circle_filled(draw, sx, sy, dx, dy, length, color, r=7):
    """Lingkaran solid ● (Assignment) — di source"""
    cx = int(sx + r * dx / length)
    cy = int(sy + r * dy / length)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)


def draw_connection(draw, conn, src_node, tgt_node, ox, oy):
    """Gambar satu koneksi dengan simbol ArchiMate yang tepat"""
    rel_type = conn.get("type", "")
    rel_clean = get_type(rel_type)

    sx = int((src_node["x"] + src_node["w"] / 2 + ox) * SCALE) + PADDING
    sy = int((src_node["y"] + src_node["h"] / 2 + oy) * SCALE) + PADDING + 60
    tx = int((tgt_node["x"] + tgt_node["w"] / 2 + ox) * SCALE) + PADDING
    ty = int((tgt_node["y"] + tgt_node["h"] / 2 + oy) * SCALE) + PADDING + 60

    dx = tx - sx
    dy = ty - sy
    length = max(math.sqrt(dx**2 + dy**2), 1)

    # Warna dan style garis per relasi
    LINE_STYLES = {
        "TriggeringRelationship":     ("#000000", "solid"),
        "FlowRelationship":           ("#000000", "solid"),
        "RealizationRelationship":    ("#000000", "dashed"),
        "AssignmentRelationship":     ("#000000", "solid"),
        "CompositionRelationship":    ("#000000", "solid"),
        "AggregationRelationship":    ("#000000", "solid"),
        "AssociationRelationship":    ("#555555", "solid"),
        "ServingRelationship":        ("#000000", "solid"),
        "AccessRelationship":         ("#555555", "dashed"),
        "InfluenceRelationship":      ("#555555", "dashed"),
        "SpecializationRelationship": ("#000000", "solid"),
    }

    style = LINE_STYLES.get(rel_clean, ("#555555", "solid"))
    color = style[0]
    is_dashed = style[1] == "dashed"

    # Gambar garis (solid atau dashed)
    if is_dashed:
        # Simulasi dashed dengan segmen pendek
        dash_len = 8
        gap_len = 6
        total = int(length)
        pos = 0
        while pos < total:
            end = min(pos + dash_len, total)
            x1 = int(sx + pos * dx / length)
            y1 = int(sy + pos * dy / length)
            x2 = int(sx + end * dx / length)
            y2 = int(sy + end * dy / length)
            draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
            pos += dash_len + gap_len
    else:
        draw.line([(sx, sy), (tx, ty)], fill=color, width=2)

    # Gambar simbol di ujung TARGET (arrow head)
    if rel_clean in ("TriggeringRelationship", "FlowRelationship"):
        draw_arrow_filled(draw, tx, ty, dx, dy, length, color)

    elif rel_clean in ("RealizationRelationship", "SpecializationRelationship"):
        draw_arrow_hollow(draw, tx, ty, dx, dy, length, color)

    elif rel_clean == "ServingRelationship":
        draw_arrow_open(draw, tx, ty, dx, dy, length, color)

    elif rel_clean == "AssociationRelationship":
        draw_arrow_open(draw, tx, ty, dx, dy, length, color)

    elif rel_clean == "InfluenceRelationship":
        draw_arrow_open(draw, tx, ty, dx, dy, length, color)

    # Gambar simbol di ujung SOURCE
    if rel_clean == "AssignmentRelationship":
        draw_circle_filled(draw, sx, sy, dx, dy, length, color)
        draw_arrow_filled(draw, tx, ty, dx, dy, length, color)

    elif rel_clean == "CompositionRelationship":
        draw_diamond_filled(draw, sx, sy, dx, dy, length, color)

    elif rel_clean == "AggregationRelationship":
        draw_diamond_hollow(draw, sx, sy, dx, dy, length, color)


def parse_grafico(model_folder):
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
                        "type": strip_ns(root.tag),
                    }
            except Exception as e:
                print(f"  [warn] {fname}: {e}")

    print(f"  Total elemen: {len(elements_map)}")

    diagrams = []
    diagrams_folder = os.path.join(model_folder, "diagrams")
    if not os.path.isdir(diagrams_folder):
        print(f"  [warn] Folder diagrams/ tidak ada")
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


def resolve_element(child, elements_map):
    xsi_type = child.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
    elem_name = child.get("name", "")
    arch_type = ""
    for sub in child:
        if strip_ns(sub.tag) == "archimateElement":
            sub_xsi = sub.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
            arch_type = get_type(sub_xsi)
            href = sub.get("href", "")
            if "#" in href:
                ref_id = href.split("#")[-1]
                if ref_id in elements_map:
                    edata = elements_map[ref_id]
                    if not elem_name:
                        elem_name = edata.get("name", "")
                    if not arch_type:
                        arch_type = edata.get("type", "")
            break
    return elem_name, arch_type if arch_type else get_type(xsi_type)


def resolve_relation_type(conn):
    for sub in conn:
        if strip_ns(sub.tag) == "archimateRelationship":
            xsi = sub.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
            return get_type(xsi)
    return get_type(conn.get("{http://www.w3.org/2001/XMLSchema-instance}type", ""))


def collect_all(elem, elements_map, offset_x=0, offset_y=0):
    nodes, connections = [], []
    for child in elem:
        tag = strip_ns(child.tag)
        if tag == "children":
            bounds = next((b for b in child if strip_ns(b.tag) == "bounds"), None)
            if bounds is not None:
                x = int(float(bounds.get("x", 0))) + offset_x
                y = int(float(bounds.get("y", 0))) + offset_y
                w = int(float(bounds.get("width", 120)))
                h = int(float(bounds.get("height", 55)))
                node_id = child.get("id", "")
                xsi_type = child.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
                elem_name, elem_type = resolve_element(child, elements_map)
                nodes.append({"id": node_id, "x": x, "y": y, "w": w, "h": h,
                               "label": elem_name, "type": elem_type, "xsi_type": xsi_type})
                # Kumpulkan sourceConnections
                for sub in child:
                    if strip_ns(sub.tag) == "sourceConnections":
                        src = sub.get("source", node_id)
                        tgt = sub.get("target", "")
                        rel = resolve_relation_type(sub)
                        if tgt:
                            connections.append({"source": src or node_id,
                                                "target": tgt, "type": rel})
                # Rekursif
                cn, cc = collect_all(child, elements_map, x, y)
                nodes.extend(cn)
                connections.extend(cc)
    return nodes, connections


def draw_diagram(diagram, elements_map, output_path, font, bold_font):
    name = diagram.get("name", "Untitled")
    nodes, connections = collect_all(diagram, elements_map)

    if not nodes:
        print(f"  [skip] '{name}' — tidak ada elemen visual")
        return False

    min_x = min(n["x"] for n in nodes)
    min_y = min(n["y"] for n in nodes)
    max_x = max(n["x"] + n["w"] for n in nodes)
    max_y = max(n["y"] + n["h"] for n in nodes)

    canvas_w = max(int((max_x - min_x) * SCALE) + PADDING * 2, MIN_W)
    canvas_h = max(int((max_y - min_y) * SCALE) + PADDING * 2 + 70, MIN_H)

    img = Image.new("RGB", (canvas_w, canvas_h), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([(0, 0), (canvas_w, 52)], fill="#2C3E50")
    draw.text((PADDING, 15), name, fill="#FFFFFF", font=bold_font)

    ox, oy = -min_x, -min_y
    id_map = {n["id"]: n for n in nodes if n.get("id")}

    # Gambar koneksi dulu
    seen = set()
    for conn in connections:
        key = (conn["source"], conn["target"])
        if key in seen:
            continue
        seen.add(key)
        src = id_map.get(conn["source"])
        tgt = id_map.get(conn["target"])
        if src and tgt:
            draw_connection(draw, conn, src, tgt, ox, oy)

    # Gambar node (besar dulu = background)
    for n in sorted(nodes, key=lambda n: n["w"] * n["h"], reverse=True):
        x1 = int((n["x"] + ox) * SCALE) + PADDING
        y1 = int((n["y"] + oy) * SCALE) + PADDING + 60
        x2 = x1 + int(n["w"] * SCALE)
        y2 = y1 + int(n["h"] * SCALE)

        fill, border = get_colors(n["type"])
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=border, width=2)

        label = n["label"] or n["type"] or "?"
        lines = wrap_text(label, max_chars=max(8, int(n["w"] * SCALE / 8)))
        line_h = FONT_SIZE + 4
        total_h = len(lines) * line_h
        ty_s = y1 + max(6, (y2 - y1 - total_h) // 2)
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(line) * 7
            draw.text((x1 + max(4, (x2 - x1 - tw) // 2), ty_s),
                      line, fill="#1a1a1a", font=font)
            ty_s += line_h

    img.save(output_path, "PNG", dpi=(150, 150))
    print(f"  ✅ {output_path} ({len(nodes)} nodes, {len(connections)} koneksi)")
    return True


def main():
    model_folder = os.environ.get("MODEL_FOLDER", "model")
    output_folder = os.environ.get("OUTPUT_FOLDER", "exports")
    if not os.path.isdir(model_folder):
        model_folder = "/github/workspace/model"
    if not os.path.isdir(model_folder):
        print("ERROR: Folder model tidak ditemukan!")
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
