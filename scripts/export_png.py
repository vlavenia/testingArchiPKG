#!/usr/bin/env python3
"""
Export ArchiMate diagrams dari file .archimate ke PNG
Menggunakan: xml.etree.ElementTree + Pillow + matplotlib
"""

import xml.etree.ElementTree as ET
import os
import sys
import re
import json

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    os.system("pip install Pillow --break-system-packages -q")
    from PIL import Image, ImageDraw, ImageFont

# ─── Warna per layer ArchiMate ───────────────────────────────────────────────
ELEMENT_COLORS = {
    # Business layer
    "BusinessActor":       ("#FFFFC0", "#8B8B00"),
    "BusinessRole":        ("#FFFFC0", "#8B8B00"),
    "BusinessProcess":     ("#FFFFC0", "#8B8B00"),
    "BusinessFunction":    ("#FFFFC0", "#8B8B00"),
    "BusinessService":     ("#FFFFC0", "#8B8B00"),
    "BusinessObject":      ("#FFFFC0", "#8B8B00"),
    "BusinessEvent":       ("#FFFFC0", "#8B8B00"),
    "BusinessInteraction": ("#FFFFC0", "#8B8B00"),
    "BusinessCollaboration":("#FFFFC0","#8B8B00"),
    "BusinessInterface":   ("#FFFFC0", "#8B8B00"),
    "Product":             ("#FFFFC0", "#8B8B00"),
    "Contract":            ("#FFFFC0", "#8B8B00"),
    "Representation":      ("#FFFFC0", "#8B8B00"),
    # Application layer
    "ApplicationComponent":("#C0E0FF", "#00008B"),
    "ApplicationService":  ("#C0E0FF", "#00008B"),
    "ApplicationFunction": ("#C0E0FF", "#00008B"),
    "ApplicationProcess":  ("#C0E0FF", "#00008B"),
    "ApplicationEvent":    ("#C0E0FF", "#00008B"),
    "ApplicationInterface":("#C0E0FF", "#00008B"),
    "ApplicationCollaboration":("#C0E0FF","#00008B"),
    "ApplicationInteraction":("#C0E0FF","#00008B"),
    "DataObject":          ("#C0E0FF", "#00008B"),
    # Technology layer
    "Node":                ("#C0FFC0", "#006400"),
    "Device":              ("#C0FFC0", "#006400"),
    "SystemSoftware":      ("#C0FFC0", "#006400"),
    "TechnologyService":   ("#C0FFC0", "#006400"),
    "TechnologyFunction":  ("#C0FFC0", "#006400"),
    "TechnologyProcess":   ("#C0FFC0", "#006400"),
    "TechnologyEvent":     ("#C0FFC0", "#006400"),
    "TechnologyInterface": ("#C0FFC0", "#006400"),
    "CommunicationPath":   ("#C0FFC0", "#006400"),
    "Network":             ("#C0FFC0", "#006400"),
    "Artifact":            ("#C0FFC0", "#006400"),
    # Motivation
    "Stakeholder":         ("#FFD700", "#8B6914"),
    "Driver":              ("#FFD700", "#8B6914"),
    "Assessment":          ("#FFD700", "#8B6914"),
    "Goal":                ("#FFD700", "#8B6914"),
    "Principle":           ("#FFD700", "#8B6914"),
    "Requirement":         ("#FFD700", "#8B6914"),
    "Constraint":          ("#FFD700", "#8B6914"),
    "Value":               ("#FFD700", "#8B6914"),
    "Meaning":             ("#FFD700", "#8B6914"),
    # Strategy
    "Resource":            ("#F4A460", "#8B4513"),
    "Capability":          ("#F4A460", "#8B4513"),
    "ValueStream":         ("#F4A460", "#8B4513"),
    "CourseOfAction":      ("#F4A460", "#8B4513"),
    # Implementation
    "WorkPackage":         ("#FFB6C1", "#8B0000"),
    "Deliverable":         ("#FFB6C1", "#8B0000"),
    "ImplementationEvent": ("#FFB6C1", "#8B0000"),
    "Gap":                 ("#FFB6C1", "#8B0000"),
    "Plateau":             ("#FFB6C1", "#8B0000"),
    # Other / Group
    "Grouping":            ("#F5F5F5", "#999999"),
    "Junction":            ("#FFFFFF", "#333333"),
}
DEFAULT_COLOR = ("#F0F0F0", "#555555")

NS = {
    "archimate": "http://www.archimatetool.com/archimate",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

SCALE = 1.5
PADDING = 40
MIN_W = 1200
MIN_H = 800
FONT_SIZE = 12
TITLE_FONT_SIZE = 18


def strip_ns(tag):
    return re.sub(r'\{.*?\}', '', tag)


def get_element_type(elem, elements_map):
    eid = elem.get("archimateElement") or elem.get("id")
    if eid and eid in elements_map:
        raw = elements_map[eid].get("type", "")
        return strip_ns(raw).replace("archimate:", "")
    raw = elem.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
    return strip_ns(raw).replace("archimate:", "")


def get_colors(etype):
    for key, val in ELEMENT_COLORS.items():
        if key.lower() in etype.lower():
            return val
    return DEFAULT_COLOR


def wrap_text(text, max_chars=18):
    words = text.split()
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
    return lines[:4]  # max 4 baris


def load_fonts():
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE)
        bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", TITLE_FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()
        bold = font
    return font, bold


def parse_archimate(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Build elements map {id -> element attribs}
    elements_map = {}
    for elem in root.iter():
        eid = elem.get("id")
        if eid:
            elements_map[eid] = dict(elem.attrib)
            elements_map[eid]["type"] = elem.tag
            name = elem.get("name", "")
            if name:
                elements_map[eid]["name"] = name

    # Find all diagrams/views
    diagrams = []
    for elem in root.iter():
        tag = strip_ns(elem.tag)
        if tag in ("ArchimateDiagramModel", "SketchModel", "CanvasModel"):
            diagrams.append(elem)

    return diagrams, elements_map


def draw_diagram(diagram, elements_map, output_path, font, bold_font):
    name = diagram.get("name", "Untitled")

    # Collect all child elements with bounds
    nodes = []
    connections = []

    def collect(elem, offset_x=0, offset_y=0):
        for child in elem:
            tag = strip_ns(child.tag)
            if tag == "children":
                collect(child, offset_x, offset_y)
            elif tag == "child" or tag == "node":
                bounds = child.find("bounds") or child.find("{*}bounds")
                if bounds is not None:
                    x = int(float(bounds.get("x", 0))) + offset_x
                    y = int(float(bounds.get("y", 0))) + offset_y
                    w = int(float(bounds.get("width", 120)))
                    h = int(float(bounds.get("height", 55)))
                    etype = get_element_type(child, elements_map)
                    eid = child.get("archimateElement") or child.get("id", "")
                    label = child.get("name", "")
                    if not label and eid in elements_map:
                        label = elements_map[eid].get("name", "")
                    nodes.append({"x": x, "y": y, "w": w, "h": h,
                                  "label": label, "type": etype, "id": child.get("id")})
                    collect(child, x, y)
            elif tag in ("sourceConnection", "connection"):
                src = child.get("source")
                tgt = child.get("target")
                if src and tgt:
                    connections.append((src, tgt))
                collect(child, offset_x, offset_y)

    collect(diagram)

    if not nodes:
        print(f"  [skip] Diagram '{name}' tidak memiliki elemen visual")
        return False

    # Hitung canvas size
    max_x = max(n["x"] + n["w"] for n in nodes)
    max_y = max(n["y"] + n["h"] for n in nodes)
    min_x = min(n["x"] for n in nodes)
    min_y = min(n["y"] for n in nodes)

    canvas_w = max(int((max_x - min_x) * SCALE) + PADDING * 2, MIN_W)
    canvas_h = max(int((max_y - min_y) * SCALE) + PADDING * 2 + 50, MIN_H)

    img = Image.new("RGB", (canvas_w, canvas_h), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((PADDING, 10), name, fill="#1a1a1a", font=bold_font)
    draw.line([(PADDING, 36), (canvas_w - PADDING, 36)], fill="#CCCCCC", width=1)

    offset_x = -min_x
    offset_y = -min_y

    # Build id->node map for connections
    id_map = {n["id"]: n for n in nodes if n.get("id")}

    # Draw connections
    for src_id, tgt_id in connections:
        src = id_map.get(src_id)
        tgt = id_map.get(tgt_id)
        if src and tgt:
            sx = int((src["x"] + src["w"] / 2 + offset_x) * SCALE) + PADDING
            sy = int((src["y"] + src["h"] / 2 + offset_y) * SCALE) + PADDING + 40
            tx = int((tgt["x"] + tgt["w"] / 2 + offset_x) * SCALE) + PADDING
            ty = int((tgt["y"] + tgt["h"] / 2 + offset_y) * SCALE) + PADDING + 40
            draw.line([(sx, sy), (tx, ty)], fill="#555555", width=2)
            # Arrow head
            dx, dy = tx - sx, ty - sy
            length = max((dx**2 + dy**2) ** 0.5, 1)
            arrow_len = 10
            ax = tx - arrow_len * dx / length
            ay = ty - arrow_len * dy / length
            perp_x = -dy / length * 5
            perp_y = dx / length * 5
            draw.polygon([(tx, ty),
                          (int(ax + perp_x), int(ay + perp_y)),
                          (int(ax - perp_x), int(ay - perp_y))],
                         fill="#555555")

    # Draw nodes
    for n in nodes:
        x1 = int((n["x"] + offset_x) * SCALE) + PADDING
        y1 = int((n["y"] + offset_y) * SCALE) + PADDING + 40
        x2 = x1 + int(n["w"] * SCALE)
        y2 = y1 + int(n["h"] * SCALE)

        fill, border = get_colors(n["type"])
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=border, width=2)

        # Label
        label = n["label"] or n["type"]
        lines = wrap_text(label, max_chars=max(8, int(n["w"] * SCALE / 7)))
        line_h = FONT_SIZE + 3
        total_h = len(lines) * line_h
        text_y = y1 + (y2 - y1 - total_h) // 2
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(line) * 7
            text_x = x1 + (x2 - x1 - tw) // 2
            draw.text((text_x, text_y), line, fill="#1a1a1a", font=font)
            text_y += line_h

    img.save(output_path, "PNG", dpi=(150, 150))
    return True


def main():
    model_path = os.environ.get("MODEL_PATH", "/github/workspace/model/testinganarchipkg.archimate")
    output_folder = os.environ.get("OUTPUT_FOLDER", "/github/workspace/exports")

    # Cari file .archimate jika tidak ditemukan di path default
    if not os.path.exists(model_path):
        base = os.path.dirname(model_path) if "/" in model_path else "model"
        for root_dir, dirs, files in os.walk(base):
            for f in files:
                if f.endswith(".archimate"):
                    model_path = os.path.join(root_dir, f)
                    print(f"Found model: {model_path}")
                    break

    if not os.path.exists(model_path):
        print(f"ERROR: File tidak ditemukan: {model_path}")
        sys.exit(1)

    os.makedirs(output_folder, exist_ok=True)
    print(f"Parsing: {model_path}")

    diagrams, elements_map = parse_archimate(model_path)
    print(f"Ditemukan {len(diagrams)} diagram")

    font, bold_font = load_fonts()

    exported = 0
    for diagram in diagrams:
        dname = diagram.get("name", "Untitled")
        safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', dname)
        out = os.path.join(output_folder, f"{safe}.png")
        print(f"Exporting: {dname} → {out}")
        if draw_diagram(diagram, elements_map, out, font, bold_font):
            exported += 1

    print(f"\n✅ Selesai! {exported}/{len(diagrams)} diagram berhasil di-export ke: {output_folder}")


if __name__ == "__main__":
    main()
