# CLI Color Scheme

This document describes the color scheme used in the CLI for optimal readability on both dark and light terminal backgrounds.

## Design Principles

1. **Dual-theme compatibility**: All colors work well on both dark and light backgrounds
2. **Accessibility**: High contrast for important information
3. **Consistency**: Same semantic meaning always uses the same color

## Color Palette

### Message Roles

| Role | Color | Reasoning |
|------|-------|-----------|
| **User** | `cyan` | Bright enough for dark backgrounds, readable on light |
| **Assistant** | `green` | Universal visibility, positive connotation |
| **System** | `bright_white` | High contrast on dark, readable on light |
| **Tool** | `yellow` | Warning-level visibility, works on both themes |

### Status Indicators

| Status | Color | Usage |
|--------|-------|-------|
| **Success** | `green` | Successful operations, OK status |
| **Error** | `red` | Errors, failures, exceptions |
| **Warning** | `yellow` | Warnings, non-critical issues |
| **Info** | `cyan` | Headers, metadata |

### Data Display

| Element | Color | Reasoning |
|---------|-------|-----------|
| **Trace ID** | `bright_blue` | Distinguishable, readable on both themes |
| **Span Count** | `bright_blue` | Numeric data, distinct from content |
| **Duration** | `green` | Performance metric, positive when low |
| **Input** | `bright_blue` | Request data |
| **Output** | `magenta` | Response data |
| **Payload** | `yellow` | Technical details |

## Problematic Colors (Avoided)

| Color | Issue | Replacement |
|-------|-------|-------------|
| `blue` | Too dark for dark backgrounds | `bright_blue` |
| `dim blue` | Nearly invisible on dark backgrounds | `bright_white` |
| `purple` | Low contrast on many terminals | `magenta` |

## Rich Terminal Color Support

The CLI uses [Rich](https://rich.readthedocs.io/) for terminal output, which supports:
- 16 basic colors
- 256 color palette
- True color (16.7 million colors)

Our color choices prioritize the 16 basic colors for maximum compatibility.

## Testing

Colors have been validated on:
- ✅ Dark terminal backgrounds (VS Code Dark, iTerm2 Dark)
- ✅ Light terminal backgrounds (VS Code Light, Terminal.app Light)
- ✅ High contrast modes

## Environment Variables

No color customization via environment variables is currently supported, but the scheme is designed to work universally without customization.
