#!/usr/bin/env python3
"""Render a GraphViz DOT attack graph into a lightweight SVG visualization.

The script only relies on Python's standard library so it works in
restricted environments where GraphViz and other visualization
libraries are unavailable.
"""
import argparse
import html
import math
import re
from typing import Dict, List, Sequence, Tuple

NODE_PATTERN = re.compile(r'^\s*("[^"]*"|[^\s\[]+)\s+\[type=node\];')
EDGE_PATTERN = re.compile(
    r'^\s*("[^"]*"|[^\s\[]+)\s+->\s+("[^"]*"|[^\s\[]+)\s+'
    r'\[key=\d+, label=([^\]]+)\];'
)

EDGE_COLORS = {
    'read': '#1f77b4',
    'write': '#d62728',
    'delete': '#9467bd',
    'resolve': '#ff7f0e',
    'web_request': '#2ca02c',
    'web_response': '#17becf',
    'refer': '#bcbd22',
}


def _clean_name(raw: str) -> str:
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return raw


def parse_dot(path: str) -> Tuple[List[str], List[Tuple[str, str, str]]]:
    nodes: List[str] = []
    node_set = set()
    edges: List[Tuple[str, str, str]] = []
    with open(path, 'r', encoding='utf-8') as dot_file:
        for line in dot_file:
            node_match = NODE_PATTERN.match(line)
            if node_match:
                node_name = _clean_name(node_match.group(1))
                if node_name not in node_set:
                    node_set.add(node_name)
                    nodes.append(node_name)
                continue
            edge_match = EDGE_PATTERN.match(line)
            if edge_match:
                src = _clean_name(edge_match.group(1))
                dst = _clean_name(edge_match.group(2))
                label = edge_match.group(3).strip()
                edges.append((src, dst, label))
    nodes.sort()
    return nodes, edges


def compute_layout(nodes: Sequence[str], radius: float = 420.0,
                   width: int = 1100, height: int = 1100) -> Dict[str, Tuple[float, float]]:
    positions: Dict[str, Tuple[float, float]] = {}
    count = len(nodes)
    if count == 0:
        return positions
    angle_step = (2 * math.pi) / count
    for index, node in enumerate(nodes):
        angle = index * angle_step
        x = width / 2 + radius * math.cos(angle)
        y = height / 2 + radius * math.sin(angle)
        positions[node] = (x, y)
    return positions


def _arrow_points(start: Tuple[float, float], end: Tuple[float, float],
                  radius: float, arrow_size: float = 10.0) -> Tuple[Tuple[float, float],
                                                                     Tuple[float, float],
                                                                     Tuple[float, float],
                                                                     Tuple[float, float]]:
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    dist = math.hypot(dx, dy)
    if dist == 0:
        return (sx, sy), (ex, ey), (ex, ey), (ex, ey)
    ux, uy = dx / dist, dy / dist
    line_start = (sx + ux * radius, sy + uy * radius)
    line_end = (ex - ux * radius, ey - uy * radius)
    ax = line_end[0]
    ay = line_end[1]
    left = (ax - ux * arrow_size - uy * (arrow_size / 2),
            ay - uy * arrow_size + ux * (arrow_size / 2))
    right = (ax - ux * arrow_size + uy * (arrow_size / 2),
             ay - uy * arrow_size - ux * (arrow_size / 2))
    return line_start, line_end, left, right


def render_svg(output_path: str, nodes: Sequence[str],
               edges: Sequence[Tuple[str, str, str]]) -> None:
    width, height = 1100, 1100
    node_radius = 26
    positions = compute_layout(nodes, radius=420, width=width, height=height)

    svg_lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"',
        '     viewBox="0 0 {0} {1}">'.format(width, height),
        '  <style>',
        '    text { font-family: Arial, sans-serif; font-size: 11px; fill: #111; }',
        '  </style>'
    ]

    for src, dst, label in edges:
        if src not in positions or dst not in positions:
            continue
        color = EDGE_COLORS.get(label, '#7f7f7f')
        start, end, left, right = _arrow_points(positions[src], positions[dst],
                                                node_radius)
        svg_lines.append(
            '  <line x1="{:.2f}" y1="{:.2f}" x2="{:.2f}" y2="{:.2f}" '
            'stroke="{}" stroke-width="1.6" opacity="0.85" />'
            .format(start[0], start[1], end[0], end[1], color)
        )
        svg_lines.append(
            '  <polygon points="{:.2f},{:.2f} {:.2f},{:.2f} {:.2f},{:.2f}" '
            'fill="{}" opacity="0.85" />'
            .format(end[0], end[1], left[0], left[1], right[0], right[1], color)
        )
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        svg_lines.append(
            '  <text x="{:.2f}" y="{:.2f}" fill="{}" opacity="0.8">{}</text>'
            .format(mid_x, mid_y, color, html.escape(label))
        )

    for node, (x, y) in positions.items():
        svg_lines.append(
            '  <circle cx="{:.2f}" cy="{:.2f}" r="{}" fill="#fefefe" '
            'stroke="#444" stroke-width="1.5" />'.format(x, y, node_radius)
        )
        label = node
        if len(label) > 28:
            label = label[:25] + '…'
        svg_lines.append(
            '  <text x="{:.2f}" y="{:.2f}" text-anchor="middle">{}</text>'
            .format(x, y + 4, html.escape(label))
        )

    svg_lines.append('</svg>')
    with open(output_path, 'w', encoding='utf-8') as svg_file:
        svg_file.write('\n'.join(svg_lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Render DOT attack graph to SVG')
    parser.add_argument('dot_path', help='Path to GraphViz DOT file')
    parser.add_argument('-o', '--output', default='attack_graph.svg',
                        help='Output SVG path (default: attack_graph.svg)')
    args = parser.parse_args()
    nodes, edges = parse_dot(args.dot_path)
    if not nodes:
        raise SystemExit('No nodes were found in the DOT file.')
    render_svg(args.output, nodes, edges)


if __name__ == '__main__':
    main()
