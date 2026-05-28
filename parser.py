"""Natural language prompt parser for color grading and composition hints."""

from dataclasses import dataclass, field

WARM_KEYWORDS = {"微暖", "偏暖", "暖一點", "暖調", "warm", "warmer"}
COOL_KEYWORDS = {"偏冷", "冷一點", "冷調", "冷色", "cool", "cooler"}
GREEN_KEYWORDS = {"偏綠", "綠一點", "偏青綠", "green tint"}
YELLOW_KEYWORDS = {"偏黃", "黃調", "yellow"}
ORANGE_KEYWORDS = {"偏橘", "橘調", "orange"}
CLEAN_KEYWORDS = {"顏色乾淨", "不要太亂", "不要太鮮豔", "乾淨", "clean", "desaturate"}
VIBRANT_KEYWORDS = {"鮮豔", "飽和", "vivid", "vibrant"}
SOFT_KEYWORDS = {"柔和", "清淡", "輕盈", "soft", "airy", "gentle"}
MOODY_KEYWORDS = {"戲劇", "暗調", "heavy", "moody", "dramatic"}
VINTAGE_KEYWORDS = {"復古", "老味道", "底片", "film", "vintage", "老照片"}
JAPANESE_KEYWORDS = {"日系", "日式", "japanese", "japan", "日系街拍", "街拍"}
CINEMATIC_KEYWORDS = {"電影感", "cinematic", "film look"}
LAYER_KEYWORDS = {"S 曲線", "s curve", "立體感", "層次", "對比層次"}
SUBJECT_LIFT_KEYWORDS = {"主體提亮", "人物提亮", "subject lift", "主體亮"}
EDGE_LIFT_KEYWORDS = {"邊緣提亮", "邊角提亮", "edge lift"}
EDGE_DARK_KEYWORDS = {"邊緣壓暗", "暗角", "vignette", "邊角壓暗"}
BG_SUPPRESS_KEYWORDS = {"背景不要搶戲", "背景壓暗", "background dark"}
CROP_SQUARE_KEYWORDS = {"方形", "正方形", "1:1", "ig square", "ig 方形"}
CROP_PORTRAIT_KEYWORDS = {"人像比例", "4:5", "portrait", "直幅"}
CROP_WIDE_KEYWORDS = {"16:9", "寬螢幕", "wide"}
CENTER_COMP_KEYWORDS = {"中央構圖", "置中", "center", "centered"}
THIRDS_COMP_KEYWORDS = {"三分法", "rule of thirds", "三分線"}

# Food-specific theme keywords → maps to food preset names
FOOD_THEME_KEYWORDS: dict[str, str] = {
    "早餐": "Food: Bright & Airy",
    "breakfast": "Food: Bright & Airy",
    "明亮食物": "Food: Bright & Airy",
    "bright food": "Food: Bright & Airy",
    "咖啡廳": "Food: Warm Cafe",
    "咖啡": "Food: Warm Cafe",
    "cafe": "Food: Warm Cafe",
    "coffee": "Food: Warm Cafe",
    "甜點": "Food: Warm Cafe",
    "pastry": "Food: Warm Cafe",
    "麵包": "Food: Vintage Film",
    "bread": "Food: Vintage Film",
    "手作": "Food: Vintage Film",
    "artisan": "Food: Vintage Film",
    "烘焙": "Food: Vintage Film",
    "bakery": "Food: Vintage Film",
    "巧克力": "Food: Moody Dark",
    "chocolate": "Food: Moody Dark",
    "紅酒": "Food: Moody Dark",
    "wine": "Food: Moody Dark",
    "暗調食物": "Food: Moody Dark",
    "沙拉": "Food: Clean & Fresh",
    "salad": "Food: Clean & Fresh",
    "健康": "Food: Clean & Fresh",
    "healthy": "Food: Clean & Fresh",
    "蔬菜": "Food: Clean & Fresh",
    "vegetables": "Food: Clean & Fresh",
    "清爽": "Food: Clean & Fresh",
    "米其林": "Food: Fine Dining",
    "餐廳": "Food: Fine Dining",
    "restaurant": "Food: Fine Dining",
    "fine dining": "Food: Fine Dining",
    "擺盤": "Food: Fine Dining",
}


@dataclass
class ParseResult:
    style_tags: list[str] = field(default_factory=list)
    param_delta: dict = field(default_factory=dict)
    crop_suggestion_hint: str | None = None
    local_adjustment_hint: list[str] = field(default_factory=list)
    suggested_preset: str | None = None  # direct preset name from theme keyword


def parse_prompt(text: str) -> ParseResult:
    t = text.lower()
    result = ParseResult()

    def hit(keywords: set) -> bool:
        return any(k in t for k in keywords)

    # Style tags
    if hit(JAPANESE_KEYWORDS):
        result.style_tags.append("japanese")
    if hit(CINEMATIC_KEYWORDS):
        result.style_tags.append("cinematic")
    if hit(VINTAGE_KEYWORDS):
        result.style_tags.append("vintage")
    if hit(MOODY_KEYWORDS):
        result.style_tags.append("moody")
    if hit(SOFT_KEYWORDS):
        result.style_tags.append("soft")

    # Temperature / tint
    if hit(WARM_KEYWORDS):
        result.param_delta["temperature"] = result.param_delta.get("temperature", 0) + 6
    if hit(COOL_KEYWORDS):
        result.param_delta["temperature"] = result.param_delta.get("temperature", 0) - 6
    if hit(GREEN_KEYWORDS):
        result.param_delta["tint"] = result.param_delta.get("tint", 0) - 5
    if hit(YELLOW_KEYWORDS):
        result.param_delta.setdefault("hsl", {})
        result.param_delta["hsl"]["yellow_hue"] = -15
    if hit(ORANGE_KEYWORDS):
        result.param_delta.setdefault("hsl", {})
        result.param_delta["hsl"]["yellow_hue"] = -20

    # Saturation / vibrance
    if hit(CLEAN_KEYWORDS):
        result.param_delta["saturation"] = result.param_delta.get("saturation", 1.0) * 0.88
        result.param_delta["vibrance"] = result.param_delta.get("vibrance", 0) - 4
    if hit(VIBRANT_KEYWORDS):
        result.param_delta["saturation"] = result.param_delta.get("saturation", 1.0) * 1.08
        result.param_delta["vibrance"] = result.param_delta.get("vibrance", 0) + 6

    # Curve / clarity
    if hit(LAYER_KEYWORDS):
        result.param_delta["curve"] = "soft_s"
        result.param_delta["clarity"] = result.param_delta.get("clarity", 0) + 4

    # Local adjustments
    if hit(SUBJECT_LIFT_KEYWORDS):
        result.local_adjustment_hint.append("subject_lift")
    if hit(EDGE_LIFT_KEYWORDS):
        result.local_adjustment_hint.append("edge_lift")
    if hit(EDGE_DARK_KEYWORDS):
        result.local_adjustment_hint.append("edge_darken")
    if hit(BG_SUPPRESS_KEYWORDS):
        result.local_adjustment_hint.append("edge_darken")

    # Food theme direct preset suggestion
    for kw, preset_name in FOOD_THEME_KEYWORDS.items():
        if kw in t:
            result.suggested_preset = preset_name
            break

    # Crop hints
    if hit(CROP_SQUARE_KEYWORDS):
        result.crop_suggestion_hint = "1:1"
    elif hit(CROP_PORTRAIT_KEYWORDS):
        result.crop_suggestion_hint = "4:5"
    elif hit(CROP_WIDE_KEYWORDS):
        result.crop_suggestion_hint = "16:9"
    elif hit(CENTER_COMP_KEYWORDS):
        result.crop_suggestion_hint = "center"
    elif hit(THIRDS_COMP_KEYWORDS):
        result.crop_suggestion_hint = "thirds"

    return result


def merge_preset_with_delta(preset: dict, delta: ParseResult) -> dict:
    """Apply parser delta on top of a preset, returning new params dict."""
    params = dict(preset)

    d = delta.param_delta
    if "temperature" in d:
        params["temperature"] = params.get("temperature", 0) + d["temperature"]
    if "tint" in d:
        params["tint"] = params.get("tint", 0) + d["tint"]
    if "saturation" in d:
        params["saturation"] = params.get("saturation", 1.0) * d["saturation"]
    if "vibrance" in d:
        params["vibrance"] = params.get("vibrance", 0) + d["vibrance"]
    if "clarity" in d:
        params["clarity"] = params.get("clarity", 0) + d["clarity"]
    if "curve" in d:
        params["curve"] = d["curve"]
    if "hsl" in d:
        base_hsl = dict(params.get("hsl") or {})
        for k, v in d["hsl"].items():
            base_hsl[k] = base_hsl.get(k, 0) + v
        params["hsl"] = base_hsl

    if delta.local_adjustment_hint:
        params["local_adjustments"] = list(set(
            params.get("local_adjustments", []) + delta.local_adjustment_hint
        ))

    return params
