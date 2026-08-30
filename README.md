# Comfyui-Resolution-Master-Lite

A simplified edit of **[Azornes/Comfyui-Resolution-Master](https://github.com/Azornes/Comfyui-Resolution-Master)** for ComfyUI.

This Lite version keeps the preset-driven resolution and latent-generation workflow while removing UI features that are not needed for a compact preset selector.

## Changes in this Lite version

- Removed the interactive 2D resolution canvas.
- Removed image input and Auto-Detect functionality.
- Removed the visible batch-size control; batch size is fixed internally to `1`.
- Removed the visible rescale-factor output.
- Simplified the visible outputs to:
  - `width`
  - `height`
  - `latent`
- Adjusted output spacing and node layout for a cleaner compact interface.
- Removed the obsolete **2D Canvas Shortcuts** section from the Help dialog.
- Renamed the node/extension so it can coexist with the original Resolution Master installation.

## Credits and attribution

The original **Comfyui-Resolution-Master** project was created by **Azornes**:

https://github.com/Azornes/Comfyui-Resolution-Master

This repository is an edited derivative of that project. The modifications in this Lite version were made **with ChatGPT by OpenAI, at the user's direction**.

The original project's license is preserved in [`LICENSE`](LICENSE).

## Installation

Clone this repository into your ComfyUI `custom_nodes` folder:

```bash
git clone https://github.com/MarcusBankz/Comfyui-Resolution-Master-Lite.git
```

Then restart ComfyUI and search for:

```text
Resolution Master Lite
```

The Lite version uses a separate node ID and extension name so it can be installed alongside the original.

## Repository

https://github.com/MarcusBankz/Comfyui-Resolution-Master-Lite
