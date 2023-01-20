
from typing import Mapping
from pprint import pprint

from FoxDot.lib import Clock, player_method

from .ReaperInstruments import ReaperInstrumentFacade
from FoxDot.lib.Extensions.ReaperIntegrationLib.ReaProject import ReaProject
from FoxDot.lib.Extensions.ReaperIntegrationLib.ReaTrack import ReaTrack

def init_reapy_project():
    project = None
    try:
        import reapy
        project = ReaProject(Clock, reapy)
    except Exception as err:
        output = err.message if hasattr(err, 'message') else err
        print("Error scanning and initializing Reaper project: {output} -> skipping Reaper integration".format(output=output))
    return project

class ReaperInstrumentFactory:

    def __init__(self, presets: Mapping, project: ReaProject) -> None:
        self._presets = presets
        self._reaproject = project
        self.used_track_indexes = []

    def update_used_track_indexes(self):
        for i in range(16):
            if len(self._reaproject.reatracks["chan"+str(i+1)].reafxs) != 0 and i+1 not in self.used_track_indexes:
                self.used_track_indexes.append(i+1)
            elif i+1 in self.used_track_indexes and len(self._reaproject.reatracks["chan"+str(i+1)].reafxs) == 0:
                self.used_track_indexes = [index for index in self.used_track_indexes if index != i+1]

    def create_instrument_facade(self, *args, **kwargs):
        """handle exceptions gracefully especially if corresponding track does not exist in Reaper"""
        try:
            return ReaperInstrumentFacade(self._reaproject, self._presets, *args, **kwargs)
        except Exception as err:
            output = err.message if hasattr(err, 'message') else err
            print("Error creating instruc {name}: {output} -> skipping".format(name=kwargs["track_name"], output=output))
            return None

    def create_all_facades_from_reaproject_tracks(self):
        instrument_dict = {}
        for reatrack in self._reaproject.bus_tracks:
            instrument_dict[reatrack.name[1:]] = self.create_instrument_facade(track_name=reatrack.name, midi_channel=-1)

        for i, track in enumerate(self._reaproject.instrument_tracks):
            if len(track.reafxs.values()) > 0:
                instrument_name = list(track.reafxs.values())[0].name # first fx is the usually the synth/instrument that give the name
            else:
                instrument_name = track.name # if not exist, use the less interesting track name (chan2...)
            instrument_kwargs = {
                "track_name": track.name,
                "midi_channel": i + 1,
            }
            instrument_dict[instrument_name] = self.create_instrument_facade(**instrument_kwargs)
        return instrument_dict

    def add_instrument(self, name, plugin_name, preset=None, params={}, scan_all_params=True, is_chain=True):
        free_indexes = [index for index in range(1,17) if index not in self.used_track_indexes]
        free_index = free_indexes[0]
        if preset is None:
            preset = name
        self.used_track_indexes.append(free_index)
        return self.create_instrument_facade(
            track_name='chan'+str(free_index),
            midi_channel=free_index,
            create_instrument=True,
            instrument_name=name,
            plugin_name=plugin_name,
            plugin_preset=preset,
            instrument_params=params,
            scan_all_params=scan_all_params,
            is_chain=is_chain
        )

@player_method
def setp(self, param_dict):
    for key, value in param_dict.items():
        setattr(self, key, value)

@player_method
def getp(self, filter = None):
    result = None
    if "reatrack" in self.attr.keys():
        reatrack = self.attr["reatrack"][0]
        if isinstance(reatrack, ReaTrack):
            #result = reatrack.config
            if filter is not None:
                result = {key: value for key, value in reatrack.get_all_params().items() if filter in key}
            else:
                result = reatrack.get_all_params()
    return result

@player_method
def showp(self, filter = None):
    pprint(self.getp(filter))