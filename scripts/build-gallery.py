#!/usr/bin/env python3
"""Create non-destructive, web-ready gallery copies from Avinash's photo archive."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps


ROOTS = [Path(value).expanduser() for value in sys.argv[1:]]

PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / "assets" / "gallery-edited"
THUMBS = OUTPUT / "thumbs"
FULL = OUTPUT / "full"

# The New York Instagram-edit folder contains alternate exports of IDs 220–230;
# retain the edited copies (242–252). The remaining IDs below are photographs
# Avinash explicitly removed during the August 2026 gallery review.
OMIT_AS_SIMILAR = set(range(220, 231)) | {
    28, 29, 31, 35, 38, 40, 41, 42, 44, 48, 51, 64, 77, 112, 126,
    129, 131, 137, 141, 154, 155, 169, 188, 190, 199, 202, 244, 245, 284,
    10, 144, 185,
}

# Photographs selected by Avinash for a stronger, still documentary-faithful
# finish during the August 2026 gallery review. These IDs were resolved from
# the visible gallery order before any removals were applied.
SELECTED_ENHANCEMENTS = {
    11, 14, 15, 16, 17, 18, 19, 20, 21, 30, 32, 33, 34, 36, 43, 45,
    46, 47, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63,
    66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 78, 80, 81, 82, 84,
    85, 86, 87, 88, 89, 90, 92, 95, 96, 99, 142, 148, 150, 151, 159,
    163, 164, 166, 168, 170, 182, 183, 184, 186, 187, 189, 191, 192,
    193, 195, 196, 197, 198, 204, 205, 206, 211, 213, 214, 242, 254,
    256, 257, 271, 275, 285, 286, 287, 295,
}

FORCE_ARCHITECTURE = {
    14, 16, 19, 20, 21, 22, 23, 24, 25, 26, 27, 30, 33, 36, 37, 39,
    43, 45, 46, 47, 49, 50, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
    63, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 78, 79, 80,
    81, 82, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97,
    98, 99, 100, 101, 124, 128, 130, 132, 133, 134, 135, 136, 138, 139,
    140, 142, 144, 146, 148, 149, 150, 151, 152, 164, 171, 185, 187,
    249, 252, 285, 287, 288, 292, 295,
}
FORCE_CUTIES = {193, 207, 261, 262, 263, 266, 268, 269, 270, 278}
BERLIN_WALL = set(range(102, 112)) | set(range(113, 126))
VIENNA = {23, 24, 27, 30, 34, 36, 44, 45, 46}
FEATURED_ORDER = [167, 91]
MOVE_LATE = {10}
FORCE_REBUILD = {12} | SELECTED_ENHANCEMENTS
MANUAL_EDIT_OVERRIDES = {
    11: PROJECT / "assets" / "gallery-manual-edits" / "photo-011-enhanced.png",
    32: PROJECT / "assets" / "gallery-manual-edits" / "photo-032-clean.png",
    33: PROJECT / "assets" / "gallery-manual-edits" / "photo-033-clean.png",
}


def source_group(path: Path) -> str:
    lowered = str(path).lower()
    if "postcards from new york" in lowered:
        return "new-york"
    for label in ("berkshires", "beautiful places", "cuties", "minimalist", "providence"):
        if label in lowered:
            return label.replace("beautiful places", "beautiful")
    if "anything in or beside ocean" in lowered or "anthing in or beside ocean" in lowered:
        return "ocean"
    return "tour"


def place_for(photo_id: int, source: str) -> tuple[str, str]:
    if source == "new-york" or 185 <= photo_id <= 190:
        return "new-york", "New York"
    if source == "providence":
        return "providence", "Providence"
    if source == "berkshires":
        return "berkshires", "The Berkshires"
    if source == "ocean":
        return "rhode-island", "Rhode Island coast"
    if source in {"beautiful", "cuties", "minimalist"}:
        return "nature", "Close to home"
    if photo_id in set(range(12, 15)) | set(range(19, 47)):
        return "vienna", "Vienna"
    if 47 <= photo_id <= 51:
        return "milan", "Milan"
    if 52 <= photo_id <= 89:
        return "rome", "Rome"
    if 90 <= photo_id <= 98 or 146 <= photo_id <= 152:
        return "jordan", "Jordan"
    if 99 <= photo_id <= 145:
        return "berlin", "Berlin"
    return "travel", "Elsewhere"


def subjects_for(photo_id: int, source: str) -> list[str]:
    subjects: list[str] = []
    macro_ids = set(range(156, 159)) | {83, 147, 161, 162, 169, 255} | set(range(272, 283))
    wildlife_ids = {193, 207, 214} | set(range(261, 272))
    if source == "minimalist" or photo_id in macro_ids:
        subjects.append("macro-minimal")
    if source == "cuties" or photo_id in wildlife_ids:
        subjects.append("wildlife")
    if source == "ocean" or photo_id in set(range(10, 19)) | set(range(153, 156)):
        subjects.append("coast-ocean")
    if source in {"berkshires", "beautiful"} or photo_id in set(range(16, 19)) | set(range(28, 47)) | set(range(90, 95)):
        subjects.append("landscapes")
    if source in {"new-york", "providence"} or (source == "tour" and photo_id in set(range(12, 15)) | set(range(19, 90)) | set(range(95, 153))):
        subjects.append("cities-architecture")
    if photo_id in FORCE_ARCHITECTURE and "cities-architecture" not in subjects:
        subjects.insert(0, "cities-architecture")
    if photo_id in FORCE_CUTIES and "wildlife" not in subjects:
        subjects.insert(0, "wildlife")
    return subjects or ["landscapes"]


def subject_label(subject: str) -> str:
    return {
        "macro-minimal": "Macro & minimal",
        "wildlife": "Cuties",
        "coast-ocean": "Coast & ocean",
        "landscapes": "Landscapes",
        "cities-architecture": "Cities & architecture",
    }[subject]


def corrected(image: Image.Image, photo_id: int) -> Image.Image:
    """Restrained editorial correction; never crops or alters image content."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    if photo_id == 12:
        # Straighten the Belvedere frame while keeping the edit local to the
        # generated website copy. The original archive is never touched.
        angle = 1.65
        width, height = image.size
        radians = math.radians(abs(angle))
        sine, cosine = math.sin(radians), math.cos(radians)
        cosine2 = cosine * cosine - sine * sine
        crop_width = (width * cosine - height * sine) / cosine2
        crop_height = (height * cosine - width * sine) / cosine2
        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        left = (image.width - crop_width) / 2
        top = (image.height - crop_height) / 2
        image = image.crop((left, top, left + crop_width, top + crop_height))
    if photo_id in SELECTED_ENHANCEMENTS:
        # A restrained archival finish: recover usable tonal range, add modest
        # midtone contrast and colour separation, then restore downsampled
        # detail. No generative content, object removal, or reframing.
        image = ImageOps.autocontrast(image, cutoff=0.6, preserve_tone=True)
        image = ImageEnhance.Brightness(image).enhance(1.025)
        image = ImageEnhance.Contrast(image).enhance(1.075)
        image = ImageEnhance.Color(image).enhance(1.08)
        image = ImageEnhance.Sharpness(image).enhance(1.14)
    else:
        image = ImageEnhance.Contrast(image).enhance(1.045)
        image = ImageEnhance.Color(image).enhance(1.055)
        image = ImageEnhance.Sharpness(image).enhance(1.08)
    return image


def save_variant(image: Image.Image, path: Path, max_size: int, quality: int) -> None:
    variant = image.copy()
    variant.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    variant.save(path, "WEBP", quality=quality, method=6)


def main() -> None:
    if not ROOTS:
        raise SystemExit("Usage: python scripts/build-gallery.py PHOTO_FOLDER [PHOTO_FOLDER ...]")
    THUMBS.mkdir(parents=True, exist_ok=True)
    FULL.mkdir(parents=True, exist_ok=True)
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".cr2"}
    source_files = sorted({path.resolve() for root in ROOTS for path in root.rglob("*") if path.suffix.lower() in extensions})
    records = []
    skipped_raw = 0
    for photo_id, source_path in enumerate(source_files, 1):
        if photo_id in OMIT_AS_SIMILAR:
            continue
        try:
            edit_override = MANUAL_EDIT_OVERRIDES.get(photo_id)
            image_path = edit_override if edit_override and edit_override.exists() else source_path
            with Image.open(image_path) as original:
                image = corrected(original, photo_id)
        except Exception:
            skipped_raw += 1
            continue
        source = source_group(source_path)
        subjects = subjects_for(photo_id, source)
        place, place_label = place_for(photo_id, source)
        if photo_id in BERLIN_WALL:
            place, place_label = "berlin", "Berlin Wall"
        elif photo_id in VIENNA:
            place, place_label = "vienna", "Vienna"
        filename = f"photo-{photo_id:03d}.webp"
        thumb_path = THUMBS / filename
        full_path = FULL / filename
        if not thumb_path.exists() or photo_id in FORCE_REBUILD or (edit_override and edit_override.exists()):
            save_variant(image, thumb_path, 760, 78)
        if not full_path.exists() or photo_id in FORCE_REBUILD or (edit_override and edit_override.exists()):
            save_variant(image, full_path, 2048, 84)
        if photo_id in BERLIN_WALL:
            label = "Berlin Wall · Berlin"
            alt = "Photograph from the Berlin Wall memorial by Avinash Holmes"
        elif photo_id == 44:
            label = "Schönbrunn Palace · Austria"
            alt = "Schönbrunn Palace in Vienna, Austria"
        else:
            label = f"{place_label} · {subject_label(subjects[0])}"
            alt = f"{subject_label(subjects[0])} photograph by Avinash Holmes, {place_label}"
        records.append({
            "id": photo_id,
            "thumb": f"assets/gallery-edited/thumbs/{filename}",
            "full": f"assets/gallery-edited/full/{filename}",
            "width": image.width,
            "height": image.height,
            "subjects": subjects,
            "place": place,
            "placeLabel": place_label,
            "label": label,
            "alt": alt,
        })
        if len(records) % 25 == 0:
            print(f"Prepared {len(records)} photographs", flush=True)
    featured_rank = {photo_id: rank for rank, photo_id in enumerate(FEATURED_ORDER)}
    records.sort(key=lambda record: (
        0 if record["id"] in featured_rank else 2 if record["id"] in MOVE_LATE else 1,
        featured_rank.get(record["id"], record["id"]),
    ))
    data = "window.GALLERY_PHOTOS = " + json.dumps(records, ensure_ascii=False, indent=2) + ";\n"
    (PROJECT / "assets" / "gallery-data.js").write_text(data, encoding="utf-8")
    print(f"Complete: {len(records)} photographs; {skipped_raw} unsupported/raw files skipped", flush=True)


if __name__ == "__main__":
    main()
