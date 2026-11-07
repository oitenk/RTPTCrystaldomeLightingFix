// RT/PT Crystaldome Lighting Fix
//
// The dark Crystal Dome panels use an effect shader that ray-traced reflections
// look straight through, so the cabin picks up the bright world outside. The
// archive adds an opaque stand-in a few millimetres from each dark panel
// (components "cdlf_*"). This script shows them while the dome is dark
// and hides them while it is see-through, following the game's own dome
// switching (the same way the game toggles the Basilisk's canopy shadow).

// The stand-in names (CDLF_StandInNames) are in StandInNames.reds, written by tools/build_archive.py.
// A car only has the ones for its own panels; the rest are simply not found.

@addMethod(VehicleComponent)
private func CDLF_ShowStandIns(show: Bool) {
    let names = CDLF_StandInNames();
    for name in names {
        let component = this.FindComponentByName(name);
        if IsDefined(component) {
            component.Toggle(show);
        }
    }
}

// Dome on: hide the stand-ins at once, so the see-through look is not blocked.
@wrapMethod(VehicleComponent)
private func ToggleCrystalDome(toggle: Bool, opt force: Bool, opt instant: Bool, opt instantDelay: Float, opt meshVisibilityDelay: Float, opt fastStop: Bool) {
    wrappedMethod(toggle, force, instant, instantDelay, meshVisibilityDelay, fastStop);
    if toggle && this.GetPS().GetCrystalDomeState() {
        this.CDLF_ShowStandIns(false);
    }
}

// Dome off: the game marks the dome dark 0.6 s after the off effect starts; show them then.
@wrapMethod(VehicleComponent)
protected cb func OnVehicleCrystalDomeOffDelayEvent(evt: ref<VehicleCrystalDomeOffDelayEvent>) -> Bool {
    let result = wrappedMethod(evt);
    this.CDLF_ShowStandIns(!this.GetPS().GetCrystalDomeState());
    return result;
}
