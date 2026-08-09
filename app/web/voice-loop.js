(() => {
  "use strict";

  const DEFAULT_VOICE_CONFIG = Object.freeze({
    silenceTimeoutMs: 2000,
    rmsThreshold: 0.025,
    speechStartTimeoutMs: 10000,
  });

  function nextVadState(previous = {}, sample = {}, config = DEFAULT_VOICE_CONFIG, nowMs = performance.now()) {
    const threshold = Number(config.rmsThreshold);
    const rms = Number(sample.rms) || 0;
    let hasSpeech = Boolean(previous.hasSpeech);
    let silenceStartedAt = previous.silenceStartedAt ?? null;
    const confirmedText = String(sample.confirmedText ?? previous.confirmedText ?? "");
    const exitThreshold = threshold * 0.8;
    const speaking = rms >= (hasSpeech ? exitThreshold : threshold);
    if (speaking) {
      hasSpeech = true;
      silenceStartedAt = null;
    } else if (hasSpeech && silenceStartedAt === null) {
      silenceStartedAt = nowMs;
    }
    const silenceMs = silenceStartedAt === null ? 0 : Math.max(0, nowMs - silenceStartedAt);
    const shouldFinalize = Boolean(
      hasSpeech && confirmedText.trim() && silenceMs >= Number(config.silenceTimeoutMs),
    );
    return {
      hasSpeech,
      silenceStartedAt,
      confirmedText,
      phase: shouldFinalize ? "PROCESSING" : "LISTENING",
      shouldFinalize,
    };
  }

  function rmsFromTimeDomain(data) {
    if (!data?.length) return 0;
    let sum = 0;
    for (let index = 0; index < data.length; index += 1) {
      const sample = (data[index] - 128) / 128;
      sum += sample * sample;
    }
    return Math.sqrt(sum / data.length);
  }

  class VoiceLoopController {
    constructor(options = {}) {
      this.config = { ...DEFAULT_VOICE_CONFIG, ...(options.config || {}) };
      this.onState = options.onState || (() => {});
      this.onPartial = options.onPartial || (() => {});
      this.onFinal = options.onFinal || (() => {});
      this.onEvent = options.onEvent || (() => {});
      this.onError = options.onError || (() => {});
      this.recognitionFactory = options.recognitionFactory || (() => {
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        return Recognition ? new Recognition() : null;
      });
      this.active = false;
      this.paused = false;
      this.finalized = new Set();
      this.state = { hasSpeech: false, silenceStartedAt: null, confirmedText: "" };
      this.stream = null;
      this.audioContext = null;
      this.analyser = null;
      this.frameId = null;
      this.recognition = null;
      this.listenId = null;
      this.clientTurnId = null;
    }

    async start() {
      if (this.active) return;
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("microphone_unavailable");
      if (!this.recognitionFactory()) throw new Error("speech_recognition_unavailable");
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 512;
      source.connect(this.analyser);
      this.active = true;
      this.paused = false;
      this.#createRecognition();
      this.#emitState("LISTENING");
      this.#frame();
    }

    stop() {
      this.active = false;
      this.paused = true;
      if (this.frameId !== null) cancelAnimationFrame(this.frameId);
      this.frameId = null;
      try { this.recognition?.stop(); } catch (_) { /* late browser callback */ }
      this.recognition = null;
      this.stream?.getTracks().forEach((track) => track.stop());
      this.stream = null;
      if (this.audioContext) void this.audioContext.close().catch(() => {});
      this.audioContext = null;
      this.analyser = null;
    }

    pause() {
      this.paused = true;
      try { this.recognition?.stop(); } catch (_) { /* late browser callback */ }
    }

    resume() {
      if (!this.active) return;
      this.paused = false;
      this.state = { hasSpeech: false, silenceStartedAt: null, confirmedText: "" };
      this.#startRecognition();
      this.#emitState("LISTENING");
    }

    toggle() {
      if (this.paused) this.resume();
      else this.pause();
    }

    #createRecognition() {
      this.recognition = this.recognitionFactory();
      if (!this.recognition) throw new Error("speech_recognition_unavailable");
      this.recognition.lang = "es-CO";
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.maxAlternatives = 1;
      this.recognition.onresult = (event) => {
        let interim = "";
        let confirmed = this.state.confirmedText;
        for (let index = event.resultIndex || 0; index < event.results.length; index += 1) {
          const transcript = event.results[index]?.[0]?.transcript || "";
          if (event.results[index]?.isFinal) confirmed = `${confirmed} ${transcript}`.trim();
          else interim += transcript;
        }
        this.state = { ...this.state, confirmedText: confirmed };
        this.onPartial(interim.trim(), confirmed);
      };
      this.recognition.onerror = (event) => this.onError(event?.error || "recognition_error");
      this.recognition.onend = () => {
        if (this.active && !this.paused && this.state.phase !== "PROCESSING") this.#startRecognition();
      };
      this.#startRecognition();
    }

    #startRecognition() {
      if (!this.recognition || !this.active || this.paused) return;
      try { this.recognition.start(); } catch (_) { /* already started */ }
    }

    #frame() {
      if (!this.active || !this.analyser) return;
      const samples = new Uint8Array(this.analyser.fftSize);
      this.analyser.getByteTimeDomainData(samples);
      const next = nextVadState(this.state, { rms: rmsFromTimeDomain(samples) }, this.config, performance.now());
      if (next.hasSpeech && !this.state.hasSpeech) {
        this.listenId = `listen_${crypto.randomUUID?.() || Date.now()}`.slice(0, 128);
        this.clientTurnId = `client_turn_${crypto.randomUUID?.() || Date.now()}`.slice(0, 128);
        this.onEvent("vad_speech_started", {
          listenId: this.listenId,
          clientTurnId: this.clientTurnId,
        });
      }
      if (next.silenceStartedAt !== null && this.state.silenceStartedAt === null) {
        this.onEvent("vad_silence_started", {
          listenId: this.listenId,
          clientTurnId: this.clientTurnId,
        });
      }
      this.state = next;
      if (next.shouldFinalize) this.#finalizeSegment();
      this.frameId = requestAnimationFrame(() => this.#frame());
    }

    #finalizeSegment() {
      const text = this.state.confirmedText.trim();
      if (!text || this.paused) return;
      const listenId = this.listenId || `listen_${crypto.randomUUID?.() || Date.now()}`;
      if (this.finalized.has(listenId)) return;
      this.finalized.add(listenId);
      this.paused = true;
      this.onEvent("vad_segment_finalized", { listenId, clientTurnId: this.clientTurnId });
      try { this.recognition?.stop(); } catch (_) { /* late browser callback */ }
      this.onState("PROCESSING");
      this.onFinal(text, { listenId, clientTurnId: this.clientTurnId });
      this.listenId = null;
      this.clientTurnId = null;
    }

    #emitState(state) {
      this.state = { ...this.state, phase: state };
      this.onState(state);
    }
  }

  window.VoiceLoop = Object.freeze({ DEFAULT_VOICE_CONFIG, VoiceLoopController, nextVadState, rmsFromTimeDomain });
})();
