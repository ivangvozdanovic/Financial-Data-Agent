import pyautogui
import base64
from io import BytesIO
from PIL import Image
import io
from openai import OpenAI

def capture_screenshot(tool_args: dict = None):
    try:
        screenshot = pyautogui.screenshot()

        # Save to buffer
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "status": "success",
            "image_base64": img_base64 + "...",  # Trim for display [:100]
            "note": "Returned as base64. Truncated for readability."
        }

    except Exception as e:
        return {"error": f"Screenshot failed: {str(e)}"}


def describe_image(tool_args: dict):
    """
    Args:
        tool_args: {
            "image_path": "path/to/image.png" (optional),
            "image_bytes": b"...",             (optional),
            "prompt": "What is in this image?" (optional)
        }
    Returns:
        dict with "description" or "error"
    """
    try:
        # Handle raw bytes
        if "image_bytes" in tool_args and isinstance(tool_args["image_bytes"], bytes):
            image_bytes = tool_args["image_bytes"]

        # Handle base64 string (your case)
        elif "image_bytes" in tool_args and isinstance(tool_args["image_bytes"], str):
            try:
                image_bytes = base64.b64decode(tool_args["image_bytes"])
            except Exception:
                return {"error": "Provided image_bytes is not valid base64"}

        # Handle file path
        elif "image_path" in tool_args and isinstance(tool_args["image_path"], str):
            with open(tool_args["image_path"], "rb") as f:
                image_bytes = f.read()

        else:
            return {"error": "Missing or invalid 'image_path' or 'image_bytes'"}

        def compress_image_bytes(image_bytes, max_size=(256, 256), quality=40):
            """Compress image to JPEG at smaller resolution and quality."""
            try:
                img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                img.thumbnail(max_size)  # Downscale
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=quality)
                return buffer.getvalue()
            except Exception as e:
                raise RuntimeError(f"Image compression failed: {e}")

        compressed_bytes = compress_image_bytes(image_bytes)
        print(f"Compressed size: {len(compressed_bytes)} bytes")
        img = Image.open(io.BytesIO(compressed_bytes))
        img.verify()  # This will raise if the image is invalid

        base64_image = base64.b64encode(compressed_bytes).decode("utf-8")
        prompt = tool_args.get("prompt", "What is in this image?")
        print(f"Base64 size: {len(base64_image)} characters")
        image_url = f"data:image/jpeg;base64,{base64_image}"

        client = OpenAI()  # Automatically uses your OPENAI_API_KEY env variable

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=500
        )


        return {"description": response.choices[0].message["content"]}

    except Exception as e:
        return {"error": str(e)}
