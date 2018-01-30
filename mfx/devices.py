import pcdsdevices.device_types


class XFLS(pcdsdevices.device_types.XFLS):
    """
    XRay Focusing Lens (Be)

    These are the stacks with common names on their states and state config PVs
    that show the focusing config
    """
    states_list = ['6K70', '7K50', '9K45', 'OUT']
    in_states = ['6K70', '7K50', '9K45']
