from ophyd import (Device, EpicsSignal, EpicsSignalRO, Component as C,
                   FormattedComponent as FC)
from ophyd.signal import AttributeSignal

import pcdsdevices.device_types
from pcdsdevices.inout import InOutPositioner

class XFLS(pcdsdevices.device_types.XFLS):
    """
    XRay Focusing Lens (Be)

    These are the stacks with common names on their states and state config PVs
    that show the focusing config
    """
    states_list = ['6K70', '7K50', '9K45', 'OUT']
    in_states = ['6K70', '7K50', '9K45']

class Piezo(Device):
    """
    Device for controlling piezo injector motors
    """
    velocity =  C(EpicsSignalRO, ':VELOCITYGET')
    req_velocity = C(EpicsSignal, ':VELOCITYSET')
    open_loop_step = C(EpicsSignal, ':OPENLOOPSTEP')

    _default_read_attrs = ['open_loop_step']
    _default_configuration_attrs = ['velocity']

    def tweak(self, distance):
        """
        Tweak the Piezo by a distance
        """
        return self.open_loop_step.set(distance)


class LaserShutter(InOutPositioner):
    """Controls shutter controlled by Analog Output"""
    # EpicsSignals
    voltage = C(EpicsSignal, '')
    state = FC(AttributeSignal, 'voltage_check')
    # Constants
    out_voltage = 5.0
    in_voltage = 0.0
    barrier_voltage = 1.4

    @property
    def voltage_check(self):
        """Return the position we believe shutter based on the channel"""
        if self.voltage.get() >= self.barrier_voltage:
            return 'OUT'
        else:
            return 'IN'

    def _do_move(self, state):
        """Override to just put to the channel"""
        if state.name == 'IN':
            self.voltage.put(self.in_voltage)
        elif state.name == 'OUT':
            self.voltage.put(self.out_voltage)
        else:
            raise ValueError("%s is in an invalid state", state)
