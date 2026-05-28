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


def apply_temperature_tint(arr: np.ndarray, temperature: float, tint: float) -> np.ndarray:
    result = arr.astype(float)
    result[:, :, 0] = np.clip(result[:, :, 0] + temperature * 2.0, 0, 255)  # R
    result[:, :, 2] = np.clip(result[:, :, 2] - temperature * 2.0, 0, 255)  # B
    result[:, :, 1] = np.clip(result[:, :, 1] - tint * 1.5, 0, 255)         # G
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
    # 只影響最暗的像素（lum < 0.3）
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


def process_image(img: Image.Image, params: dict) -> Image.Image:
    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.array(img)

    if params.get("exposure", 0) != 0:
        arr = apply_exposure(arr, params["exposure"])
    if params.get("contrast", 1.0) != 1.0:
        arr = apply_contrast(arr, params["contrast"])
    if params.get("saturation", 1.0) != 1.0:
        arr = apply_saturation(arr, params["saturation"])

    temp = params.get("temperature", 0)
    tint = params.get("tint", 0)
    if temp != 0 or tint != 0:
        arr = apply_temperature_tint(arr, temp, tint)

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

    if params.get("grain", 0) > 0:
        arr = apply_grain(arr, params["grain"])
    if params.get("vignette", 0) > 0:
        arr = apply_vignette(arr, params["vignette"])

    return Image.fromarray(arr)
