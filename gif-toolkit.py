#!/usr/bin/env python3
"""
GIF Toolkit - FFmpeg-based GIF & Video processing tool
Usage: python gif-toolkit.py <command> [options]

Commands:
  info      - Show GIF/Video metadata
  to-mp4    - Convert GIF to MP4
  to-webp   - Convert GIF to WebP
  to-gif    - Convert video (MP4/AVI/MOV) to GIF
  speed     - Change playback speed
  compress  - Reduce file size (color reduction + lossy)
  reverse   - Reverse playback direction
  trim      - Extract a time segment
  resize    - Change dimensions (width x height)
  crop      - Crop a region (W:H:X:Y)
  text      - Add text overlay
  loop      - Change loop count
  frames    - Extract frames as PNG images
  merge     - Concatenate multiple GIFs
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

FFMPEG = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
FFPROBE = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe"
# Chinese font path on Windows
FONT = r"C:/Windows/Fonts/msyh.ttc"


def run(cmd, desc=None):
    """Run a command and return (returncode, stdout, stderr)."""
    if desc:
        print(f"[gif] {desc}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def get_media_info(path):
    """Get media metadata using ffprobe."""
    cmd = [
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(path)
    ]
    rc, out, err = run(cmd, "Reading media info")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        return None
    data = json.loads(out)
    info = {"file": str(path), "size_bytes": os.path.getsize(path)}
    fmt = data.get("format", {})
    info["duration_sec"] = float(fmt.get("duration", 0))
    info["bitrate"] = fmt.get("bit_rate", "N/A")
    for s in data.get("streams", []):
        if s["codec_type"] == "video":
            info["width"] = s.get("width")
            info["height"] = s.get("height")
            info["codec"] = s.get("codec_name")
            info["fps"] = eval(s.get("r_frame_rate", "0/1"))
            info["nb_frames"] = int(s.get("nb_frames", 0))
            break
    return info


def cmd_info(args):
    info = get_media_info(args.input)
    if not info:
        sys.exit(1)
    print(f"\n[FILE] {info['file']}")
    print(f"   Size:        {info['size_bytes'] / 1024:.1f} KB")
    print(f"   Dimensions:  {info.get('width', '?')}x{info.get('height', '?')}")
    print(f"   Duration:    {info['duration_sec']:.2f}s")
    print(f"   FPS:         {info.get('fps', '?')}")
    print(f"   Frames:      {info.get('nb_frames', '?')}")
    print(f"   Codec:       {info.get('codec', '?')}")
    print(f"   Bitrate:     {info.get('bitrate', '?')}")


def cmd_to_mp4(args):
    out = args.output or args.input.with_suffix(".mp4")
    cmd = [
        FFMPEG, "-i", str(args.input),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out)
    ]
    rc, _, err = run(cmd, "Converting GIF -> MP4")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_to_webp(args):
    out = args.output or args.input.with_suffix(".webp")
    cmd = [
        FFMPEG, "-i", str(args.input),
        "-c:v", "libwebp_anim", "-lossless", "0",
        "-compression_level", str(args.quality or 6),
        "-loop", "0",
        str(out)
    ]
    rc, _, err = run(cmd, "Converting GIF -> WebP")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_to_gif(args):
    out = args.output or args.input.with_suffix(".gif")
    # Use palette for better quality
    palette = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    palette_path = palette.name
    palette.close()

    filters = f"fps={args.fps or 10},scale={args.width or -1}:{args.height or -1}:flags=lanczos"
    # Generate palette
    cmd1 = [
        FFMPEG, "-i", str(args.input),
        "-vf", f"{filters},palettegen=stats_mode=diff",
        "-y", palette_path
    ]
    subprocess.run(cmd1, capture_output=True)

    # Apply palette
    cmd2 = [
        FFMPEG, "-i", str(args.input), "-i", palette_path,
        "-lavfi", f"{filters} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5",
        "-loop", "0",
        str(out)
    ]
    rc, _, err = run(cmd2, "Converting video -> GIF")
    os.unlink(palette_path)
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_speed(args):
    """Change playback speed. Multiplier: 2.0 = 2x faster, 0.5 = half speed."""
    out = args.output or args.input.with_stem(args.input.stem + f"_{args.multiplier}x")
    setpts = 1.0 / args.multiplier
    # For GIF, use setpts filter
    cmd = [
        FFMPEG, "-i", str(args.input),
        "-filter:v", f"setpts={setpts}*PTS",
        "-an",
        str(out)
    ]
    rc, _, err = run(cmd, f"Changing speed to {args.multiplier}x")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_compress(args):
    """Reduce GIF file size by limiting colors and using lossy compression."""
    out = args.output or args.input.with_stem(args.input.stem + "_compressed")
    colors = args.colors or 128
    # Two-pass palette approach with reduced colors
    palette = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    p_path = palette.name
    palette.close()

    cmd1 = [
        FFMPEG, "-i", str(args.input),
        "-vf", f"palettegen=max_colors={colors}:stats_mode=diff",
        "-y", p_path
    ]
    subprocess.run(cmd1, capture_output=True)

    dither = "none" if args.no_dither else "bayer:bayer_scale=5"
    cmd2 = [
        FFMPEG, "-i", str(args.input), "-i", p_path,
        "-lavfi", f"[0:v][1:v] paletteuse=dither={dither}",
        "-loop", "0",
        str(out)
    ]
    rc, _, err = run(cmd2, f"Compressing (max {colors} colors)")
    os.unlink(p_path)
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    old_size = os.path.getsize(args.input) / 1024
    new_size = os.path.getsize(out) / 1024
    saved = (1 - new_size / old_size) * 100 if old_size else 0
    print(f"  [OK] {old_size:.0f} KB -> {new_size:.0f} KB (saved {saved:.0f}%)")


def cmd_reverse(args):
    out = args.output or args.input.with_stem(args.input.stem + "_reversed")
    cmd = [
        FFMPEG, "-i", str(args.input),
        "-vf", "reverse",
        "-an",
        str(out)
    ]
    rc, _, err = run(cmd, "Reversing GIF")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_trim(args):
    """Extract a time segment: --start 0 --duration 3"""
    out = args.output or args.input.with_stem(args.input.stem + "_trimmed")
    cmd = [
        FFMPEG, "-i", str(args.input),
        "-ss", str(args.start),
        "-t", str(args.duration),
        "-c", "copy",
        str(out)
    ]
    rc, _, err = run(cmd, f"Trimming {args.start}s~{args.start+args.duration}s")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_resize(args):
    """Resize: --width 320 --height 240 (omit one to keep aspect ratio)"""
    out = args.output or args.input.with_stem(
        args.input.stem + f"_{args.width or 'auto'}x{args.height or 'auto'}"
    )
    scale = f"{args.width or -1}:{args.height or -1}"
    cmd = [
        FFMPEG, "-i", str(args.input),
        "-vf", f"scale={scale}:flags=lanczos",
        str(out)
    ]
    rc, _, err = run(cmd, f"Resizing to {args.width or 'auto'}x{args.height or 'auto'}")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_crop(args):
    """Crop: --width 300 --height 200 --x 50 --y 50"""
    out = args.output or args.input.with_stem(args.input.stem + "_cropped")
    crop = f"{args.width}:{args.height}:{args.x}:{args.y}"
    cmd = [
        FFMPEG, "-i", str(args.input),
        "-vf", f"crop={crop}",
        str(out)
    ]
    rc, _, err = run(cmd, f"Cropping {crop}")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_text(args):
    """Add text overlay to GIF using Pillow + FFmpeg overlay."""
    from PIL import Image, ImageDraw, ImageFont
    out = args.output or args.input.with_stem(args.input.stem + "_text")
    font_size = args.font_size or 24
    color = args.font_color or "white"
    x_pos = args.x
    y_pos = args.y

    # Get video dimensions
    info = get_media_info(args.input)
    if not info:
        sys.exit(1)
    w = info["width"]
    h = info["height"]

    # Create text overlay image with Pillow
    font_path = r"C:\Windows\Fonts\msyh.ttc"
    font = ImageFont.truetype(font_path, font_size)

    # Measure text size
    dummy = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), args.text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Position text
    pad = 10
    ox = (w - tw) // 2 if x_pos is None else int(x_pos)
    oy = (h - th - pad) if y_pos is None else int(y_pos)

    # Create overlay image with padding for box background
    box_pad = 5
    overlay_w = tw + box_pad * 2
    overlay_h = th + box_pad * 2
    overlay = Image.new("RGBA", (overlay_w, overlay_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Semi-transparent background
    draw.rectangle([0, 0, overlay_w, overlay_h], fill=(0, 0, 0, 100))
    # Draw text
    draw.text((box_pad, box_pad), args.text, font=font, fill=color)

    # Save overlay
    overlay_path = out.with_suffix(".png")
    overlay.save(overlay_path)

    # Use FFmpeg overlay filter
    cmd = [
        FFMPEG, "-i", str(args.input),
        "-i", str(overlay_path),
        "-filter_complex", f"overlay={ox}:{oy}",
        str(out)
    ]
    rc, _, err = run(cmd, f"Adding text: \"{args.text}\"")
    os.unlink(overlay_path)
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_loop(args):
    """Change loop count. 0 = infinite, -1 = no loop."""
    out = args.output or args.input.with_stem(args.input.stem + f"_loop{args.count}")
    if args.input.suffix.lower() in (".gif",):
        # GIF loop: add loop extension via palette workaround
        # Use a simple approach with -loop flag
        cmd = [
            FFMPEG, "-i", str(args.input),
            "-loop", str(args.count),
            str(out)
        ]
    else:
        cmd = [
            FFMPEG, "-stream_loop", str(args.count),
            "-i", str(args.input),
            "-c", "copy",
            str(out)
        ]
    rc, _, err = run(cmd, f"Setting loop count to {args.count}")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def cmd_frames(args):
    """Extract all frames as PNG images."""
    out_dir = args.output or args.input.parent / args.input.stem
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "frame_%04d.png")
    cmd = [
        FFMPEG, "-i", str(args.input),
        pattern
    ]
    rc, _, err = run(cmd, f"Extracting frames to {out_dir}/")
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    count = len(list(out_dir.glob("*.png")))
    print(f"  [OK] Extracted {count} frames to {out_dir}/")


def cmd_merge(args):
    """Merge multiple GIFs/videos into one."""
    inputs = args.inputs
    if len(inputs) < 2:
        print("  [ERR] Need at least 2 input files to merge.")
        sys.exit(1)
    out = args.output or Path("merged.gif")
    # Create concat file list
    list_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    for f in inputs:
        list_file.write(f"file '{Path(f).resolve()}'\n")
    list_file.close()
    cmd = [
        FFMPEG, "-f", "concat", "-safe", "0",
        "-i", list_file.name,
        "-c", "copy",
        str(out)
    ]
    rc, _, err = run(cmd, f"Merging {len(inputs)} files")
    os.unlink(list_file.name)
    if rc != 0:
        print(f"  Error: {err.strip()}")
        sys.exit(1)
    print(f"  [OK] Created: {out}")


def main():
    parser = argparse.ArgumentParser(
        description="GIF Toolkit - FFmpeg-based GIF & video processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gif-toolkit.py info input.gif
  python gif-toolkit.py to-mp4 input.gif
  python gif-toolkit.py speed input.gif --multiplier 2.0
  python gif-toolkit.py compress input.gif --colors 64
  python gif-toolkit.py text input.gif "Hello World" --font-size 36
  python gif-toolkit.py trim input.gif --start 1.5 --duration 3
  python gif-toolkit.py resize input.gif --width 320
  python gif-toolkit.py to-gif input.mp4 --fps 15 --width 480
  python gif-toolkit.py merge input1.gif input2.gif input3.gif
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # info
    p = subparsers.add_parser("info", help="Show media metadata")
    p.add_argument("input", type=Path, help="Input GIF/video file")

    # to-mp4
    p = subparsers.add_parser("to-mp4", help="Convert GIF to MP4")
    p.add_argument("input", type=Path, help="Input GIF file")
    p.add_argument("-o", "--output", type=Path, help="Output MP4 file")

    # to-webp
    p = subparsers.add_parser("to-webp", help="Convert GIF to WebP")
    p.add_argument("input", type=Path, help="Input GIF file")
    p.add_argument("-o", "--output", type=Path, help="Output WebP file")
    p.add_argument("-q", "--quality", type=int, default=6, choices=range(0, 7),
                   help="Compression level 0-6 (default 6, higher=better)")

    # to-gif
    p = subparsers.add_parser("to-gif", help="Convert video to GIF")
    p.add_argument("input", type=Path, help="Input video file")
    p.add_argument("-o", "--output", type=Path, help="Output GIF file")
    p.add_argument("--fps", type=int, default=10, help="Output FPS (default 10)")
    p.add_argument("--width", type=int, help="Output width (auto height)")
    p.add_argument("--height", type=int, help="Output height (auto width)")

    # speed
    p = subparsers.add_parser("speed", help="Change playback speed")
    p.add_argument("input", type=Path, help="Input file")
    p.add_argument("-m", "--multiplier", type=float, required=True,
                   help="Speed multiplier (2.0=2x, 0.5=half speed)")
    p.add_argument("-o", "--output", type=Path, help="Output file")

    # compress
    p = subparsers.add_parser("compress", help="Compress GIF (reduce file size)")
    p.add_argument("input", type=Path, help="Input GIF file")
    p.add_argument("-o", "--output", type=Path, help="Output GIF file")
    p.add_argument("-c", "--colors", type=int, default=128,
                   help="Max colors (2-256, default 128, lower=smaller)")
    p.add_argument("--no-dither", action="store_true", help="Disable dithering")

    # reverse
    p = subparsers.add_parser("reverse", help="Reverse playback")
    p.add_argument("input", type=Path, help="Input file")
    p.add_argument("-o", "--output", type=Path, help="Output file")

    # trim
    p = subparsers.add_parser("trim", help="Extract time segment")
    p.add_argument("input", type=Path, help="Input file")
    p.add_argument("-s", "--start", type=float, default=0, help="Start time in seconds")
    p.add_argument("-d", "--duration", type=float, required=True, help="Duration in seconds")
    p.add_argument("-o", "--output", type=Path, help="Output file")

    # resize
    p = subparsers.add_parser("resize", help="Resize dimensions")
    p.add_argument("input", type=Path, help="Input file")
    p.add_argument("--width", type=int, help="Target width (omit for auto)")
    p.add_argument("--height", type=int, help="Target height (omit for auto)")
    p.add_argument("-o", "--output", type=Path, help="Output file")

    # crop
    p = subparsers.add_parser("crop", help="Crop region")
    p.add_argument("input", type=Path, help="Input file")
    p.add_argument("--width", type=int, required=True, help="Crop width")
    p.add_argument("--height", type=int, required=True, help="Crop height")
    p.add_argument("--x", type=int, default=0, help="Crop X offset")
    p.add_argument("--y", type=int, default=0, help="Crop Y offset")
    p.add_argument("-o", "--output", type=Path, help="Output file")

    # text
    p = subparsers.add_parser("text", help="Add text overlay")
    p.add_argument("input", type=Path, help="Input file")
    p.add_argument("text", type=str, help="Text to add")
    p.add_argument("--font-size", type=int, default=24, help="Font size (default 24)")
    p.add_argument("--font-color", type=str, default="white", help="Font color (default white)")
    p.add_argument("--x", type=str, help="X position (default center)")
    p.add_argument("--y", type=str, help="Y position (default bottom-20)")
    p.add_argument("-o", "--output", type=Path, help="Output file")

    # loop
    p = subparsers.add_parser("loop", help="Change loop count")
    p.add_argument("input", type=Path, help="Input file")
    p.add_argument("-c", "--count", type=int, default=0, help="Loop count (0=infinite, 1=play once)")
    p.add_argument("-o", "--output", type=Path, help="Output file")

    # frames
    p = subparsers.add_parser("frames", help="Extract all frames as PNG")
    p.add_argument("input", type=Path, help="Input GIF/video file")
    p.add_argument("-o", "--output", type=Path, help="Output directory")

    # merge
    p = subparsers.add_parser("merge", help="Concatenate multiple files")
    p.add_argument("inputs", type=Path, nargs="+", help="Input files (2+)")
    p.add_argument("-o", "--output", type=Path, help="Output file")

    args = parser.parse_args()

    # Validate input exists
    if hasattr(args, "input") and args.input and not args.input.exists():
        print(f"  [ERR] Input file not found: {args.input}")
        sys.exit(1)

    # Route commands
    commands = {
        "info": cmd_info,
        "to-mp4": cmd_to_mp4,
        "to-webp": cmd_to_webp,
        "to-gif": cmd_to_gif,
        "speed": cmd_speed,
        "compress": cmd_compress,
        "reverse": cmd_reverse,
        "trim": cmd_trim,
        "resize": cmd_resize,
        "crop": cmd_crop,
        "text": cmd_text,
        "loop": cmd_loop,
        "frames": cmd_frames,
        "merge": cmd_merge,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()

