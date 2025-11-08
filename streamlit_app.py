import os
import io
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import requests

st.set_page_config(page_title="AI Hair Transformer — Demo", layout="centered")

st.title("AI Hair Transformer — Demo")
st.write("This is a lightweight Streamlit demo that shows the upload and processing flow.\n"
         "For real Stable Diffusion inference, set a `WORKER_URL` environment variable in the deployment settings that points to a GPU-backed inference worker.")

worker_url = os.environ.get("WORKER_URL")

uploaded = st.file_uploader("Upload a face photo", type=["png", "jpg", "jpeg"]) 
simulate = st.checkbox("Simulate processing (no external worker)", value=True)

if uploaded:
    try:
        image = Image.open(uploaded).convert("RGB")
    except Exception:
        st.error("Could not read the uploaded image. Try a different file.")
        st.stop()

    st.subheader("Uploaded image")
    st.image(image, use_column_width=True)

    st.info("Please wait — hairstyles are being generated. This demo uses a lightweight simulation unless a WORKER_URL is provided.")

    if simulate or not worker_url:
        # Simulate transformations locally (fast, deterministic)
        variants = []

        # Variant 1: brighter
        enhancer = ImageEnhance.Brightness(image)
        variants.append(("Brighter", enhancer.enhance(1.25)))

        # Variant 2: desaturated (pretend a different style)
        converter = ImageEnhance.Color(image)
        variants.append(("Muted color", converter.enhance(0.45)))

        # Variant 3: soft blur + sharpen (pretend stylistic change)
        v3 = image.filter(ImageFilter.GaussianBlur(2)).filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        variants.append(("Soft style", v3))

        st.success("Generated hairstyles (simulated)")
        cols = st.columns(len(variants))
        for col, (title, img) in zip(cols, variants):
            col.image(img, caption=title, use_column_width=True)

    else:
        # Send to external worker
        st.write(f"Calling worker at: {worker_url}")
        try:
            with st.spinner("Uploading and waiting for inference..."):
                files = {"image": ("upload.png", uploaded.getvalue(), "image/png")}
                resp = requests.post(worker_url, files=files, timeout=300)

            if resp.ok:
                # Expecting JSON with either image URLs or base64 images
                data = resp.json()
                images = data.get("images") or data.get("result_images") or []
                if not images:
                    st.success("Worker responded successfully but no images were returned.")
                else:
                    cols = st.columns(len(images))
                    for col, item in zip(cols, images):
                        # If item is a URL
                        if isinstance(item, str) and item.startswith("http"):
                            col.image(item, use_column_width=True)
                        else:
                            # Assume base64-encoded image bytes
                            try:
                                import base64
                                img_bytes = base64.b64decode(item)
                                col.image(img_bytes, use_column_width=True)
                            except Exception:
                                col.write(item)
            else:
                st.error(f"Worker returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            st.error(f"Error calling worker: {e}")

st.markdown("---")
st.caption("If you want a full Django deployment, Streamlit Community Cloud is not an ideal host — consider Render, Railway, or a Docker-based Space. This demo is for UX/testing only.")
