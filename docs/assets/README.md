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

## Demo clips

| File | From | Shows |
|---|---|---|
| `demo-workspace.gif` / `.mp4` | screen recording, 2026-09-02 | `colcon build` of a user's Franka workspace (`rcm_ws`) on macOS, then `ros2 launch … use_fake_hardware:=true` with RViz on the Mac and the arm following an RCM trajectory |
| `demo-bridge.gif` / `.mp4` | screen recording, 2026-09-02 | `nav2-diffbot` sim in the VM, Foxglove on the Mac (`ws://localhost:8765`), teleop via `ros2 topic pub /cmd_vel` from `rosmac shell` — laser scan updates live across the bridge |
| `demo-workspace-poster.png` | frame from `demo-workspace.mp4` | still fallback / social preview |

- The GIF is the README hero (renders on GitHub **and** PyPI, autoplays); the GIF
  links to the MP4 for a click-to-watch full-resolution version.
- Known cosmetic issues in the source footage (cannot re-record): the RViz title
  bar is clipped; `demo-bridge` shows a Foxglove "out of date" banner and the
  Default layout rather than `nav2.json`. Replace with a cleaner take when possible.
- The `franka_msgs` `install_name_tool: … invalidate the code signature` /
  `generating fake signature` lines in `demo-workspace` are the harmless macOS
  dylib re-sign step, not an error.

### Regenerating

The source `.mov` files are kept outside the repo (`~/Downloads/recording-1.mov`,
`recording-2.mov` at capture time — not committed). Rebuild from a fresh capture:

```bash
# hero GIF (≤5 MB target): trim, 1000 px, 12 fps, diff palette
ffmpeg -y -ss <start> -t <dur> -i recording.mov \
  -vf "fps=12,scale=1000:-1:flags=lanczos,palettegen=stats_mode=diff" pal.png
ffmpeg -y -ss <start> -t <dur> -i recording.mov -i pal.png \
  -lavfi "fps=12,scale=1000:-1:flags=lanczos [x];[x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  demo-workspace.gif
# click-to-watch MP4
ffmpeg -y -ss <start> -t <dur> -i recording.mov -vf "scale=1280:-2" \
  -c:v libx264 -crf 30 -preset veryslow -pix_fmt yuv420p -movflags +faststart -an demo-workspace.mp4
```
