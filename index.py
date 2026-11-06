import io
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)

def process_custom_image_bytes(file_stream, width, height, target_kb=45):
    with Image.open(file_stream) as img:
        # Convert transparent PNGs/palettes to white background
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            canvas = Image.new("RGB", img.size, (255, 255, 255))
            canvas.paste(img, mask=img.convert("RGBA").split()[3])
            img = canvas
        else:
            img = img.convert("RGB")

        # Resize dynamically to user-defined dimensions
        resized_img = img.resize((width, height), Image.Resampling.LANCZOS)

        # Save to JPEG in-memory
        buffer = io.BytesIO()
        resized_img.save(buffer, format="JPEG", quality=100)
        jpeg_bytes = buffer.getvalue()

    # Calculate padding for user-defined KB
    target_bytes = target_kb * 1024
    if len(jpeg_bytes) < target_bytes:
        final_bytes = jpeg_bytes + (b"\x00" * (target_bytes - len(jpeg_bytes)))
    else:
        final_bytes = jpeg_bytes

    output_stream = io.BytesIO(final_bytes)
    output_stream.seek(0)
    return output_stream


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Custom Resizer API is running"}), 200


@app.route("/api/resize-signature", methods=["POST"])
def resize_signature_api():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use form-data key 'file'."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    try:
        # Read user-defined parameters from request form
        width = int(request.form.get("width", 140))
        height = int(request.form.get("height", 60))
        target_kb = int(request.form.get("target_kb", 45))

        if width <= 0 or height <= 0 or target_kb <= 0:
            return jsonify({"error": "Width, height, and target KB must be positive numbers."}), 400

        output_buffer = process_custom_image_bytes(file.stream, width, height, target_kb)

        return send_file(
            output_buffer,
            mimetype="image/jpeg",
            as_attachment=True,
            download_name=f"resized_{width}x{height}_{target_kb}kb.jpg"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)