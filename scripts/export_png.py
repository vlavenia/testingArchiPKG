#!/usr/bin/env python3
"""
Export ArchiMate diagrams dari format Grafico (coArchi v1) ke PNG
Membaca nama elemen dari href referensi ke file XML terpisah
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

# ─── Warna per tipe ArchiMate ─────────────────────────────────────────────────
ELEMENT_COLORS = {
    # Business layer - kuning
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
    # Strategy layer - oranye
    "ValueStream":           ("#FFE0B0", "#8B5000"),
    "Capability":            ("#FFE0B0", "#8B5000"),
    "Resource":              ("#FFE0B0", "#8B5000"),
    "CourseOfAction":        ("#FFE0B0", "#8B5000"),
    # Application layer - biru
    "ApplicationComponent":  ("#C0E0FF", "#00008B"),
    "ApplicationService":    ("#C0E0FF", "#00008B"),
    "ApplicationFunction":   ("#C0E0FF", "#00008B"),
    "ApplicationProcess":    ("#C0E0FF", "#00008B"),
    "DataObject":            ("#C0E0FF", "#00008B"),
    # Technology layer - hijau
    "Node":                  ("#C0FFC0", "#006400"),
    "Device":                ("#C0FFC0", "#006400"),
    "SystemSoftware":        ("#C0FFC0", "#006400"),
    "TechnologyService":     ("#C0FFC0", "#006400"),
    "Artifact":              ("#C0FFC0", "#006400"),
    # Motivation - gold
    "Stakeholder":           ("#FFD700", "#8B6914"),
    "Goal":                  ("#FFD700", "#8B6914"),
    "Requirement":           ("#FFD700", "#8B6914"),
    # Implementation - pink
    "WorkPackage":           ("#FFB6C1", "#8B0000"),
    "Deliverable":           ("#FFB6C1", "#8B0000"),
    # Grouping - abu
    "Grouping":              ("#F0F0F0", "#888888"),
    "DiagramModelGroup":     ("#F0F4F0", "#888888"),
}
DEFAULT_COLOR = ("#F5F5F5", "#666666")

# Warna koneksi per tipe relasi
RELATION_COLORS = {
    "TriggeringRelationship":    "#000000",
    "RealizationRelationship":   "#0000CC",
    "AssignmentRelationship":    "#CC6600",
    "CompositionRelationship":   "#009900",
    "AggregationRelationship":   "#009999",
    "AssociationRelationship":   "#555555",
    "FlowRelationship":          "#CC0000",
    "InfluenceRelationship":     "#666666",
    "AccessRelationship":        "#9900CC",
    "ServingRelationship":       "#0099CC",
    "SpecializationRelationship":"#CC0099",
}

SCALE = 1.5
PADDING = 60
MIN_W = 1400
MIN_H = 900
FONT_SIZE = 12
TITLE_FONT_SIZE = 18


def strip_ns(tag):
    return re.sub(r'\{.*?\}', '', tag)


def get_type_from_xsi(xsi_type):
    """Ambil nama tipe bersih dari xsi:type seperti 'archimate:ValueStream'"""
    return xsi_type.split(":")[-1] if ":" in xsi_type else xsi_type


def get_colors(etype):
    etype_clean = get_type_from_xsi(str(etype))
    for key, val in ELEMENT_COLORS.items():
        if key.lower() == etype_clean.lower():
            return val
    for key, val in ELEMENT_COLORS.items():
        if key.lower() in etype_clean.lower():
            return val
    return DEFAULT_COLOR


def get_relation_color(rel_type):
    rel_clean = get_type_from_xsi(str(rel_type))
    for key, val in RELATION_COLORS.items():
        if key.lower() in rel_clean.lower():
            return val
    return "#555555"


def load_fonts():
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
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


def parse_grafico(model_folder):
    """
    Baca format Grafico coArchi v1.
    Setiap elemen ArchiMate ada di file terpisah misal:
      business/ValueStream_id-xxx.xml
      business/BusinessProcess_id-xxx.xml
    Referensi di diagram: href="ValueStream_id-xxx.xml#id-xxx"
    """
    elements_map = {}  # id -> {name, type}

    element_folders = [
        "business", "application", "technology", "motivation",
        "strategy", "implementation_migration", "other", "relations"
    ]

    for subdir in element_folders:
        folder = os.path.join(model_folder, subdir)
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            if not fname.endswith(".xml"):
                continue
            fpath = os.path.join(folder, fname)
            try:
                root = ET.parse(fpath).getroot()
                eid = root.get("id")
                ename = root.get("name", "")
                etype = strip_ns(root.tag)
                if eid:
                    elements_map[eid] = {
                        "id": eid,
                        "name": ename,
                        "type": etype,
                        "file": fname,
                    }
            except Exception as e:
                print(f"  [warn] {fname}: {e}")

    print(f"  Total elemen: {len(elements_map)}")

    # Baca diagram
    diagrams = []
    diagrams_folder = os.path.join(model_folder, "diagrams")
    if not os.path.isdir(diagrams_folder):
        print(f"  [warn] Folder diagrams/ tidak ada")
        return diagrams, elements_map

    for fname in sorted(os.listdir(diagrams_folder)):
        if not fname.endswith(".xml"):
            continue
        fpath = os.path.join(diagrams_folder, fname)
        try:
            root = ET.parse(fpath).getroot()
            dname = root.get("name", fname)
            print(f"  Found diagram: '{dname}'")
            diagrams.append(root)
        except Exception as e:
            print(f"  [warn] {fname}: {e}")

    return diagrams, elements_map


def resolve_element(child, elements_map):
    """
    Ambil nama dan tipe elemen dari node diagram.
    Referensi lewat <archimateElement xsi:type="..." href="File.xml#id"/>
    """
    xsi_type = child.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
    elem_type = get_type_from_xsi(xsi_type)  # e.g. DiagramModelArchimateObject
    elem_name = child.get("name", "")
    arch_type = ""

    # Cari child <archimateElement> yang berisi href ke elemen asli
    for sub in child:
        stag = strip_ns(sub.tag)
        if stag == "archimateElement":
            # Ambil tipe dari xsi:type
            sub_xsi = sub.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
            arch_type = get_type_from_xsi(sub_xsi)

            # Ambil id dari href="FileName.xml#id-xxx"
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

    final_type = arch_type if arch_type else elem_type
    return elem_name, final_type


def resolve_relation_type(conn):
    """Ambil tipe relasi dari sourceConnection"""
    for sub in conn:
        stag = strip_ns(sub.tag)
        if stag == "archimateRelationship":
            xsi = sub.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
            return get_type_from_xsi(xsi)
    xsi = conn.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
    return get_type_from_xsi(xsi)


def collect_nodes_and_connections(elem, elements_map, offset_x=0, offset_y=0):
    """Rekursif kumpulkan nodes dan koneksi dari diagram"""
    nodes = []
    connections = []

    for child in elem:
        tag = strip_ns(child.tag)

        if tag == "sourceConnections":
            src_id = child.get("source", "")
            tgt_id = child.get("target", "")
            rel_type = resolve_relation_type(child)
            conn_id = child.get("id", "")
            if src_id and tgt_id:
                connections.append({
                    "id": conn_id,
                    "source": src_id,
                    "target": tgt_id,
                    "type": rel_type,
                })

        elif tag == "children":
            xsi_type = child.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
            node_id = child.get("id", "")

            # Cari bounds
            bounds = None
            for sub in child:
                if strip_ns(sub.tag) == "bounds":
                    bounds = sub
                    break

            if bounds is not None:
                x = int(float(bounds.get("x", 0))) + offset_x
                y = int(float(bounds.get("y", 0))) + offset_y
                w = int(float(bounds.get("width", 120)))
                h = int(float(bounds.get("height", 55)))

                elem_name, elem_type = resolve_element(child, elements_map)

                nodes.append({
                    "id": node_id,
                    "x": x, "y": y, "w": w, "h": h,
                    "label": elem_name,
                    "type": elem_type,
                    "xsi_type": xsi_type,
                })

                # Kumpulkan sourceConnections dari child ini
                for sub in child:
                    stag = strip_ns(sub.tag)
                    if stag == "sourceConnections":
                        src_id = sub.get("source", node_id)
                        tgt_id = sub.get("target", "")
                        rel_type = resolve_relation_type(sub)
                        conn_id = sub.get("id", "")
                        if tgt_id:
                            connections.append({
                                "id": conn_id,
                                "source": src_id if src_id else node_id,
                                "target": tgt_id,
                                "type": rel_type,
                            })

                # Rekursif untuk nested children
                child_nodes, child_conns = collect_nodes_and_connections(
                    child, elements_map, x, y
                )
                nodes.extend(child_nodes)
                connections.extend(child_conns)

    return nodes, connections


def draw_diagram(diagram, elements_map, output_path, font, bold_font):
    name = diagram.get("name", "Untitled")

    nodes, connections = collect_nodes_and_connections(diagram, elements_map)

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

    # Build id → node map
    id_map = {n["id"]: n for n in nodes if n.get("id")}

    # Gambar koneksi (dulu sebelum node supaya node di atas)
    seen_conns = set()
    for conn in connections:
        ckey = (conn["source"], conn["target"])
        if ckey in seen_conns:
            continue
        seen_conns.add(ckey)

        src = id_map.get(conn["source"])
        tgt = id_map.get(conn["target"])
        if not src or not tgt:
            continue

        sx = int((src["x"] + src["w"] / 2 + ox) * SCALE) + PADDING
        sy = int((src["y"] + src["h"] / 2 + oy) * SCALE) + PADDING + 60
        tx = int((tgt["x"] + tgt["w"] / 2 + ox) * SCALE) + PADDING
        ty = int((tgt["y"] + tgt["h"] / 2 + oy) * SCALE) + PADDING + 60

        color = get_relation_color(conn["type"])
        draw.line([(sx, sy), (tx, ty)], fill=color, width=2)

        # Arrow head
        dx, dy = tx - sx, ty - sy
        length = max((dx**2 + dy**2) ** 0.5, 1)
        al = 12
        ax2 = tx - al * dx / length
        ay2 = ty - al * dy / length
        px = -dy / length * 6
        py = dx / length * 6
        draw.polygon(
            [(tx, ty), (int(ax2 + px), int(ay2 + py)), (int(ax2 - px), int(ay2 - py))],
            fill=color
        )

    # Gambar node — yang lebih besar dulu (background group)
    sorted_nodes = sorted(nodes, key=lambda n: n["w"] * n["h"], reverse=True)

    for n in sorted_nodes:
        x1 = int((n["x"] + ox) * SCALE) + PADDING
        y1 = int((n["y"] + oy) * SCALE) + PADDING + 60
        x2 = x1 + int(n["w"] * SCALE)
        y2 = y1 + int(n["h"] * SCALE)

        fill, border = get_colors(n["type"])

        # Group/container punya sudut berbeda
        xsi = n.get("xsi_type", "")
        is_group = "Group" in xsi or "Grouping" in n["type"]
        if is_group:
            # Border tebal untuk group
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline=border, width=3)
            draw.rectangle([x1, y1, x2, y1 + 20], fill=border)
        else:
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline=border, width=2)

        # Label
        label = n["label"] or n["type"] or "?"
        max_chars = max(8, int(n["w"] * SCALE / 8))
        lines = wrap_text(label, max_chars=max_chars)
        line_h = FONT_SIZE + 4
        total_h = len(lines) * line_h
        ty_start = y1 + max(6, (y2 - y1 - total_h) // 2)

        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(line) * 7
            tx_start = x1 + max(4, (x2 - x1 - tw) // 2)
            draw.text((tx_start, ty_start), line, fill="#1a1a1a", font=font)
            ty_start += line_h

    img.save(output_path, "PNG", dpi=(150, 150))
    print(f"  ✅ {output_path} ({len(nodes)} nodes, {len(connections)} koneksi)")
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
