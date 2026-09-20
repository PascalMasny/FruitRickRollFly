"""A Drosophila mushroom body, in NumPy, with an opinion about one song."""

from brain.audio import JohnstonsOrgan, decode
from brain.config import BrainConfig
from brain.dopamine import DopamineRelease, DopamineTrace, prediction_error
from brain.layers import AntennalLobe, KenyonCells, MBONCompartment
from brain.model import FlyBrain, Response

__all__ = [
    "AntennalLobe",
    "BrainConfig",
    "DopamineRelease",
    "DopamineTrace",
    "FlyBrain",
    "JohnstonsOrgan",
    "KenyonCells",
    "MBONCompartment",
    "Response",
    "decode",
    "prediction_error",
]
