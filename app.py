import io
import json

import streamlit as st
from PIL import Image

from parser import parse_prompt, merge_preset_with_delta
from processor import (
    process_image,
    crop_to_ratio,
    apply_manual_crop,
    apply_straighten,
    suggest_crop,
)
from scraper import list_presets_for_theme

st.set_page_config(page_title="Photo Coloring", layout="wide", page_icon="🎨")


@st.cache_data
def load_presets():
    with open("presets.json", "r", encoding="utf-8") as f:
        return json.load(f)


presets = load_presets()

# Bucket presets by theme for the UI
THEME_BUCKETS = {
    "全部": list(presets.keys()),
    "🍽 食物": [k for k in presets if k.startswith("Food:")],
    "🏙 街景": [k for k in presets if "Street" in k or "Japanese" in k.split(":")[0].strip()],
    "🎬 電影": [k for k in presets if k in ("Cinematic", "Teal & Orange", "Moody")],
    "✨ 膠片": [k for k in presets if k in ("Film", "Light & Airy")],
}
# Fallback: anything not bucketed goes into 全部 only
bucketed = {p for v in list(THEME_BUCKETS.values()) for p in v}
THEME_BUCKETS["全部"] = list(presets.keys())

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎨 Photo Coloring")
    st.markdown("---")

    uploaded_file = st.file_uploader("上傳照片", type=["jpg", "jpeg", "png"])

    # Theme selector
    st.markdown("### 主題")
    active_theme = st.radio(
        "主題",
        list(THEME_BUCKETS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )

    available = THEME_BUCKETS[active_theme]

    st.markdown("### 選擇風格")
    selected = st.radio(
        "風格",
        options=available,
        label_visibility="collapsed",
    )
    if selected:
        st.caption(presets[selected]["description"])

    # Show food reference info panel when a food preset is selected
    if selected and selected.startswith("Food:"):
        food_refs = list_presets_for_theme("food")
        ref = food_refs.get(selected, {})
        if ref:
            with st.expander("📚 參考資料來源"):
                st.caption(ref.get("rationale", ""))
                tags = ref.get("style_tags", [])
                if tags:
                    st.caption("關鍵詞：" + " · ".join(tags[:5]))
                crop_hints = ref.get("crop_hints", [])
                if crop_hints:
                    st.caption("建議裁切比例：" + " / ".join(crop_hints))

    st.markdown("---")
    st.markdown("### 自然語言微調")
    prompt_text = st.text_area(
        "描述你想要的風格",
        placeholder="例如：咖啡廳、微暖偏綠、主體提亮、降低藍綠飽和\n輸入食物主題關鍵字（如「早餐」「沙拉」「巧克力」）可自動切換預設",
        height=100,
        label_visibility="collapsed",
    )

    parsed = None
    auto_switch_preset = None
    if prompt_text.strip():
        parsed = parse_prompt(prompt_text)
        suggested = getattr(parsed, "suggested_preset", None)
        if suggested and suggested in presets:
            auto_switch_preset = suggested
            st.info(f"偵測到主題，建議切換：**{auto_switch_preset}**")
        if parsed.style_tags:
            st.caption(f"風格標籤：{', '.join(parsed.style_tags)}")
        if parsed.crop_suggestion_hint:
            st.caption(f"構圖提示：{parsed.crop_suggestion_hint}")

    st.markdown("---")
    st.markdown("### 構圖與裁切")

    crop_mode = st.radio(
        "裁切模式",
        ["不裁切", "比例裁切", "手動裁切", "拉直"],
        label_visibility="collapsed",
    )

    crop_ratio = None
    manual_crop = None
    straighten_angle = 0.0
    show_thirds = False

    if crop_mode == "比例裁切":
        # Use food reference crop hint if available
        default_ratio_idx = 0
        ratio_options = ["1:1", "4:5", "3:4", "16:9"]
        if selected and selected.startswith("Food:"):
            food_refs = list_presets_for_theme("food")
            hints = food_refs.get(selected, {}).get("crop_hints", [])
            if hints and hints[0] in ratio_options:
                default_ratio_idx = ratio_options.index(hints[0])
        crop_ratio = st.selectbox("選擇比例", ratio_options, index=default_ratio_idx)
        show_thirds = st.checkbox("顯示三分線參考")
        if uploaded_file is not None:
            img_tmp = Image.open(uploaded_file)
            suggestion = suggest_crop(img_tmp, crop_ratio)
            st.caption(
                f"建議裁切：從 ({suggestion['x']}, {suggestion['y']}) "
                f"裁 {suggestion['width']}×{suggestion['height']} px"
            )

    elif crop_mode == "手動裁切":
        if uploaded_file is not None:
            img_tmp = Image.open(uploaded_file)
            iw, ih = img_tmp.size
            st.caption(f"原圖尺寸：{iw} × {ih} px")
            cx = st.number_input("左邊起點 X", 0, iw - 1, 0)
            cy = st.number_input("上邊起點 Y", 0, ih - 1, 0)
            cw = st.number_input("寬度", 1, iw - int(cx), iw - int(cx))
            ch = st.number_input("高度", 1, ih - int(cy), ih - int(cy))
            manual_crop = (int(cx), int(cy), int(cw), int(ch))
        show_thirds = st.checkbox("顯示三分線參考")

    elif crop_mode == "拉直":
        straighten_angle = st.slider("旋轉角度", -15.0, 15.0, 0.0, 0.1)

# ── Main area ────────────────────────────────────────────────────────────────
if uploaded_file is None:
    st.markdown("## 請先在左側上傳照片 👈")

    # Show food preset gallery when no image is uploaded
    if active_theme == "🍽 食物":
        st.markdown("---")
        st.markdown("### 食物攝影 Preset 預覽")
        food_refs = list_presets_for_theme("food")
        cols = st.columns(3)
        for i, (name, ref) in enumerate(food_refs.items()):
            with cols[i % 3]:
                st.markdown(f"**{name}**")
                st.caption(ref.get("description", ""))
                tags = ref.get("style_tags", [])
                st.caption("· ".join(tags[:4]))
                crops = ref.get("crop_hints", [])
                if crops:
                    st.caption(f"建議裁切：{' / '.join(crops)}")
else:
    original = Image.open(uploaded_file)

    # Determine effective preset (auto-switch from prompt if suggested)
    active_preset_name = auto_switch_preset if auto_switch_preset else selected
    if active_preset_name not in presets:
        # Fallback to first available preset if selection state is inconsistent
        active_preset_name = list(presets.keys())[0]
    base_params = dict(presets[active_preset_name])

    if parsed is not None:
        effective_params = merge_preset_with_delta(base_params, parsed)
    else:
        effective_params = base_params

    processed = process_image(original, effective_params)

    # Apply crop / straighten
    if crop_mode == "比例裁切" and crop_ratio:
        processed = crop_to_ratio(processed, crop_ratio)
        original_display = crop_to_ratio(original, crop_ratio)
    elif crop_mode == "手動裁切" and manual_crop:
        x, y, w, h = manual_crop
        processed = apply_manual_crop(processed, x, y, w, h)
        original_display = apply_manual_crop(original, x, y, w, h)
    elif crop_mode == "拉直" and straighten_angle != 0:
        processed = apply_straighten(processed, straighten_angle)
        original_display = apply_straighten(original, straighten_angle)
    else:
        original_display = original

    # ── Preset switch banner ──
    if auto_switch_preset and auto_switch_preset != selected:
        st.success(f"已根據關鍵字自動切換為 **{auto_switch_preset}** 風格")

    # ── Preview ──
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**原圖**")
        st.image(original_display, width="stretch")
    with col2:
        label = active_preset_name
        if parsed and parsed.style_tags:
            label += f"  +  {' · '.join(parsed.style_tags)}"
        st.markdown(f"**{label}**")
        st.image(processed, width="stretch")

    if show_thirds:
        w_px, h_px = processed.size
        st.caption(
            f"三分線交點（供構圖參考）："
            f"({w_px//3}, {h_px//3})  ({w_px*2//3}, {h_px//3})  "
            f"({w_px//3}, {h_px*2//3})  ({w_px*2//3}, {h_px*2//3})"
        )

    # ── Download ──
    buf = io.BytesIO()
    processed.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    fname = active_preset_name.lower().replace(" ", "_").replace(":", "")
    if parsed and parsed.style_tags:
        fname += "_" + "_".join(parsed.style_tags[:2])
    st.download_button(
        label="⬇️ 下載調色後照片",
        data=buf,
        file_name=f"{fname}.jpg",
        mime="image/jpeg",
    )

    # ── Param inspector ──
    with st.expander("查看套用的參數"):
        display_params = {k: v for k, v in effective_params.items() if v not in (None, 0, [], {})}
        st.json(display_params)
