SynthDef.new(\pmcrotal, {
	|bus = 0, freq = 0, atone = 4, btone = 3, atk = 0, sus = 1, rel = 0.9, curve = -7, amp = 1, pan = 0, modLo = 5.25, modHi = 6.5|
	var env, osc1, osc, mod;
	freq = In.kr(bus, 1);
	env = Env.linen(atk, sus, rel, curve: curve).kr(doneAction:0);
	mod = Rand(modLo, modHi);
	osc = PMOsc.ar(freq/2, mod * freq/2, pmindex: atone, mul: 0.5);
	osc1 = PMOsc.ar(freq/4, freq, pmindex: btone, mul: 0.5);
	osc = HPF.ar(osc,freq, mul:0.4);
	osc = Mix.ar([osc,osc1]) * 0.2;
	osc = osc * env * amp;
	osc = Pan2.ar(osc,pan);
	ReplaceOut.ar(bus,osc)
}).add;