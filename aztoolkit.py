# ComfyUI - azToolkit - Azornes 2025

import torch
import comfy.model_management
from comfy_api.latest import io

try:
    from .core.auto_detect import (
        apply_backend_auto_detect_fallback,
        calculate_rescale_factor,
        safe_float,
        safe_int,
    )
    from .core.calculation_api import register_calculation_routes
    from .core.dimension_cache import register_dimension_routes, store_detected_dimensions
    from .core.log_system import create_module_logger
except ImportError:
    from core.auto_detect import (
        apply_backend_auto_detect_fallback,
        calculate_rescale_factor,
        safe_float,
        safe_int,
    )
    from core.calculation_api import register_calculation_routes
    from core.dimension_cache import register_dimension_routes, store_detected_dimensions
    from core.log_system import create_module_logger


log = create_module_logger(__name__)


class ResolutionMasterLite(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ResolutionMasterLite",
            display_name="Resolution Master Lite",
            category="utils/azToolkit",
            description="Resolution Master Lite: presets, scaling, and latent-size helper without the free-form canvas or image input.",
            inputs=[
                io.Combo.Input(
                    "mode",
                    options=["Manual", "Manual Sliders", "Common Resolutions", "Aspect Ratios"],
                    tooltip="Choose how to control the output size. Manual mode uses the Resolution Master canvas.",
                ),
                io.Combo.Input(
                    "latent_type",
                    options=["latent_4x8", "latent_128x16"],
                    default="latent_4x8",
                    tooltip="Choose the latent type. Use 4x8 for most models, or 128x16 for Flux.2.",
                ),
                io.Int.Input("width", default=512, min=0, max=32768, step=64, tooltip="Final output width in pixels."),
                io.Int.Input("height", default=512, min=0, max=32768, step=64, tooltip="Final output height in pixels."),
                io.Boolean.Input("auto_detect", default=False, label_on="Auto-detect from input", label_off="Manual", tooltip="Detect the size from the connected input image."),
                io.String.Input("auto_detect_source", default="backend", tooltip="Technical setting used by the Resolution Master interface."),
                io.Int.Input("auto_detect_width", default=0, min=0, max=32768, tooltip="Detected input width used by auto-detect."),
                io.Int.Input("auto_detect_height", default=0, min=0, max=32768, tooltip="Detected input height used by auto-detect."),
                io.Boolean.Input("auto_fit_on_change", default=False, tooltip="When a new image is detected, fit it to the closest preset automatically."),
                io.Boolean.Input("auto_resize_on_change", default=False, tooltip="When a new image is detected, resize it automatically using the selected scaling mode."),
                io.Boolean.Input("auto_snap_on_change", default=False, tooltip="When a new image is detected, round its size to the selected snap step."),
                io.Boolean.Input("smart_fit", default=False, tooltip="Fit to the closest preset aspect ratio while keeping the size close to the current resolution."),
                io.Boolean.Input("use_custom_calc", default=False, tooltip="When a new image is detected, apply the selected model or category size rules automatically."),
                io.Boolean.Input("preserve_scaling_ratio", default=False, tooltip="Keep the image proportions while scaling."),
                io.String.Input("selected_category", default="", tooltip="Selected preset category."),
                io.Int.Input("snap_value", default=64, min=1, max=32768, tooltip="Snap step used when rounding width and height."),
                io.Float.Input("upscale_value", default=1.0, min=0.0, max=100.0, tooltip="Manual scale multiplier."),
                io.Int.Input("target_resolution", default=1080, min=1, max=32768, tooltip="Target p-resolution used for scaling."),
                io.Float.Input("target_megapixels", default=2.0, min=0.0, max=1000.0, tooltip="Target megapixels used for scaling."),
                io.String.Input("auto_detect_presets_json", default="{}", tooltip="Technical preset data used by auto-detect."),
                io.String.Input("rescale_mode", default="resolution", tooltip="Scaling mode used for the Rescale Factor output."),
                io.Float.Input("rescale_value", default=1.0, step=0.001, min=0.0, max=100.0, tooltip="Current Rescale Factor value shown by the interface."),
            ],
            outputs=[
                io.Int.Output("width", tooltip="Final output width in pixels."),
                io.Int.Output("height", tooltip="Final output height in pixels."),
                io.Latent.Output("latent", tooltip="Empty latent created with the selected size and latent type. Batch size is fixed to 1."),
            ],
            hidden=[io.Hidden.unique_id, io.Hidden.prompt],
        )

    @staticmethod
    def detect_image_dimensions(input_image):
        if input_image.dim() == 4:  # [batch, height, width, channels]
            return int(input_image.shape[2]), int(input_image.shape[1])
        if input_image.dim() == 3:  # [height, width, channels]
            return int(input_image.shape[1]), int(input_image.shape[0])
        log.warning("Unsupported input image tensor dimensions", input_image.dim())
        return None

    @staticmethod
    def _is_empty_local_image_gallery_selection(value):
        return str(value or "").strip().lower() in ("", "none", "null", "undefined")

    @classmethod
    def is_empty_local_image_gallery_input(cls, prompt, unique_id):
        if not isinstance(prompt, dict) or unique_id is None:
            return False

        current_node = prompt.get(str(unique_id)) or prompt.get(unique_id)
        input_link = current_node.get("inputs", {}).get("input_image") if isinstance(current_node, dict) else None
        if not isinstance(input_link, (list, tuple)) or not input_link:
            return False

        source_node_id = str(input_link[0])
        source_node = prompt.get(source_node_id) or prompt.get(input_link[0])
        if not isinstance(source_node, dict) or source_node.get("class_type") != "LocalImageGallery":
            return False

        selected_image = source_node.get("inputs", {}).get("selected_image", "")
        return cls._is_empty_local_image_gallery_selection(selected_image)

    @classmethod
    def execute(
        cls,
        mode,
        latent_type,
        width,
        height,
        auto_detect,
        auto_detect_source,
        auto_detect_width,
        auto_detect_height,
        auto_fit_on_change,
        auto_resize_on_change,
        auto_snap_on_change,
        smart_fit,
        use_custom_calc,
        preserve_scaling_ratio,
        selected_category,
        snap_value,
        upscale_value,
        target_resolution,
        target_megapixels,
        auto_detect_presets_json,
        rescale_mode,
        rescale_value,
    ) -> io.NodeOutput:
        unique_id = cls.hidden.unique_id
        prompt = cls.hidden.prompt
        device = comfy.model_management.intermediate_device()
        batch_size = 1  # Resolution Master Lite intentionally fixes batch size to one.

        log.debug(
            "Executing",
            "device=",
            device,
            "mode=",
            mode,
            "latent_type=",
            latent_type,
            "width=",
            width,
            "height=",
            height,
            "auto_detect=",
            auto_detect,
        )

        # Auto-detect input-image support intentionally removed in this custom build.
        # The hidden compatibility settings remain so existing Resolution Master workflows
        # can still deserialize without breaking.

        rescale_factor = calculate_rescale_factor(
            width,
            height,
            rescale_mode,
            safe_float(upscale_value, 1.0),
            safe_int(target_resolution, 1080),
            safe_float(target_megapixels, 2.0),
        )

        if latent_type == "latent_128x16":
            latent = torch.zeros([batch_size, 128, height // 16, width // 16], device=device)
        else:
            latent = torch.zeros([batch_size, 4, height // 8, width // 8], device=device)

        log.debug(
            "Returning result",
            "width=",
            width,
            "height=",
            height,
            "rescale_factor=",
            rescale_factor,
            "batch_size=",
            batch_size,
        )
        return io.NodeOutput(width, height, {"samples": latent})


register_calculation_routes()
