from enum import Enum
from typing import Tuple, Union, Optional, Dict, List

from FoxDot.lib.TimeVar import TimeVar
from pprint import pformat
import reapy

class ReaTrackType(Enum):
    INSTRUMENT = 1
    BUS = 2

def make_snake_name(name: str) -> str:
    return name.lower().replace(' ', '_').replace('/', '_').replace('(', '_').replace(':', '_').replace('__','_').replace('-','_')

def split_param_name(name) -> Tuple[str, str]:
    if name == make_snake_name(name):
        splitted = name.split('_')
        reaobject_name = splitted[0]
        param_name = '_'.join(splitted[1:])
        return reaobject_name, param_name
    else:
        raise KeyError("Parameter name not snake_case :" + name)

class ReaTask(object):
    def __init__(self, type, reaper_object, param_name, param_value):
        self.id = id(self)
        self.type = type
        self.reaper_object = reaper_object
        self.param_name = param_name
        self.param_value = param_value
        self.result = None

class ReaParamState(Enum):
    NORMAL = 0
    VAR1 = 1
    VAR2 = 2

class ReaParam(object):
    def __init__(self, name, value, index=None, state=ReaParamState.NORMAL):
        self.name = name
        self.index = index
        self.value = value
        self.state: ReaParamState = state

class ReaSend(ReaParam):
    def __repr__(self):
        return "<ReaSend {}>".format(self.name)

class ReaTrack(object):
    def __init__(self, clock, track: reapy.Track, name: str, type: ReaTrackType, reaproject):
        self._clock = clock
        self.track = track
        self.reaproject = reaproject
        self.name = name
        self.type = type
        self.reafxs = {}
        self.firstfx = None
        self.reaparams: Dict[str, ReaSend] = {}
        for index, send in enumerate(self.track.sends):
            name = make_snake_name(send.dest_track.name)[1:]
            if name =="mixer":
                self.reaparams["vol"] = ReaSend(name=name, index=index, value=send.volume*2)
            else:
                self.reaparams[name] = ReaSend(name=name, index=index, value=send.volume)
        for index, fx in enumerate(self.track.fxs):
            snake_name = make_snake_name(fx.name)
            if index == 0 and self.firstfx is None:
                self.firstfx = snake_name
            if snake_name not in self.reafxs.keys():
                reafx = ReaFX(fx, snake_name, index)
                self.reafxs[snake_name] = reafx
            elif isinstance(self.reafxs[snake_name], ReaFXGroup):
                self.reafxs[snake_name].add_fx(fx, index)
            else:
                old_reafx = self.reafxs[snake_name]
                reafxgroup = ReaFXGroup([old_reafx.fx, fx], snake_name, [old_reafx.index, index])
                self.reafxs[snake_name] = reafxgroup

    def __repr__(self):
        return "<ReaTrack {} - {}>".format(self.name, pformat(self.reafxs))

    def get_param(self, full_name):
        if full_name in self.reaparams.keys():
            return self.reaparams[full_name].value
        else:
            fx_name, param_name = split_param_name(full_name)
            return self.reafxs[fx_name].reaparams[param_name].value

    def get_all_params(self):
        result = {send.name: send.value for send in self.reaparams.values()}
        for reafx in self.reafxs.values():
            result = result | reafx.get_all_params()
        return result

    def set_param(self, name, value):
        # if name == "mixer":
        #     name = "vol"
        # name = "vol" if name =="mixer" else name
        # value = value/2 if name =="vol" else value
        self.reaparams[name].value = value

    def set_param_direct(self, name, value):
        value = value/2 if name =="vol" else value
        param = self.reaparams[name]
        self.track.sends[param.index].volume = 5*float(value)**2.5 # convert vol logarithmic value to linear 0 -> 1 value




class ReaFX(object):
    def __init__(self, fx, name, index):
        self.fx = fx
        self.name = name
        self.index = index
        self.reaparams: Dict[str, ReaParam] = {}
        for index, param in enumerate(fx.params):
            snake_name = make_snake_name(param.name)
            self.reaparams[snake_name] = ReaParam(name=snake_name, value=param.real, index=index)

    def __repr__(self):
        return "<ReaFX {}>".format(self.name)

    def get_all_params(self):
        return {self.name + "_" + param.name : param.value for param in self.reaparams.values()}

    def get_param(self, name):
        return self.reaparams[name].value

    def set_param(self, name, value):
        self.reaparams[name].value = value

    def set_param_direct(self, name, value):
        id = self.reaparams[name].index
        self.fx.params[id] = float(value)


class ReaFXGroup(ReaFX):
    def __init__(self, fxs: List[reapy.FX], name, indexes:List[int]):
        self.fxs = fxs
        self.name = name
        self.indexes = indexes
        self.reaparams: Dict[str, ReaParam] = {}
        for index, param in enumerate(fxs[0].params):
            snake_name = make_snake_name(param.name)
            self.reaparams[snake_name] = ReaParam(name=snake_name, value=param.real, index=index)

    def add_fx(self, fx:reapy.FX, index):
        self.fxs.append(fx)
        self.indexes.append(index)

    def __repr__(self):
        return "<ReaFXGroup {}>".format(self.name)

    def set_param_direct(self, name, value):
        id = self.reaparams[name].index
        for fx in self.fxs:
            fx.params[id] = float(value)


class ReaProject(object):
    def __init__(self, clock):
        self._clock = clock
        self.reapy_project = reapy.Project()
        self.reatracks = {}
        self.instrument_tracks = []
        self.bus_tracks = []
        self.reapy_access_tasks = []
        self.reapy_access_queue_size = 200
        self.reapy_task_execute_freq = 0.1
        self.reapy_results_by_id = {}
        self.currently_processing_tasks = False
        with reapy.inside_reaper():
            for index, track in enumerate(self.reapy_project.tracks):
                snake_name: str = make_snake_name(track.name)
                reatrack = ReaTrack(self._clock, track, name=snake_name, type=ReaTrackType.INSTRUMENT, reaproject=self)
                self.reatracks[snake_name] = reatrack
                if snake_name.startswith('_'):
                    self.bus_tracks.append(reatrack)
                else:
                    self.instrument_tracks.append(reatrack)

    def __repr__(self):
        return "<ReaProject \n\n ################ \n\n {}>".format(self.reatracks)

    def get_track(self, track_name):
        return self.reatracks[track_name]

    def add_reapy_task(self, task: ReaTask):
        if len(self.reapy_access_tasks) < self.reapy_access_queue_size:
            self.reapy_access_tasks.append(task)
            if not self.currently_processing_tasks:
                self._clock.future(self.reapy_task_execute_freq, self.execute_reapy_tasks, args=[])
        else:
            print("maximum reapy tasks in queue reached")

    def execute_reapy_tasks(self):
        if not self.currently_processing_tasks:
            self.currently_processing_tasks = True
            with reapy.inside_reaper():
                while self.reapy_access_tasks:
                    task: ReaTask = self.reapy_access_tasks.pop(0)
                    if task.type == "set":
                        task.reaper_object.set_param_direct(task.param_name, task.param_value)
                        task.reaper_object.set_param(task.param_name, task.param_value)
            self.currently_processing_tasks = False
            self._clock.future(self.reapy_task_execute_freq, self.execute_reapy_tasks, args=[])

    def timevar_update_loop(self, rea_object, name, value, state, update_freq):
        if rea_object.reaparams[name].state == state:
            self.add_reapy_task(ReaTask("set", rea_object, name, value))
            self._clock.future(update_freq, self.timevar_update_loop, args=[rea_object, name, value, state, update_freq])

def get_reaper_object_and_param_name(track: ReaTrack, param_fullname: str, quiet: bool = True)\
        -> Tuple[Optional[Union[ReaTrack, ReaFX]], Optional[str]]:
    """
    Return object (ReaTrack or ReaFX) and parameter name to apply modification to.
    Choose usecase (parameter kind : track param like vol, send amount or fx param) depending on parameter name.
    """
    reaper_object, param_name = None, None
    # Param concern current track
    if param_fullname in track.reaparams.keys():
        reaper_object = track
        return reaper_object, param_fullname
    # Param is a fx param
    elif '_' in param_fullname:
        fx_name, rest = split_param_name(param_fullname)
        if fx_name in track.reafxs.keys():
            fx = track.reafxs[fx_name]
            if rest in fx.reaparams.keys() or rest == 'on':
                reaper_object = track.reafxs[fx_name]
                param_name = rest
                return reaper_object, param_name
    elif param_fullname in track.reafxs[track.firstfx].reaparams.keys(): # Try to match param name with first fx params
        reaper_object = track.reafxs[track.firstfx]
        return reaper_object, param_fullname
    if not quiet:
        print("Parameter doesn't exist: " + param_fullname)
    return reaper_object, param_name


def set_reaper_param(track: ReaTrack, full_name, value, update_freq=0.05):
    # fx can point to a fx or a track (self) -> (when param is vol or pan)
    rea_object, name = get_reaper_object_and_param_name(track, full_name)
    if rea_object is None or name is None:
        return
    if name == "on":
        # TODO: wrong way to do fx disabling this doesn't work -> put it in set_param_direct method
        def fx_enable(rea_object, name, value):
            if not value:
                rea_object.disable()
            else:
                rea_object.enable()
            return
        track._clock.schedule(fx_enable, beat=None, args=[rea_object, name, value])
    elif isinstance(value, TimeVar) and name != 'on':
        # to update a time varying param and tell the preceding recursion loop to stop
        # we switch between two timevar state old and new alternatively 'timevar1' and 'timevar2'
        if rea_object.reaparams[name].state != ReaParamState.VAR1:
            new_state = ReaParamState.VAR1
        else:
            new_state = ReaParamState.VAR2
        def initiate_timevar_update_loop(name, value, new_state, update_freq):
            rea_object.reaparams[name].state = new_state
            track.reaproject.timevar_update_loop(rea_object, name, value, new_state, update_freq)
        # beat=None means schedule for the next bar
        track._clock.schedule(initiate_timevar_update_loop, beat=None, args=[name, value, new_state, update_freq])
    else:
        # to switch back to non varying value use the state normal to make the recursion loop stop
        def normal_value_update(rea_object, name, value):
            rea_object.reaparams[name].state = ReaParamState.NORMAL
            rea_object.set_param(name, float(value))
            track.reaproject.add_reapy_task(ReaTask("set", rea_object, name, float(value)))
        # beat=None means schedule for the next bar
        track._clock.schedule(normal_value_update, beat=None, args=[rea_object, name, value])

def get_reaper_param(self, full_name):
    # rea_object can point to a fx or a track (self) -> (when param is vol or pan)
    rea_object, name = get_reaper_object_and_param_name(self, full_name)
    if rea_object is None or name is None:
        return None
    return rea_object.get_param(full_name)