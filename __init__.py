from comfy_api.latest import ComfyExtension, io

from .aztoolkit import ResolutionMasterLite


class ResolutionMasterLiteExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [ResolutionMasterLite]


async def comfy_entrypoint() -> ResolutionMasterLiteExtension:
    return ResolutionMasterLiteExtension()

WEB_DIRECTORY = "./js"

__all__ = ["WEB_DIRECTORY", "comfy_entrypoint"]
