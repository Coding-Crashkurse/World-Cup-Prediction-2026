// Lightweight broadcast SFX, synthesized with the Web Audio API — no asset
// files, no licensing. Everything is a no-op until ensure() runs inside a user
// gesture (browser autoplay policy) and while muted.

class SoundEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private muted = true;

  ensure(): void {
    if (!this.ctx) {
      const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return;
      this.ctx = new Ctor();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.muted ? 0 : 0.9;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === "suspended") void this.ctx.resume();
  }

  setMuted(muted: boolean): void {
    this.muted = muted;
    if (this.ctx && this.master) {
      this.master.gain.setTargetAtTime(muted ? 0 : 0.9, this.ctx.currentTime, 0.03);
    }
  }

  private ready(): boolean {
    return !!this.ctx && !!this.master && !this.muted;
  }

  private noiseBuffer(seconds: number): AudioBuffer {
    const ctx = this.ctx!;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * seconds), ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    return buf;
  }

  // Soft "pock" on a played match.
  kick(): void {
    if (!this.ready()) return;
    const ctx = this.ctx!;
    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(170, t);
    osc.frequency.exponentialRampToValueAtTime(90, t + 0.12);
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.16, t + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.16);
    osc.connect(gain).connect(this.master!);
    osc.start(t);
    osc.stop(t + 0.18);
  }

  // Short data blip for Monte-Carlo frames; pitch rises with convergence.
  tick(progress = 0): void {
    if (!this.ready()) return;
    const ctx = this.ctx!;
    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.value = 320 + progress * 680;
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.05, t + 0.005);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
    osc.connect(gain).connect(this.master!);
    osc.start(t);
    osc.stop(t + 0.1);
  }

  // Whoosh stinger on stage changes.
  whoosh(): void {
    if (!this.ready()) return;
    const ctx = this.ctx!;
    const t = ctx.currentTime;
    const src = ctx.createBufferSource();
    src.buffer = this.noiseBuffer(0.7);
    const band = ctx.createBiquadFilter();
    band.type = "bandpass";
    band.frequency.setValueAtTime(350, t);
    band.frequency.exponentialRampToValueAtTime(2400, t + 0.45);
    band.Q.value = 0.8;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.28, t + 0.18);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.6);
    src.connect(band).connect(gain).connect(this.master!);
    src.start(t);
    src.stop(t + 0.7);
  }

  private chord(freqs: number[], t0: number, dur: number, peak: number): void {
    const ctx = this.ctx!;
    for (const f of freqs) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.value = f;
      gain.gain.setValueAtTime(0.0001, t0);
      gain.gain.exponentialRampToValueAtTime(peak, t0 + 0.08);
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      osc.connect(gain).connect(this.master!);
      osc.start(t0);
      osc.stop(t0 + dur + 0.05);
    }
  }

  // Short triumphant chord (Monte-Carlo finished).
  fanfare(): void {
    if (!this.ready()) return;
    const t = this.ctx!.currentTime;
    this.chord([392, 494, 587], t, 0.5, 0.12); // G major
    this.chord([523, 659, 784], t + 0.18, 0.7, 0.13); // C major
  }

  // Crowd swell + rising chord for the champion reveal.
  cheer(): void {
    if (!this.ready()) return;
    const ctx = this.ctx!;
    const t = ctx.currentTime;
    const src = ctx.createBufferSource();
    src.buffer = this.noiseBuffer(2.0);
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.setValueAtTime(500, t);
    lp.frequency.exponentialRampToValueAtTime(3200, t + 1.2);
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.3, t + 0.8);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 1.9);
    src.connect(lp).connect(gain).connect(this.master!);
    src.start(t);
    src.stop(t + 2.0);
    this.chord([523, 659, 784, 1047], t + 0.4, 1.4, 0.12); // C major triad + octave
  }
}

export const sound = new SoundEngine();
