import logging
import threading

import numpy as np

from ophyd.signal import Signal, EpicsSignalRO
from ophyd.suspenders import SuspenderBase, SuspendFloor

logger = logging.getLogger()


class AvgSignal(Signal):
    """
    Signal that acts as a rolling average of another signal
    """
    def __init__(self, signal, averages, name=None, parent=None, **kwargs):
        super().__init__(name=name, parent=parent, **kwargs)
        self.sig = signal
        self.lock = threading.RLock()
        self.index = 0
        self.values = np.ones(averages) * self.sig.get()
        self.sig.subscribe(self._update_avg)

    def _update_avg(self, *args, value, **kwargs):
        with self.lock:
            self.values[self.index] = value
            self.index += 1
            if self.index == len(self.values):
                self.index = 0
            self.put(np.mean(self.values))


class PvSuspenderBase(SuspenderBase):
    """
    Base class for a suspender that expects a pvname instead of a signal.
    If averages is greater than 1, we'll implement a rolling average of the
    signal instead of the raw value.
    """
    def __init__(self, pvname, sleep=0, pre_plan=None, post_plan=None,
                 tripped_message="", averages=1, **kwargs):
        sig = EpicsSignalRO(pvname)
        if averages > 1:
            sig = AvgSignal(sig, averages, name=sig.name + "_avg")

        super().__init__(sig, sleep=sleep, pre_plan=pre_plan(),
                         post_plan=post_plan(),
                         tripped_message=tripped_message,
                         **kwargs)


class PvSuspendFloor(SuspendFloor, PvSuspenderBase):
    """
    Suspend the run if a pv falls below a set value.
    """
    pass


class BeamEnergySuspendFloor(PvSuspendFloor):
    """
    Suspend the run if the beam energy falls below a set value.
    """
    def __init__(self, suspend_thresh, resume_thresh=None, sleep=5.0,
                 pre_plan=None, post_plan=None, averages=120,
                 **kwargs):
        super().__init__("GDET:FEE1:241:ENRC", suspend_thresh,
                         resume_thresh=resume_thresh, sleep=sleep,
                         pre_plan=pre_plan, post_plan=post_plan,
                         averages=averages, **kwargs)
