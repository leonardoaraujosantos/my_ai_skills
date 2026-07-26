# JSON Canvas (.canvas)

> Config variables used below (`$OBSIDIAN_VAULT`, `$OBSIDIAN_VAULT_NAME`, `$OBSIDIAN_ICLOUD`, `$CLI`) are defined in the obsidian skill's [SKILL.md](../SKILL.md#configuration).

Canvas files (`.canvas`) follow the [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/) and contain two top-level arrays:

```json
{
  "nodes": [],
  "edges": []
}
```

## Canvas Workflows

### Create a New Canvas

1. Create a `.canvas` file with `{"nodes": [], "edges": []}`
2. Generate unique 16-character hex IDs per node (e.g., `"6f0ad84f44ce9c17"`)
3. Add nodes with required fields: `id`, `type`, `x`, `y`, `width`, `height`
4. Add edges referencing valid node IDs via `fromNode` and `toNode`
5. Validate: parse the JSON; verify all edge references resolve

### Add a Node

1. Read and parse the `.canvas` file
2. Generate a unique ID that doesn't collide with existing nodes/edges
3. Choose `x`, `y` that avoid overlapping existing nodes (50-100px spacing)
4. Append node to `nodes`; optionally add edges

### Connect Two Nodes

1. Identify source/target node IDs
2. Generate a unique edge ID
3. Set `fromNode`, `toNode`; optionally `fromSide`/`toSide` (`top`, `right`, `bottom`, `left`)
4. Optionally set `label` for descriptive text
5. Append the edge to `edges`

## Nodes

Array order determines z-index: first = bottom layer, last = top layer.

### Generic Node Attributes

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `id` | Yes | string | Unique 16-char hex identifier |
| `type` | Yes | string | `text`, `file`, `link`, or `group` |
| `x` | Yes | integer | X position in pixels |
| `y` | Yes | integer | Y position in pixels |
| `width` | Yes | integer | Width in pixels |
| `height` | Yes | integer | Height in pixels |
| `color` | No | canvasColor | Preset `"1"`-`"6"` or hex (`"#FF0000"`) |

### Text Nodes

```json
{
  "id": "6f0ad84f44ce9c17",
  "type": "text",
  "x": 0,
  "y": 0,
  "width": 400,
  "height": 200,
  "text": "# Hello World\n\nThis is **Markdown** content."
}
```

**Newline pitfall**: Use `\n` for line breaks in JSON strings. Do NOT use `\\n` — Obsidian renders that as the literal characters `\` and `n`.

### File Nodes

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `file` | Yes | string | Path to file within the vault |
| `subpath` | No | string | Link to heading or block (starts with `#`) |

```json
{
  "id": "a1b2c3d4e5f67890",
  "type": "file",
  "x": 500,
  "y": 0,
  "width": 400,
  "height": 300,
  "file": "Attachments/diagram.png"
}
```

### Link Nodes

```json
{
  "id": "c3d4e5f678901234",
  "type": "link",
  "x": 1000,
  "y": 0,
  "width": 400,
  "height": 200,
  "url": "https://obsidian.md"
}
```

### Group Nodes

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `label` | No | string | Text label for the group |
| `background` | No | string | Path to background image |
| `backgroundStyle` | No | string | `cover`, `ratio`, or `repeat` |

```json
{
  "id": "d4e5f6789012345a",
  "type": "group",
  "x": -50,
  "y": -50,
  "width": 1000,
  "height": 600,
  "label": "Project Overview",
  "color": "4"
}
```

## Edges

| Attribute | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| `id` | Yes | string | - | Unique identifier |
| `fromNode` | Yes | string | - | Source node ID |
| `fromSide` | No | string | - | `top`, `right`, `bottom`, `left` |
| `fromEnd` | No | string | `none` | `none` or `arrow` |
| `toNode` | Yes | string | - | Target node ID |
| `toSide` | No | string | - | `top`, `right`, `bottom`, `left` |
| `toEnd` | No | string | `arrow` | `none` or `arrow` |
| `color` | No | canvasColor | - | Line color |
| `label` | No | string | - | Text label |

```json
{
  "id": "0123456789abcdef",
  "fromNode": "6f0ad84f44ce9c17",
  "fromSide": "right",
  "toNode": "a1b2c3d4e5f67890",
  "toSide": "left",
  "toEnd": "arrow",
  "label": "leads to"
}
```

## Canvas Colors

Accepts a hex string or a preset number:

| Preset | Color |
|--------|-------|
| `"1"` | Red |
| `"2"` | Orange |
| `"3"` | Yellow |
| `"4"` | Green |
| `"5"` | Cyan |
| `"6"` | Purple |

## Canvas Layout Guidelines

- Coordinates can be negative (canvas extends infinitely)
- `x` increases right, `y` increases down; position is the top-left corner
- Space nodes 50-100px apart; leave 20-50px padding inside groups
- Align to grid (multiples of 10 or 20) for cleaner layouts

| Node Type | Suggested Width | Suggested Height |
|-----------|-----------------|------------------|
| Small text | 200-300 | 80-150 |
| Medium text | 300-450 | 150-300 |
| Large text | 400-600 | 300-500 |
| File preview | 300-500 | 200-400 |
| Link preview | 250-400 | 100-200 |

## Canvas Validation Checklist

1. All `id` values unique across both nodes and edges
2. Every `fromNode` and `toNode` references an existing node ID
3. Required fields present per node type (`text`, `file`, `url`)
4. `type` is `text`, `file`, `link`, or `group`
5. `fromSide`/`toSide` values are `top`, `right`, `bottom`, `left`
6. `fromEnd`/`toEnd` values are `none` or `arrow`
7. Color presets are `"1"`-`"6"` or valid hex
8. JSON parses cleanly

### ID Generation

Generate 16-character lowercase hexadecimal strings (64-bit random value):

```bash
# In shell
openssl rand -hex 8

# Or in JS via obsidian eval
obsidian eval code="crypto.randomUUID().replace(/-/g, '').slice(0, 16)"
```

---
