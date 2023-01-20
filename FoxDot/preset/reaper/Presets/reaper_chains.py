from FoxDot.lib.Extensions.ReaperIntegration import init_reapy_project, ReaperInstrumentFactory

old_style_presets = {}

reaproject = init_reapy_project()
reainstru_factory = ReaperInstrumentFactory(old_style_presets, reaproject)
#reaper_instruments = reainstru_factory.create_all_facades_from_reaproject_tracks()

def add_chains(*args, scan_all_params=True, is_chain=True):
    facades = []
    for chain in args:
        try:
            facade = reainstru_factory.add_instrument(chain, chain, scan_all_params=scan_all_params, is_chain=is_chain)
        except e:
            print(f"Error adding chain {chain}: {e}")
        if facade:
            facades.append(facade)
    return tuple([facade.out for facade in facades])