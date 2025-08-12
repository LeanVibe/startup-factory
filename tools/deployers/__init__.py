from .base import BaseDeployer
from .fly import FlyDeployer
from .render import RenderDeployer

def get_deployer(name: str):
    name = (name or "").lower()
    if name == "fly":
        return FlyDeployer()
    if name == "render":
        return RenderDeployer()
    return BaseDeployer()
