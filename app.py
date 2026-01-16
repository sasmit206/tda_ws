import streamlit as st
import requests
import io
import random
import time
from PIL import Image
from urllib.parse import quote

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="AI Art Studio",
    page_icon="🎨",
    layout="centered"
)

st.title("AI Art Studio")
st.markdown(
    "Generate AI images using a **free community model** "
    "(rate-limited, shared infrastructure)."
)

# --------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------
defaults = {
    "last_gen_time": 0,
    "last_image": None,
    "is_generating": False,
    "current_seed": None,
    "style": "Cyberpunk",
    "model": "turbo",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

COOLDOWN_SECONDS = 10

# --------------------------------------------------
# SIDEBAR (FORM + STATE)
# --------------------------------------------------
with st.sidebar.form("settings_form"):
    st.header("⚙️ Settings")

    selected_style = st.selectbox(
        "Choose Art Style",
        [
            "Cyberpunk",
            "3D Disney",
            "Anime",
            "Oil Painting",
            "Realistic",
            "Pixel Art",
            "No Style"
        ],
        index=[
            "Cyberpunk",
            "3D Disney",
            "Anime",
            "Oil Painting",
            "Realistic",
            "Pixel Art",
            "No Style",
        ].index(st.session_state.style),
    )

    selected_model = st.radio(
        "AI Model",
        ["turbo", "flux"],
        captions=["Fast (Lower Quality)", "High Quality (Slower)"],
        index=0 if st.session_state.model == "turbo" else 1,
    )

    apply = st.form_submit_button("Apply Settings")

if apply:
    st.session_state.style = selected_style
    st.session_state.model = selected_model
    st.cache_data.clear()  # IMPORTANT

style = st.session_state.style
model = st.session_state.model

# --------------------------------------------------
# PROMPT INPUT
# --------------------------------------------------
prompt = st.text_area(
    "Describe your image:",
    height=100,
    placeholder="A serene Japanese village at sunrise..."
)

st.caption(f"Active style: **{style}**")

# --------------------------------------------------
# STYLE MODIFIERS
# --------------------------------------------------
style_map = {
    "Cyberpunk": (
        ", cyberpunk, neon lights, futuristic city, dark atmosphere, "
        "high contrast lighting, ultra detailed"
    ),

    "Anime": (
        ", anime illustration, studio ghibli style, detailed background, "
        "soft lighting, cinematic composition, high quality"
    ),

    "3D Disney": (
        ", pixar style 3d render, unreal engine, expressive characters, "
        "soft global illumination, vibrant colors"
    ),

    "Oil Painting": (
        ", oil painting, fine art, thick brush strokes, textured canvas, "
        "museum quality, dramatic lighting"
    ),

    "Realistic": (
        ", photorealistic, ultra realistic, 35mm lens, cinematic lighting, "
        "high detail, shallow depth of field"
    ),

    "Pixel Art": (
        ", pixel art, 8-bit retro style, game sprite, clean pixels, "
        "limited color palette"
    ),

    "No Style": ""
}


# --------------------------------------------------
# IMAGE FETCH (CACHED)
# --------------------------------------------------
@st.cache_data(ttl=300)
def fetch_image(url: str) -> bytes:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content

# --------------------------------------------------
# SHOW LAST IMAGE
# --------------------------------------------------
if st.session_state.last_image is not None:
    st.image(
        st.session_state.last_image,
        caption="Last generated image",
        use_container_width=True
    )

# --------------------------------------------------
# GENERATION
# --------------------------------------------------
if st.button("Generate Art 🚀", type="primary"):

    if st.session_state.is_generating:
        st.warning("Generation already in progress.")
        st.stop()

    if not prompt.strip():
        st.warning("Please enter a prompt.")
        st.stop()

    now = time.time()
    if now - st.session_state.last_gen_time < COOLDOWN_SECONDS:
        st.warning("Please wait before generating again.")
        st.stop()

    st.session_state.is_generating = True
    st.session_state.last_gen_time = now

    if st.session_state.current_seed is None:
        st.session_state.current_seed = random.randint(1, 1_000_000)

    seed = st.session_state.current_seed

    final_prompt = prompt.strip() + style_map[style]
    encoded_prompt = quote(final_prompt)

    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?model={model}&width=768&height=768"
        f"&seed={seed}&nologo=true"
    )

    try:
        with st.spinner("Generating image..."):
            image_bytes = None

            for attempt in range(3):
                try:
                    image_bytes = fetch_image(url)
                    break
                except Exception:
                    time.sleep(2 ** attempt)

            if image_bytes is None:
                raise RuntimeError("Image generation failed")

            img = Image.open(io.BytesIO(image_bytes))

            st.session_state.last_image = img
            st.session_state.current_seed = None

            st.image(img, caption=f"Generated using {model}", use_container_width=True)

            st.download_button(
                "Download Image",
                data=image_bytes,
                file_name=f"ai_art_{seed}.jpg",
                mime="image/jpeg",
            )

    except Exception:
        st.error("Pollinations is busy or rate-limited. Please wait.")

    finally:
        st.session_state.is_generating = False
