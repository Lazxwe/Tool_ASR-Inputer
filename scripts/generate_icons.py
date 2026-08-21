"""Script to process app_icon.jpg into transparent PNG, ICO, and ICNS formats."""
from pathlib import Path
from PIL import Image, ImageDraw


def create_transparent_squircle_icon(
    input_path: Path | str = "assets/app_icon.jpg",
    output_png: Path | str = "assets/icon.png",
    output_ico: Path | str = "assets/icon.ico",
) -> None:
    input_p = Path(input_path)
    if not input_p.is_file():
        raise FileNotFoundError(f"Source icon not found at {input_p}")

    img = Image.open(input_p).convert("RGBA")
    w, h = img.size

    # Create anti-aliased rounded rectangle mask
    # Standard macOS / iOS squircle radius is approx 22% of dimension
    radius = int(min(w, h) * 0.223)

    # 4x super-sampled mask for smooth anti-aliased edges
    scale = 4
    mask_large = Image.new("L", (w * scale, h * scale), 0)
    draw = ImageDraw.Draw(mask_large)
    draw.rounded_rectangle(
        [(0, 0), (w * scale, h * scale)],
        radius=radius * scale,
        fill=255,
    )
    mask = mask_large.resize((w, h), Image.Resampling.LANCZOS)

    # Apply alpha mask
    img.putalpha(mask)

    # Save 512x512 master transparent PNG
    out_png_path = Path(output_png)
    out_png_path.parent.mkdir(parents=True, exist_ok=True)
    img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    img_512.save(out_png_path, format="PNG")
    print(f"✓ Generated transparent master PNG: {out_png_path} (512x512)")

    # Save multi-resolution Windows ICO
    out_ico_path = Path(output_ico)
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(
        out_ico_path,
        format="ICO",
        sizes=ico_sizes,
    )
    print(f"✓ Generated multi-resolution Windows ICO: {out_ico_path} (sizes: {ico_sizes})")


if __name__ == "__main__":
    create_transparent_squircle_icon()
