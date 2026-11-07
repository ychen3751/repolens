"""Syntax-aware chunks with verbatim source text and separate symbol metadata."""
import ast


def windows(start, end, size, overlap):
    while start < end:
        stop = min(start + size, end)
        yield start, stop
        if stop == end:
            break
        start = stop - overlap


def chunks(text, size=80, overlap=15, syntax=False):
    if not 0 <= overlap < size:
        raise ValueError('Require 0 <= overlap < chunk size')
    lines = text.splitlines()
    regions = []
    mode = 'fixed'
    if syntax:
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            mode = 'syntax-fallback'
        else:
            mode = 'syntax'
            def visit(node, parents=()):
                # Keep nested functions inside their outer function to avoid duplicate chunks.
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
                    regions.append((start, node.end_lineno, '.'.join((*parents, node.name))))
                    return
                context = (*parents, node.name) if isinstance(node, ast.ClassDef) else parents
                for child in ast.iter_child_nodes(node):
                    visit(child, context)
            visit(tree)
    cursor = 0
    segments = []
    for start, end, symbol in sorted(regions):
        if start > cursor:
            segments.append((cursor, start, ''))
        segments.append((start, end, symbol))
        cursor = end
    if cursor < len(lines):
        segments.append((cursor, len(lines), ''))
    for start, end, symbol in segments:
        for a, b in windows(start, end, size, overlap):
            yield {'start_line': a + 1, 'end_line': b, 'text': '\n'.join(lines[a:b]),
                   'symbol': symbol, 'chunk_mode': mode}
