import logging

from mfx.devices import LaserShutter
from mfx.db import daq
from pcdsdevices.sequencer import EventSequencer, EventStep
from pcdsdevices.evr import Trigger

#########
# TODO  #
#########
# * elog
# * time estimations


logger = logging.getLogger(__name__)


#######################
#  Object Declaration #
#######################

# Declare shutter objects
opo_shutter = LaserShutter('MFX:USR:ao1:6', name='opo_shutter')
evo_shutter1 = LaserShutter('MFX:USR:ao1:7', name='evo_shutter1')
evo_shutter2 = LaserShutter('MFX:USR:ao1:2', name='evo_shutter1')
evo_shutter3 = LaserShutter('MFX:USR:ao1:3', name='evo_shutter1')

# Sequencer object
sequencer = EventSequencer('ECS:SYS0:7', name='mfx_sequencer')

# Sequencer steps
seq_prefix = 'MFX:ECS:IOC:01'
seq_no = 7
seq_steps = [EventStep(seq_prefix, seq_no, step, name='step_{}'.format(step))
             for step in range(0, 20)]

# Trigger objects
pacemaker = Trigger('MFX:LAS:EVR:01:TRIG4', name='pacemaker_trigger')
inhibit = Trigger('MFX:LAS:EVR:01:TRIG6', name='inhibit_trigger')

# Laser parameter
opo_time_zero = 748935
inhibit_delay = 500000

###########################
# Configuration Functions #
###########################

class User:
    """Generic User Object"""
    opo_shutter = opo_shutter
    evo_shutter1 = evo_shutter1
    evo_shutter2 = evo_shutter2
    evo_shutter3 = evo_shutter3
    sequencer = sequencer

    @property
    def current_rate(self):
        """Current configured EventSequencer rate"""
        return sequencer.sync_marker.get(as_string=True)

    def configure_shutters(self, pulse1=False, pulse2=False, pulse3=False, opo=False):
        """
        Configure all four laser shutters

        True means that the pulse will be used and the shutter is removed.
        False means that the pulse will be blocked and the shutter is inserted

        Parameters
        ----------
        pulse1: bool
            Controls ``evo_shutter1``

        pulse2: bool
            Controls ``evo_shutter2``

        pulse3: bool
            Controls ``evo_shutter3``

        opo: bool
            Controls ``opo_shutter``
        """
        for state, shutter in zip((pulse1, pulse2, pulse3, opo),
                                  (evo_shutter1, evo_shutter2,
                                   evo_shutter3, opo_shutter)):
            logger.info("Using %s : %s", shutter.name, state)
            shutter.move(int(state) + 1)

    def configure_sequencer(self, rate='10Hz'):
        """
        Setup laser triggers and EventSequencer

        Parameters
        ----------
        rate : str, optional
            "10Hz" or "30Hz"
        """
        logger.info("Configure EventSequencer ...")
        # Setup sequencer
        sequencer.sync_marker.put(rate)
        sequencer.sequence_length.put(5)
        # Set sequence
        seq_steps[0].configure({'eventcode': 197, 'delta_beam': 2,
                                'fiducial': 0, 'comment': 'PulsePicker'})
        seq_steps[1].configure({'eventcode': 212, 'delta_beam': 0,
                                'fiducial': 0, 'comment': 'Delay > 7 ms'})
        seq_steps[2].configure({'eventcode': 211, 'delta_beam': 1,
                                'fiducial': 0, 'comment': 'Delay > 160 us'})
        seq_steps[3].configure({'eventcode': 210, 'delta_beam': 1,
                                'fiducial': 0, 'comment': 'Delay < 160 us'})
        seq_steps[4].configure({'eventcode': 198, 'delta_beam': 0,
                                'fiducial': 0, 'comment': 'DAQ Readout'})
        # Clear other sequence steps 
        for i in range(5, 20):
            seq_steps[i].clear()


    def configure_evr(self):
        """
        Configure the Pacemaker and Inhibit EVR

        This handles setting the correct polarity and widths. However this
        **does not** handle configuring the delay between the two EVR triggers.
        """
        logger.debug("Configuring triggers to defaults ...")
        # Pacemaker Trigger
        pacemaker.configure({'eventcode': 40, 'polarity': 0,
                             'width': 50000./1e9})
        pacemaker.enable()
        # Inhibit Trigger
        inhibit.configure({'polarity': 1, 'width': 2000000./1e9})
        inhibit.enable()


    def set_delay(self, delay):
        """
        Set the relative delay between the pacemaker and inhibit triggers

        Parameters
        ----------
        delay: float
            Requested laser delay in nanoseconds. Must be less that 15.5 ms
        """
        # Determine event code of inhibit pulse
        logger.info("Setting delay %s", delay)
        if delay <= 0.16e6:
            logger.debug("Triggering on simultaneous event code")
            inhibit_ec = 210
            ipulse = 0
        elif delay <= 7.e6:
            logger.debug("Triggering on one event code prior")
            inhibit_ec = 211
            ipulse = 1
        elif delay <= 15.5e6:
            logger.debug("Triggering two event codes prior")
            inhibit_ec = 212
            ipulse = 2
        else:
            raise ValueError("Invalid input %s ns, must be < 15.5 ms")
        # Determine relative delays
        pulse_delay = ipulse*1.e9/120. # Convert to ns
        # Configure Inhibit pulse
        inhibit_delay = opo_time_zero - inhibit_delay + pulse_delay
        inhibit.configure({"eventcode": inhibit_ec, "delay": inhibit_delay})
        # Conifgure Pacemaker pulse
        pacemaker_delay = opo_time_zero + pulse_delay
        pacemaker.configure({"delay": pacemaker_delay})


    ######################
    # Scanning Functions #
    ######################
    def perform_run(self, events, record=True, comment='', post=True,
                    **kwargs):
        """
        Perform a single run of the experiment

        Parameters
        ----------
        events: int
            Number of events to include in run

        record: bool, optional
            Whether to record the run

        comment : str, optional
            Comment for ELog

        post: bool, optional
            Whether to post to the experimental ELog or not

        kwargs:
            Used to control the laser shutters. See ``configure_shutters`` for more
            information

        Note
        ----
        This does not configure the laser parameters. Either use ``loop`` or
        ``configure_evr`` and ``configure_sequencer`` to set these parameters
        """
        # Configure the shutters
        self.configure_shutters(**kwargs)
        # time.sleep(3) / a leftover from original script
        # Start recording
        logger.info("Starting DAQ run, -> record=%s", record)
        daq.begin(events=events, record=record)
        # Post information to elog
        # Wait for the DAQ to finish
        logger.info("Waiting or DAQ to complete %s events ...", events)
        daq.wait()
        logger.info("Run complete!")
        daq.end_run()
        # time.sleep(3) / a leftover from original script


    def loop(self, delays=[], nruns=1, pulse1=False, pulse2=False,
             pulse3=False, light_events=3000, dark_events=None, rate='10Hz',
             **kwargs):
        """
        Loop through a number of delays a number of times while running the DAQ

        Parameters
        ----------
        delays: list, optional
            Requested laser delays in nanoseconds

        nruns: int, optional
            Number of iterations to run requested delays

        pulse1: bool, optional
            Include the first pulse

        pulse2: bool, optional
            Include the second pulse

        pulse3: bool, optional
            Include the third pulse

        light_events: int, optional
            Number of events to sample with requested laser pulses

        dark_events: int, optional
            Number of events to sample with all lasers shuttered

        rate : str, optional
            "10Hz" or "30Hz"

        kwargs:
            Remainder of the kwargs are passed to ``perform_run`` to setup the DAQ
            and ELog. This includes ``record``, ``comment``, and ``post``
        """
        self.configure_sequencer(rate=rate)
        #configure_evr()
        # Preserve the original state of DAQ
        logger.info("Running delays %r, %s times ...", delays, nruns)
        delays = delays or [False]
        logger.info("Starting EventSequencer ...")
        sequencer.start()
        # Estimated time for completion
        try:
            for run in range(nruns):
                logger.info("Beginning run %s of %s", run, nruns)
                for delay in delays:
                    if light_events:
                        logger.info("Beginning light events using delay %s", delay)
                        # Set the laser delay if it exists
                        if delay:
                            pass
                            #self.set_delay(delay)
                        # Perform the light run
                        self.perform_run(light_events, pulse1=pulse1,
                                         pulse2=pulse2, pulse3=pulse3,
                                         opo=bool(delay), **kwargs)
                    # Estimated time for completion
                    # Perform the dark run
                    # No shutter information means all closed!
                    if dark_events:
                        self.perform_run(events=dark_events, **kwargs)
            logger.info("All requested scans completed!")
        except KeyboardInterrupt:
            logger.warning("Scan interrupted by user request!")
        # Return the DAQ to the original state
        finally:
            sequencer.stop()
            logger.info("Disconnecting from DAQ ...")
            daq.disconnect()
            logger.info("Closing all laser shutters ...")
            self.configure_shutters()
