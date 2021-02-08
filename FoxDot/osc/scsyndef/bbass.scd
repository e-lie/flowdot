SynthDef(\bbass, {
	|bus=0, freq = 0, amp = 1, pan=0, sus=1, blur=1, fmod=0|
	var env, oscfreq, osc, envout, lfo;
	freq = In.kr(bus, 1);
	sus = sus * blur;
	freq = [freq, freq+fmod];
	oscfreq = {freq * LFNoise2.kr(Rand(0.0001,0.5)).range(0.98, 1.02)}!5;
	lfo = { SinOsc.kr({ 1/Rand(2,52) }!5) };
	env = Env.adsr(0.07, 1, 0.9, 0.1).kr(doneAction:0);
	osc = LFSaw.ar(oscfreq, mul: lfo.value.range(0,1));
	osc = RLPF.ar(osc,(env*freq) + 1*freq * lfo.value.range(10/freq,5/freq), lfo.value.range(0.1,1));
	osc = Splay.ar(osc, lfo.value.range(0,1));
	envout = EnvGen.ar(Env.perc(level: amp,releaseTime: sus,attackTime: 0.02, curve: 'lin'), doneAction: 0);
	osc = Mix(osc) * 0.1 * envout * amp;
	osc = Pan2.ar(osc, pan);
	ReplaceOut.ar(bus,osc);
}).add;