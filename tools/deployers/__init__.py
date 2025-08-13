from .base import BaseDeployer
from .fly import FlyDeployer
from .render import RenderDeployer
from .railway import RailwayDeployer

def get_deployer(name: str):
    name = (name or "").lower()
    if name == "fly":
        return FlyDeployer()
    if name == "render":
        return RenderDeployer()
    if name == "railway":
        return RailwayDeployer()
    return BaseDeployer()
