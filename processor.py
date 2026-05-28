import math

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def apply_exposure(arr: np.ndarray, exposure: float) -> np.ndarray:
    result = arr.astype(float) * (2 ** exposure)
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_contrast(arr: np.ndarray, contrast: float) -> np.ndarray:
    result = (arr.astype(float) - 128) * contrast + 128
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_saturation(arr: np.ndarray, saturation: float) -> np.ndarray:
    img = Image.fromarray(arr)
    result = ImageEnhance.Color(img).enhance(saturation)
    return np.array(result)


def apply_vibrance(arr: np.ndarray, vibrance: float) -> np.ndarray:
    """Boost less-saturated pixels more than already-saturated ones."""
    if vibrance == 0:
        return arr
    img = Image.fromarray(arr).convert("HSV")
    hsv = np.array(img).astype(float)
    s = hsv[:, :, 1] / 255.0
    strength = vibrance / 100.0 * (1.0 - s)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] + strength * 255, 0, 255)
    return np.array(Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB"))


def apply_temperature_tint(arr: np.ndarray, temperature: float, tint: float) -> np.ndarray:
    result = arr.astype(float)
    result[:, :, 0] = np.clip(result[:, :, 0] + temperature * 2.0, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] - temperature * 2.0, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] - tint * 1.5, 0, 255)
    return result.astype(np.uint8)


def apply_highlights_shadows(arr: np.ndarray, highlights: float, shadows: float) -> np.ndarray:
    lum = np.mean(arr, axis=2, keepdims=True) / 255.0
    h_mask = lum ** 2
    s_mask = (1 - lum) ** 2
    result = arr.astype(float)
    result += h_mask * highlights * 1.2
    result += s_mask * shadows * 1.2
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_blacks(arr: np.ndarray, blacks: float) -> np.ndarray:
    lum = np.mean(arr, axis=2, keepdims=True) / 255.0
    mask = np.clip((0.3 - lum) / 0.3, 0, 1) ** 2
    result = arr.astype(float) + mask * blacks * 0.8
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_fade(arr: np.ndarray, fade: float) -> np.ndarray:
    lift = fade * 50
    result = arr.astype(float)
    result = result + lift * (1 - result / 255)
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_clarity(arr: np.ndarray, clarity: float) -> np.ndarray:
    img = Image.fromarray(arr)
    if clarity > 0:
        blurred = np.array(img.filter(ImageFilter.GaussianBlur(radius=20))).astype(float)
        result = arr.astype(float) + (clarity / 10) * 0.8 * (arr.astype(float) - blurred)
    else:
        radius = abs(clarity) / 10 * 2
        result = np.array(img.filter(ImageFilter.GaussianBlur(radius=radius))).astype(float)
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_soft_s_curve(arr: np.ndarray) -> np.ndarray:
    lut = np.arange(256, dtype=float)
    # Gentle S: lift shadows slightly, pull highlights slightly
    lut = lut + 12 * np.sin(np.pi * lut / 255) * (1 - lut / 255) - 8 * (lut / 255) ** 2 * np.sin(np.pi * lut / 255)
    lut = np.clip(lut, 0, 255).astype(np.uint8)
    result = lut[arr]
    return result


def apply_split_tone(arr: np.ndarray, shadow_color: list, highlight_color: list, intensity: float = 0.25) -> np.ndarray:
    lum = np.mean(arr, axis=2, keepdims=True) / 255.0
    s_mask = (1 - lum) ** 2
    h_mask = lum ** 2
    sc = np.array(shadow_color, dtype=float)
    hc = np.array(highlight_color, dtype=float)
    result = arr.astype(float)
    for c in range(3):
        result[:, :, c] += s_mask[:, :, 0] * (sc[c] - arr[:, :, c]) * intensity
        result[:, :, c] += h_mask[:, :, 0] * (hc[c] - arr[:, :, c]) * intensity
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_grain(arr: np.ndarray, grain: float) -> np.ndarray:
    noise = np.random.normal(0, grain * 40, arr.shape)
    return np.clip(arr.astype(float) + noise, 0, 255).astype(np.uint8)


def apply_vignette(arr: np.ndarray, vignette: float) -> np.ndarray:
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
    dist = dist / dist.max()
    mask = (1 - vignette * dist ** 1.5).clip(0, 1)[:, :, np.newaxis]
    return np.clip(arr.astype(float) * mask, 0, 255).astype(np.uint8)


def apply_hsl_adjustments(arr: np.ndarray, hsl: dict) -> np.ndarray:
    """Shift hue and saturation for specific color channels via HSV approximation."""
    if not hsl:
        return arr
    img = Image.fromarray(arr).convert("HSV")
    hsv = np.array(img).astype(float)
    h = hsv[:, :, 0]  # 0-255 maps to 0-360 degrees

    def hue_mask(center_deg: float, width_deg: float = 30) -> np.ndarray:
        center = center_deg / 360 * 255
        width = width_deg / 360 * 255
        diff = np.abs(h - center)
        diff = np.minimum(diff, 255 - diff)
        return np.clip(1 - diff / width, 0, 1)

    # Yellow ~60°, Green ~120°, Blue ~240°
    for key, value in hsl.items():
        if key == "yellow_hue":
            mask = hue_mask(60)
            hsv[:, :, 0] = np.clip(hsv[:, :, 0] + mask * (value / 360 * 255), 0, 255)
        elif key == "green_hue":
            mask = hue_mask(120)
            hsv[:, :, 0] = np.clip(hsv[:, :, 0] + mask * (value / 360 * 255), 0, 255)
        elif key == "yellow_sat":
            mask = hue_mask(60)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] + mask * value * 2.55, 0, 255)
        elif key == "green_sat":
            mask = hue_mask(120)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] + mask * value * 2.55, 0, 255)
        elif key == "blue_sat":
            mask = hue_mask(240)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] + mask * value * 2.55, 0, 255)

    result = Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")
    return np.array(result)


# --- Local adjustments ---

def apply_subject_lift(arr: np.ndarray, strength: float = 20) -> np.ndarray:
    """Brighten the central region (approximates subject lift without segmentation)."""
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
    mask = np.clip(1 - dist, 0, 1) ** 1.5
    result = arr.astype(float) + mask[:, :, np.newaxis] * strength
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_edge_lift(arr: np.ndarray, strength: float = 15) -> np.ndarray:
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
    mask = np.clip(dist - 0.5, 0, 1)
    result = arr.astype(float) + mask[:, :, np.newaxis] * strength
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_edge_darken(arr: np.ndarray, strength: float = 0.15) -> np.ndarray:
    return apply_vignette(arr, strength)


# --- Crop / straighten ---

ASPECT_RATIOS = {
    "1:1": (1, 1),
    "4:5": (4, 5),
    "3:4": (3, 4),
    "16:9": (16, 9),
}


def crop_to_ratio(img: Image.Image, ratio: str) -> Image.Image:
    if ratio not in ASPECT_RATIOS:
        return img
    w, h = img.size
    rw, rh = ASPECT_RATIOS[ratio]
    target_w = min(w, int(h * rw / rh))
    target_h = min(h, int(w * rh / rw))
    left = (w - target_w) // 2
    top = (h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def apply_manual_crop(img: Image.Image, x: int, y: int, width: int, height: int) -> Image.Image:
    iw, ih = img.size
    x = max(0, min(x, iw))
    y = max(0, min(y, ih))
    width = max(1, min(width, iw - x))
    height = max(1, min(height, ih - y))
    return img.crop((x, y, x + width, y + height))


def apply_straighten(img: Image.Image, angle: float) -> Image.Image:
    if angle == 0:
        return img
    rotated = img.rotate(-angle, expand=True, resample=Image.BICUBIC)
    # Crop back to original aspect ratio after rotation
    rad = math.radians(abs(angle))
    ow, oh = img.size
    rw, rh = rotated.size
    scale = 1 / (math.cos(rad) + math.sin(rad) * oh / ow)
    nw = int(ow * scale)
    nh = int(oh * scale)
    left = (rw - nw) // 2
    top = (rh - nh) // 2
    return rotated.crop((left, top, left + nw, top + nh))


def suggest_crop(img: Image.Image, ratio: str = "1:1") -> dict:
    """Rule-based crop suggestion. Returns crop rect as fractions of original size."""
    w, h = img.size
    if ratio not in ASPECT_RATIOS:
        ratio = "1:1"
    rw, rh = ASPECT_RATIOS[ratio]
    target_w = min(w, int(h * rw / rh))
    target_h = min(h, int(w * rh / rw))
    x = (w - target_w) // 2
    y = (h - target_h) // 2
    return {
        "x": x, "y": y,
        "width": target_w, "height": target_h,
        "aspect_ratio": ratio,
        "rationale": ["center_composition", f"target_{ratio}"],
    }


# --- Main pipeline ---

def process_image(img: Image.Image, params: dict) -> Image.Image:
    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.array(img)

    if params.get("exposure", 0) != 0:
        arr = apply_exposure(arr, params["exposure"])
    if params.get("contrast", 1.0) != 1.0:
        arr = apply_contrast(arr, params["contrast"])

    if params.get("curve") == "soft_s":
        arr = apply_soft_s_curve(arr)

    if params.get("saturation", 1.0) != 1.0:
        arr = apply_saturation(arr, params["saturation"])
    vibrance = params.get("vibrance", 0)
    if vibrance != 0:
        arr = apply_vibrance(arr, vibrance)

    temp = params.get("temperature", 0)
    tint = params.get("tint", 0)
    if temp != 0 or tint != 0:
        arr = apply_temperature_tint(arr, temp, tint)

    hsl = params.get("hsl")
    if hsl:
        arr = apply_hsl_adjustments(arr, hsl)

    hl = params.get("highlights", 0)
    sh = params.get("shadows", 0)
    if hl != 0 or sh != 0:
        arr = apply_highlights_shadows(arr, hl, sh)

    if params.get("blacks", 0) != 0:
        arr = apply_blacks(arr, params["blacks"])
    if params.get("fade", 0) > 0:
        arr = apply_fade(arr, params["fade"])
    if params.get("clarity", 0) != 0:
        arr = apply_clarity(arr, params["clarity"])

    st = params.get("split_tone")
    if st:
        arr = apply_split_tone(arr, st["shadows"], st["highlights"])

    # Local adjustments
    for adj in params.get("local_adjustments", []):
        if adj == "subject_lift":
            arr = apply_subject_lift(arr)
        elif adj == "edge_lift":
            arr = apply_edge_lift(arr)
        elif adj == "edge_darken":
            arr = apply_edge_darken(arr)

    if params.get("grain", 0) > 0:
        arr = apply_grain(arr, params["grain"])
    if params.get("vignette", 0) > 0:
        arr = apply_vignette(arr, params["vignette"])

    return Image.fromarray(arr)
