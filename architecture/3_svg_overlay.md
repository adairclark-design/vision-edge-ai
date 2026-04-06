# Layer 1 Architecture: SVG Overlay Generation

This SOP documents the logic for taking the Layer 3 `AnalysisPayload` and rendering it as a visual "Heads-Up Display" (HUD) on the user's uploaded image.

## 1. Goal

Provide immediate, zero-latency visual clarity by drawing the AI's technical analysis (trend lines, support/resistance zones, price targets) directly over the original chart screenshot.

## 2. Inputs

The frontend component receives:

1. `image_url` (The original unmodified image from Supabase Storage).
2. `svg_overlay` (A JSON object from the `AnalysisPayload` containing coordinates).

## 3. SVG Rendering Rules

1. **Relative Scaling (`viewBox`):**
   - The SVG `viewBox` MUST match the original image dimensions (e.g., `0 0 1920 1080`).
   - The `x` and `y` coordinates from the AI are based on this native resolution, not the CSS-scaled screen size.
   - Using CSS, set `width: 100%`, `height: 100%`, and overlay the `<svg>` exactly on top of the `<img />` using `position: absolute; top: 0; left: 0;`.

2. **Visual Hierarchy (Styling):**
   - **Invalidation Point (Stop Loss):** Render as a bold `strokeColor="red"`, `stroke-dasharray="5,5"` line.
   - **Entry Zone:** Render as a semi-transparent `fillColor="rgba(0, 255, 0, 0.2)"` rectangle over the Y-axis price range.
   - **Targets:** Render as solid `strokeColor="blue"` lines or target icons at specific X/Y coords.

3. **Fallback & Edge Cases:**
   - If `edge_detected` is `false`, **do not render the SVG overlay**. Instead, dim the uploaded image and display the `status_message` ("Market is currently in a noise phase") in white text across the center.
   - If a coordinate falls outside the `viewBox` (e.g., `y: -50`), clip it or clamp it to the edge.

## 4. Maintenance

Any changes to the SVG shapes (e.g., adding a polygon for a wedge pattern) require adding a new `type` to the `AnalysisPayload.svg_overlay.elements` schema in `gemini.md` before updating the React component.
