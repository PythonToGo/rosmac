# Brand assets

| File | Size | Use |
|---|---|---|
| `rosmac-wordmark.jpg` | 1600×900 | README hero, docs headers, blog posts |
| `rosmac-icon.png` | 512×512, transparent | app / social icon, avatars |
| `rosmac-icon-256.png` | 256×256, transparent | smaller icon slot |
| `favicon.ico` | 16–256 multi-res | favicon for any future docs site |

## Palette (sampled from the artwork)

| Role | Approx. hex |
|---|---|
| Accent orange (`mac`) | `#F9663F` |
| Accent cyan (underline / icon dot) | `#04D1E8` |
| Icon mark (coral) | `#F5604A` |
| Wordmark background (dark slate) | `#2D3237` |
| Icon plate (light) | `#E6E6EB` |
| Accent blue (`ros`) | royal blue — take the exact value from the source file |

## Regenerating the web sizes

The masters are the full-resolution exports (2560×1440 wordmark, 1920×1920
lettermark) kept outside the repo. To rebuild the committed sizes:

```bash
magick rosmac-lettering-hero-gray.png   -resize 1600x    -strip -quality 90 rosmac-wordmark.jpg
magick rosmac-lettermark-favicon-gray.png -resize 512x512 -strip            rosmac-icon.png
magick rosmac-lettermark-favicon-gray.png -resize 256x256 -strip            rosmac-icon-256.png
```

## Usage

- Don't recolor or stretch the wordmark; keep clear space around it.
- The name is lowercase **rosmac**, one word.
