"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { SubmissionExchange } from "@/lib/types";

/** A pause this long, after something has been said, ends the answer on its own. */
const SILENCE_MS = 2200;
/** Total silence from the start for this long falls back to a typed answer. */
const NO_SPEECH_MS = 12000;
/** Hard stop, so an answer can never run on forever. */
const MAX_ANSWER_MS = 60000;

type Phase = "ready" | "asking" | "listening" | "waiting" | "typing";

/* The Web Speech API is not in TypeScript's DOM lib, so the shape used here is
   declared locally — only the members this component touches. */
interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onresult: ((event: SpeechResultEventLike) => void) | null;
  start: () => void;
  stop: () => void;
}

interface SpeechResultEventLike {
  results: {
    length: number;
    [index: number]: { isFinal: boolean; 0: { transcript: string } };
  };
}

function recognitionConstructor(): (new () => SpeechRecognitionLike) | null {
  const scope = window as unknown as Record<string, unknown>;
  const found = scope.SpeechRecognition ?? scope.webkitSpeechRecognition;
  return typeof found === "function" ? (found as new () => SpeechRecognitionLike) : null;
}

interface Props {
  busy: boolean;
  exchange: SubmissionExchange;
  index: number;
  onAnswer: (answer: string) => Promise<void>;
  questionLimit: number;
  submissionId: string;
}

/* Mounted once per question — the parent keys this component by the exchange index,
   so every new question starts the ask-then-listen cycle afresh. There are no
   buttons mid-conversation: a short pause is what ends an answer. */
export function ProbeStep({ busy, exchange, index, onAnswer, questionLimit, submissionId }: Props) {
  const [phase, setPhase] = useState<Phase>("ready");
  const [note, setNote] = useState<string | null>(null);
  // Only the typed fallback renders this; while speaking, nothing is shown.
  const [draft, setDraft] = useState("");

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const orbRef = useRef<HTMLDivElement | null>(null);
  const phaseRef = useRef<Phase>(phase);
  const sentRef = useRef(false);
  // What the microphone heard, kept in refs so the silence watchdog always reads
  // the current values. Deliberately never rendered while speaking.
  const transcriptRef = useRef("");
  const lastHeardRef = useRef(0);
  const listenStartRef = useRef(0);
  const meterStopRef = useRef<(() => void) | null>(null);
  const thinkingRef = useRef<HTMLAudioElement | null>(null);
  phaseRef.current = phase;

  function stopRecognition() {
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    if (recognition) {
      recognition.onend = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.stop();
    }
  }

  function stopMeter() {
    meterStopRef.current?.();
    meterStopRef.current = null;
  }

  function fallBackToTyping(reason: string) {
    stopRecognition();
    stopMeter();
    setNote(reason);
    setDraft(transcriptRef.current.trim());
    setPhase("typing");
  }

  // Drives the orb from the real microphone level, so it visibly reacts to the
  // student's own voice. Losing the meter is harmless — the orb just sits still.
  async function startMeter() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new AudioContext();
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      let frame = 0;
      const draw = () => {
        analyser.getByteTimeDomainData(samples);
        let sum = 0;
        for (let position = 0; position < samples.length; position += 1) {
          const centred = (samples[position] - 128) / 128;
          sum += centred * centred;
        }
        const level = Math.min(1, Math.sqrt(sum / samples.length) * 4);
        orbRef.current?.style.setProperty("--level", level.toFixed(3));
        frame = requestAnimationFrame(draw);
      };
      frame = requestAnimationFrame(draw);
      meterStopRef.current = () => {
        cancelAnimationFrame(frame);
        stream.getTracks().forEach((track) => track.stop());
        void context.close();
      };
    } catch {
      // No meter, no reaction — the conversation itself is unaffected.
    }
  }

  function beginListening() {
    if (phaseRef.current === "listening") return;
    const Recognition = recognitionConstructor();
    if (!Recognition) {
      fallBackToTyping("Speech input is not available in this browser, so type your answer instead.");
      return;
    }
    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-GB";
    recognition.onresult = (event) => {
      let heard = "";
      for (let position = 0; position < event.results.length; position += 1) {
        heard += event.results[position][0].transcript;
      }
      transcriptRef.current = heard.trim();
      lastHeardRef.current = Date.now();
    };
    recognition.onerror = (event) => {
      if (["not-allowed", "service-not-allowed", "audio-capture"].includes(event.error)) {
        fallBackToTyping("The microphone is not available, so type your answer instead.");
      }
    };
    // Chrome ends recognition after short silences; keep listening — the silence
    // watchdog, not the recogniser, decides when the answer is over.
    recognition.onend = () => {
      if (phaseRef.current === "listening" && recognitionRef.current === recognition) {
        try {
          recognition.start();
        } catch {
          fallBackToTyping("Listening stopped unexpectedly, so type your answer instead.");
        }
      }
    };
    recognitionRef.current = recognition;
    transcriptRef.current = "";
    lastHeardRef.current = 0;
    listenStartRef.current = Date.now();
    recognition.start();
    void startMeter();
    setPhase("listening");
  }

  // A quiet spoken "hmm" while the next question or the mark is decided, so the
  // silence never reads as the app having stopped. Three variants, picked at
  // random; failure to play is ignored.
  function playThinking() {
    const variant = Math.floor(Math.random() * 3);
    const sound = new Audio(api.thinkingAudioUrl(variant));
    sound.volume = 0.55;
    thinkingRef.current = sound;
    void sound.play().catch(() => undefined);
  }

  function send(answer: string) {
    if (sentRef.current) return;
    sentRef.current = true;
    setPhase("waiting");
    playThinking();
    // On success the parent moves to the next question or the mark, which replaces
    // this component; if the call fails the guard is released and the words appear
    // in the typed box so they can simply be sent again.
    void onAnswer(answer).finally(() => {
      sentRef.current = false;
      setDraft(answer);
      setPhase("typing");
    });
  }

  function finishAnswering() {
    if (phaseRef.current !== "listening") return;
    stopRecognition();
    stopMeter();
    const answer = transcriptRef.current.trim();
    if (!answer) {
      setNote("Nothing was heard, so type your answer instead.");
      setPhase("typing");
      return;
    }
    setNote(null);
    send(answer);
  }

  function askTheQuestion() {
    // Surface the microphone prompt now, not mid-answer.
    navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((stream) => stream.getTracks().forEach((track) => track.stop()))
      .catch(() => undefined);
    const audio = audioRef.current;
    if (!audio) {
      beginListening();
      return;
    }
    setPhase("asking");
    audio.play().catch(() => beginListening());
  }

  // Follow-up questions start speaking on their own so the conversation flows; if
  // the browser refuses the unprompted playback, the ready button remains.
  useEffect(() => {
    if (index === 0) return;
    const audio = audioRef.current;
    if (!audio) return;
    setPhase("asking");
    audio.play().catch(() => setPhase("ready"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index]);

  // The silence watchdog: a short pause after something was said ends the answer,
  // long silence from the start falls back to typing, and a hard cap backstops both.
  useEffect(() => {
    if (phase !== "listening") return;
    const timer = setInterval(() => {
      const now = Date.now();
      const saidSomething = transcriptRef.current.length > 0;
      if (saidSomething && lastHeardRef.current && now - lastHeardRef.current >= SILENCE_MS) {
        finishAnswering();
      } else if (!saidSomething && now - listenStartRef.current >= NO_SPEECH_MS) {
        fallBackToTyping("Nothing was heard, so type your answer instead.");
      } else if (now - listenStartRef.current >= MAX_ANSWER_MS) {
        finishAnswering();
      }
    }, 250);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => {
    return () => {
      stopRecognition();
      stopMeter();
      audioRef.current?.pause();
      thinkingRef.current?.pause();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function sendTyped() {
    const answer = draft.trim();
    if (!answer) {
      setNote("Say or type at least a sentence, so the answer can be marked.");
      return;
    }
    send(answer);
  }

  return (
    <>
      <div className="page-head">
        <h1 className="u-display">Question {index + 1}</h1>
        <span className="tag u-mono">of {questionLimit}</span>
      </div>

      {/* preload="auto" so the narration is generated while the student reads the intro */}
      <audio
        onEnded={beginListening}
        onError={beginListening}
        preload="auto"
        ref={audioRef}
        src={api.probeAudioUrl(submissionId, index)}
      />

      {phase === "ready" && (
        <>
          {index === 0 && (
            <div className="alert alert-info" role="note">
              <p>Answer out loud. A pause ends your answer — there is nothing to press.</p>
            </div>
          )}
          <div className="mark-actions">
            <button className="btn btn-primary" onClick={askTheQuestion} type="button">
              {index === 0 ? "Hear the first question" : "Hear the next question"}
            </button>
          </div>
        </>
      )}

      {phase !== "ready" && (
        <div className="probe-card">
          <p>{exchange.question}</p>
          {exchange.quoted_span && <p className="probe-quote">“{exchange.quoted_span}”</p>}
        </div>
      )}

      {(phase === "asking" || phase === "listening" || phase === "waiting") && (
        <div className="orb-stage">
          <div className={`orb is-${phase}`} ref={orbRef} />
          <p className="u-muted" aria-live="polite">
            {phase === "asking" && "Listen…"}
            {phase === "listening" && "Speak your answer. Pause when you have finished."}
            {phase === "waiting" && "One moment…"}
          </p>
        </div>
      )}

      {phase === "typing" && (
        <div className="mark-form">
          {note && (
            <div className="alert alert-info" role="note">
              <p>{note}</p>
            </div>
          )}
          <div className="field">
            <label htmlFor="answer">Your answer</label>
            <textarea
              id="answer"
              onChange={(event) => setDraft(event.target.value)}
              rows={5}
              value={draft}
            />
          </div>
          <div className="mark-actions">
            <button className="btn btn-primary" disabled={busy} onClick={sendTyped} type="button">
              {busy ? "One moment…" : "Send answer"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
