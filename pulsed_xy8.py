import numpy as np

from traits.api import Trait, Instance, Property, String, Range, Float, Int, Bool, Array, Enum
from traitsui.api import View, Item, HGroup, VGroup, VSplit, Tabbed, EnumEditor, TextEditor, Group, Label

import logging
import time

import random

from hardware.api import PulseGenerator, TimeTagger, Microwave, MicrowaveD, MicrowaveE, RFSource
import hardware.api as ha
from tools.emod import ManagedJob

from tools.utility import GetSetItemsMixin

from pulsed_rabi import Rabi
from pulsed import Pulsed

class XY83pi2(Rabi):
    """
    Defines a CPMG measurement with both pi/2 and 3pi/2 readout pulse,
    using a second microwave switch for 90 degree phase shifted pi pulses.
    
    Includes also bright (no pulse) and dark (pi_y pulse) reference points.
    """

    measurement_type = 'xy8_3pi2'

    t_pi2_x = Range(low=1., high=100000., value=1000., desc='pi/2 pulse length (x)', label='pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    t_pi_y = Range(low=1., high=100000., value=1000., desc='pi pulse length (y)', label='pi y [ns]', mode='text', auto_set=False, enter_set=True)
    t_pi_x = Range(low=1., high=100000., value=1000., desc='pi pulse length (x)', label='pi x [ns]', mode='text', auto_set=False, enter_set=True)
    t_3pi2_x = Range(low=1., high=100000., value=1000., desc='3pi/2 pulse length (x)', label='3pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    n_pi = Range(low=1, high=64, value=1, desc='number of XY8-n pulses', label='n pi', mode='text', auto_set=False, enter_set=True)
    n_ref = Range(low=0, high=100, value=0, desc='number of reference pulses', label='n ref', mode='text', auto_set=False, enter_set=True)
    period = Range(low=0, high=1e8, value=100, label='period [ns]', mode='text', auto_set=False, enter_set=True)
    span = Range(low=0, high=1e8, value=100, label='span [ns]', mode='text', auto_set=False, enter_set=True)
    step = Range(low=0, high=1e3, value=20, label='step', mode='text', auto_set=False, enter_set=True)
    non_uniform = Bool(True, label='non uniform')
    #logscale = Bool(False, desc='if non uniform==False, log scale == True, create from tau_begin, tau_end, step', label= 'logscale')
    #dense_step = Range(low=0, high=1e3, value=20, label='dense step', mode='text', auto_set=False, enter_set=True)
    #tau_middle = Range(low=0, high=1e8, value=100, label='tau_middle', mode='text', auto_set=False, enter_set=True)
    non_uniform_begin = Range(low=0, high=1e8, value=100, label='non_uniform_begin [ns]', mode='text', auto_set=False, enter_set=True)
    step_0 = Range(low=0, high=1e3, value=20, label='step_0', mode='text', auto_set=False, enter_set=True)
    span_0 = Range(low=0, high=1e8, value=100, label='span_0 [ns]', mode='text', auto_set=False, enter_set=True)
    
    def start_up(self):
        PulseGenerator().Night()
        Microwave().setOutput(self.power, self.frequency)

    def apply_parameters(self):

        _norm_tau = np.arange(self.tau_begin, self.tau_end, self.tau_delta)

        if self.non_uniform:
			## for Detail measurement of each k; 
			## 1. step_0, span_0 for the begining taus; 2. span around tau_end/period with step
            #span_tau_0 = np.linspace(0,self.span_0,self.step_0)
            #self.tau = _norm_tau[0] + span_tau_0[0:int(self.step_0)]
            #for n in range(1,int(self.tau_end/self.period)+1):
            #    delta_tau = np.linspace(self.period*n-self.span/2.0+self.non_uniform_begin,self.period*n+self.span/2.0+self.non_uniform_begin,self.step)
            #    self.tau = np.append(self.tau,delta_tau)
			
			# for Detail measurement of specific range
			span_tau = np.linspace(self.non_uniform_begin, self.non_uniform_begin + self.span, self.step)
			self.tau = np.append(_norm_tau, span_tau)
			self.tau = np.sort(np.unique(self.tau))
                
        #elif self.logscale:
        #   dense_log_tau = np.logspace(np.log10(self.tau_begin), np.log10(self.tau_middle), num=self.dense_step)
        #   normal_log_tau = np.logspace(np.log10(self.tau_middle), np.log10(self.tau_end), num=self.step)
        #   combined_log_tau = np.concatenate((dense_log_tau[:-1], normal_log_tau))
        #   self.tau = np.round(combined_log_tau)
        
        else:
            self.tau = _norm_tau
        
        Pulsed.apply_parameters(self)   

    def generate_sequence(self, rand=False, order=[]):
        tau = self.tau
        laser = self.laser
        wait = self.wait
        t_pi2_x = self.t_pi2_x
        t_pi_x = self.t_pi_x
        t_pi_y = self.t_pi_y
        t_3pi2_x = self.t_3pi2_x
        n_pi = self.n_pi
        n_ref = self.n_ref

        sequence = []
        
        if rand:
            sequence = []
            
            for _type, _ind in order:
                _t = tau[_ind]
                _t_2n_xy = _t / float( n_pi) - (t_pi_y+t_pi_x)/2
                _t_2n_yy = _t / float( n_pi)  - t_pi_y
                _first_t_n = _t / float(2 * n_pi)  - t_pi2_x/2 - t_pi_x/2

                if _type == 0:
                    _sec_mw_t = t_pi2_x
                    _sec_t_n = _t / float(2 * n_pi)  - t_pi2_x/2 - t_pi_x/2
                else:
                    _sec_mw_t = t_3pi2_x
                    _sec_t_n = _t / float(2 * n_pi)  - t_3pi2_x/2 - t_pi_x/2
                '''
				## for xy-n pulse
                sequence.extend ([ (['mw_x'], t_pi2_x), ([], _first_t_n)  ])
                sequence.extend (int(n_pi / 4 - 1) * [ (['mw_x'], t_pi_x), ([], _t_2n_xy), (['mw_y'], t_pi_y), ([], _t_2n_xy)] )
                sequence.extend ([ (['mw_x'], t_pi_x), ([], _t_2n_xy), (['mw_y'], t_pi_y), ([], _t_2n_yy)] )
                sequence.extend (int(n_pi / 4 - 1) * [ (['mw_y'], t_pi_y), ([],_t_2n_xy), (['mw_x'], t_pi_x), ([], _t_2n_xy)] )
                sequence.extend ([ (['mw_y'], t_pi_y), ([], _t_2n_xy), (['mw_x'], t_pi_x), ([], _sec_t_n), (['mw_x'],_sec_mw_t)])
                sequence.extend ([ (['laser', 'aom'], laser), ([], wait)  ])
				'''

				# for xy8-n pulsed
                sequence.extend ([ (['mw_x'], t_pi2_x), ([], _first_t_n)  ])
                sequence.extend (int(n_pi -1 ) * [ (['mw_x'], t_pi_x), ([], _t_2n_xy), (['mw_y'], t_pi_y), ([], _t_2n_xy), (['mw_x'], t_pi_x), ([], _t_2n_xy), (['mw_y'], t_pi_y), ([], _t_2n_yy),
                                			       (['mw_y'], t_pi_y), ([], _t_2n_xy), (['mw_x'], t_pi_x), ([], _t_2n_xy), (['mw_y'], t_pi_y), ([], _t_2n_xy), (['mw_x'], t_pi_x), ([], _t_2n_xx)])

                sequence.extend ([ (['mw_x'], t_pi_x), ([], _t_2n_xy), (['mw_y'], t_pi_y), ([], _t_2n_xy), (['mw_x'], t_pi_x), ([], _t_2n_xy), (['mw_y'], t_pi_y), ([], _t_2n_yy),
                                   (['mw_y'], t_pi_y), ([], _t_2n_xy), (['mw_x'], t_pi_x), ([], _t_2n_xy), (['mw_y'], t_pi_y), ([], _t_2n_xy), (['mw_x'], t_pi_x), ([], _sec_t_n)])
                sequence.extend ([ (['mw_x'],_sec_mw_t)  ])
                sequence.extend ([ (['laser', 'aom'], laser), ([], wait)  ])
				
                
                """
                sequence.extend([ (['mw_x'], t_pi2_x), ([],_t_n ) ])
                sequence.extend((n_pi - 1) * [ (['mw_y'], t_pi_y), ([], _t_2n) ])
                sequence.extend([ (['mw_y'], t_pi_y), ([], _sec_t_n ) ])
                sequence.extend([ (['mw_x'], _sec_mw_t) ])
                sequence.extend([ (['laser', 'aom'], laser), ([], wait) ])
                """
                # ---  for phase check  ---#
                #sequence.extend([ (['mw_x'], t_pi2_x) ])
                #sequence.extend([ (['mw_y'], _t) ])
                #sequence.extend([ (['mw_x'], _sec_mw_t) ])
                #sequence.extend([ (['laser', 'aom'], laser), ([], wait) ])
                
        else:
            _3pi2_sequence = []
            for t in tau:
                _t_n = t / float(2 * n_pi)  - t_pi2_x/2 - t_pi_y/2
                _t_2n = t / float( n_pi) - t_pi_y
                _t_n_3pi2 = t / float(2 * n_pi)  - t_3pi2_x/2 - t_pi_y/2
                
                sequence.extend([ (['mw_x'], t_pi2_x), ([], _t_n ) ])
                sequence.extend((n_pi - 1) * [ (['mw_y'], t_pi_y), ([], _t_2n ) ])
                sequence.extend([ (['mw_y'], t_pi_y), ([], _t_n ) ])
                sequence.extend([ (['mw_x'], t_pi2_x) ])
                sequence.extend([ (['laser', 'aom'], laser), ([], wait) ])
                
                _3pi2_sequence.extend([ (['mw_x'], t_pi2_x), ([], _t_n ) ])
                _3pi2_sequence.extend((n_pi - 1) * [ (['mw_y'], t_pi_y), ([], _t_2n) ])
                _3pi2_sequence.extend([ (['mw_y'], t_pi_y), ([], _t_n_3pi2 ) ])
                _3pi2_sequence.extend([ (['mw_x'], t_3pi2_x) ])
                _3pi2_sequence.extend([ (['laser', 'aom'], laser), ([], wait) ])

            sequence.extend(_3pi2_sequence)

        sequence.extend(n_ref * [ (['laser', 'aom'], laser), ([], wait) ])
        sequence.extend(n_ref * [ (['mw_y'], t_pi_y), (['laser', 'aom'], laser), ([], wait) ])
            
        sequence.append((['sequence'], 100))

        return sequence

    def _run(self):
        """Acquire data."""

        try: # try to run the acquisition from start_up to shut_down
            self.state = 'run'
            self.apply_parameters()
            if self.run_time >= self.stop_time:
                logging.getLogger().debug('Runtime larger than stop_time. Returning')
                self.state = 'done'
                return

            self.count_data = self.old_count_data

            self.start_up()
            PulseGenerator().Night()

            #tagger_0 = TimeTagger.Pulsed(int(self.n_bins), int(np.round(self.bin_width * 1000)), int(self.n_laser), Int(0), Int(2), Int(3))
            #tagger_1 = TimeTagger.Pulsed(self.n_bins, int(np.round(self.bin_width * 1000)), self.n_laser, Int(1), Int(2), Int(3))
            
            tagger_0 = TimeTagger.Pulsed(self.n_bins, int(np.round(self.bin_width * 1000)), self.n_laser, 0, 2, 3)
            tagger_1 = TimeTagger.Pulsed(self.n_bins, int(np.round(self.bin_width * 1000)), self.n_laser, 1, 2, 3)

            if not self.randomize:
                _sequence = self.sequence
                PulseGenerator().Sequence(_sequence)
            else:
                _len = self.tau.size

            if PulseGenerator().checkUnderflow():
                logging.getLogger().info('Underflow in pulse generator.')
                PulseGenerator().Night()
                if not self.randomize:
                    PulseGenerator().Sequence(_sequence)

            while self.run_time < self.stop_time:
                start_time = time.time()

                if self.randomize:
                    _rand_mapping = list( zip( [0] * _len, range(0, _len) )) + list( zip( [1] * _len, range(0, _len) ))
                    random.shuffle(_rand_mapping)
                    _sequence = self.generate_sequence(True, _rand_mapping)

                    PulseGenerator().Sequence(_sequence)
					

                    tagger_0.clear()
                    tagger_1.clear()

                if PulseGenerator().checkUnderflow():
                    logging.getLogger().info('Underflow in pulse generator.')
                    PulseGenerator().Night()
                    if self.randomize:
                        _rand_mapping = list( zip( [0] * _len, range(0, _len) )) + list( zip( [1] * _len, range(0, _len) ))
                        random.shuffle(_rand_mapping)
                        _sequence = self.generate_sequence(True, _rand_mapping)
                        PulseGenerator().Sequence(_sequence)
                        tagger_0.clear()
                        tagger_1.clear()
                    else:
                        PulseGenerator().Sequence(_sequence)

                if self.randomize:
                    self.thread.stop_request.wait(self.randomize_interval)
                else:
                    self.thread.stop_request.wait(1)

                currentcountdata0 = tagger_0.getData() 
                currentcountdata1 =  tagger_1.getData()
                currentcountdata = currentcountdata1 + currentcountdata0

                if self.randomize:
                    sorted_data = np.zeros((_len * 2, self.n_bins))
                    for _old_ind, _mapping in enumerate(_rand_mapping):
                        _pos = _mapping[1] + _mapping[0] * _len

                        logging.getLogger().debug('Data Insertion Position : ' + str(_pos))

                        sorted_data[_pos] = currentcountdata[_old_ind]

                    self.count_data[:_len * 2] += sorted_data

                    if self.n_ref:
                        self.count_data[- self.n_ref * 2:] += currentcountdata[- self.n_ref * 2:]

                    self.trait_property_changed('count_data', self.count_data)

                else:
                    self.count_data = self.old_count_data + currentcountdata

                self.run_time += time.time() - start_time

                if self.thread.stop_request.isSet():
                    logging.getLogger().debug('Caught stop signal. Exiting.')
                    break

            if self.run_time < self.stop_time:
                self.state = 'idle'
            else:
                self.state = 'done'

            del tagger_0
            del tagger_1

            self.shut_down()

        except: # if anything fails, log the exception and set the state
            logging.getLogger().exception('Something went wrong in pulsed loop.')
            self.state = 'error'

    traits_view = View(\
        VGroup(\
            HGroup(\
                Item('submit_button', show_label=False),
                Item('remove_button', show_label=False),
                Item('resubmit_button', show_label=False),
                Item('priority'),
                Item('state', style='readonly'),
                Item('run_time', style='readonly', format_str='%.f'),
                Item('stop_time'),
            ),
            Tabbed(\
                VGroup(\
                    HGroup(\
                        Item('frequency', width= -80, enabled_when='state != "run"'),
                        Item('power', width= -80, enabled_when='state != "run"'),
                    ),
                    HGroup(\
                        Item('t_pi2_x', width= -80, enabled_when='state != "run"'),
                        Item('t_pi_y', width= -80, enabled_when='state != "run"'),
                        Item('t_pi_x', width= -80, enabled_when='state != "run"'),
                        Item('t_3pi2_x', width= -80, enabled_when='state != "run"'),
                        Item('n_pi', width= -80, enabled_when='state != "run"'),
                        Item('n_ref', width= -80, enabled_when='state != "run"'),
                    ),
                    HGroup(\
                        Item('tau_begin', width= -80, enabled_when='state != "run"'),
                        Item('tau_end', width= -80, enabled_when='state != "run"'),
                        Item('tau_delta', width= -80, enabled_when='state != "run"'),
                    ),
                    HGroup(\
                        Item('non_uniform', enabled_when='state != "run"'),
                        Item('non_uniform_begin', width=-80, enabled_when='state != "run"'),
                        Item('period', width=-80, enabled_when='state != "run"'),
                        Item('span', width=-80, enabled_when='state != "run"'),
                        Item('step', width=-80, enabled_when='state != "run"'),
                    ),
                    HGroup(\
                        Item('span_0', width=-80, enabled_when='state != "run"'),
                        Item('step_0', width=-80, enabled_when='state != "run"'),
                    ),
                    label='Parameters'
                ),
                VGroup(\
                    HGroup(\
                        Item('laser', width= -80, enabled_when='state != "run"'),
                        Item('wait', width= -80, enabled_when='state != "run"'),
                        Item('record_length', width= -80, enabled_when='state != "run"'),
                        Item('bin_width', width= -80, enabled_when='state != "run"'),
                    ),
                    label='Settings'
                ),
                VGroup(\
                    HGroup(\
                        Item('randomize', width=-80, enabled_when='state != "run"'),
                        Item('randomize_interval', width=-80, enabled_when='state != "run"'),
                    ),
                    label='Others'
                ),
            ),
        ),
        title='XY8',
    )

    get_set_items = Rabi.get_set_items + ['t_pi2_x', 't_pi_y', 't_pi_x','t_3pi2_x', 'n_pi', 'n_ref', 'non_uniform', 'period','span','step','non_uniform_begin','span_0','step_0']
