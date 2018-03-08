import logging

from .devices import XFLS, Piezo, EventSequencer

from hutch_python.utils import safe_load
from mfx.suspenders import BeamEnergySuspendFloor

logger = logging.getLogger(__name__)



with safe_load('transfocator'):
    from transfocate import Transfocator
    tfs = Transfocator("MFX:LENS", name='MFX Transfocator')

with safe_load('mfx_prefocus'):
    mfx_prefocus = XFLS('MFX:DIA:XFLS', name='mfx_prefocus')

with safe_load('beam_suspender'):
    beam_suspender = BeamEnergySuspendFloor(0.6)

with safe_load('inj_z'):
    inj_x = Piezo('MFX:USR:PIZ:01', name='inj_z')

with safe_load('shield_z'):
    inj_y = Piezo('MFX:USR:PIZ:02', name='shield_z')

with safe_load('seq'):
    seq = EventSequencer('ECS:SYS0:7', name='seq')
