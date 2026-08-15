"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { SubmissionProbe } from "@/lib/types";

/** Seconds the student has to gather their thoughts after hearing the question. */
const THINKING_SECONDS = 10;
/** Maximum seconds of spoken answer; the transcript is sent when this runs out. */
const ANSWER_SECONDS = 30;

type Phase = "ready" | "listening" | "thinking" | "speaking" | "typing";

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
  onAnswer: (answer: string) => Promise<void>;
  probe: SubmissionProbe;
  submissionId: string;
}

export function ProbeStep({ busy, onAnswer, probe, submissionId }: Props) {
  const [phase, setPhase] = useState<Phase>("ready");
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [note, setNote] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const phaseRef = useRef<Phase>(phase);
  const sentRef = useRef(false);
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

  function beginThinking() {
    if (phaseRef.current === "thinking") return;
    setPhase("thinking");
    setSecondsLeft(THINKING_SECONDS);
  }

  function fallBackToTyping(reason: string) {
    stopRecognition();
    setNote(reason);
    setPhase("typing");
  }

  function beginSpeaking() {
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
      for (let index = 0; index < event.results.length; index += 1) {
        heard += event.results[index][0].transcript;
      }
      setTranscript(heard.trim());
    };
    recognition.onerror = (event) => {
      if (["not-allowed", "service-not-allowed", "audio-capture"].includes(event.error)) {
        fallBackToTyping("The microphone is not available, so type your answer instead.");
      }
    };
    // Chrome ends recognition after short silences; keep listening for the whole window.
    recognition.onend = () => {
      if (phaseRef.current === "speaking" && recognitionRef.current === recognition) {
        try {
          recognition.start();
        } catch {
          fallBackToTyping("Listening stopped unexpectedly, so type your answer instead.");
        }
      }
    };
    recognitionRef.current = recognition;
    recognition.start();
    setPhase("speaking");
    setSecondsLeft(ANSWER_SECONDS);
  }

  function send(answer: string) {
    if (sentRef.current) return;
    sentRef.current = true;
    // On success the parent unmounts this step; if marking fails the guard is
    // released so the answer can simply be sent again.
    void onAnswer(answer).finally(() => {
      sentRef.current = false;
    });
  }

  function finishSpeaking(spoken: string) {
    stopRecognition();
    const answer = spoken.trim();
    // Kept visible in the typing phase so a failed marking call can be resent,
    // and so an unheard answer can be typed instead.
    setPhase("typing");
    if (!answer) {
      setNote("Nothing was heard, so type your answer instead.");
      return;
    }
    setNote(null);
    send(answer);
  }

  function askTheQuestion() {
    // Surface the microphone prompt now, not mid-answer when the clock is running.
    navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((stream) => stream.getTracks().forEach((track) => track.stop()))
      .catch(() => undefined);
    const audio = audioRef.current;
    if (!audio) {
      beginThinking();
      return;
    }
    setPhase("listening");
    audio.play().catch(() => beginThinking());
  }

  // One clock for both timed phases. The transition at zero happens here so a
  // re-render can never skip it.
  useEffect(() => {
    if (phase !== "thinking" && phase !== "speaking") return;
    const timer = setInterval(() => {
      setSecondsLeft((current) => (current > 0 ? current - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [phase]);

  useEffect(() => {
    if (secondsLeft > 0) return;
    if (phase === "thinking") beginSpeaking();
    if (phase === "speaking") finishSpeaking(transcript);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsLeft, phase]);

  useEffect(() => {
    return () => {
      stopRecognition();
      audioRef.current?.pause();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function sendTyped() {
    const answer = transcript.trim();
    if (!answer) {
      setNote("Say or type at least a sentence, so the answer can be marked.");
      return;
    }
    send(answer);
  }

  return (
    <>
      <div className="page-head">
        <p className="u-label">One question</p>
        <h1 className="u-display">About your own reasoning</h1>
      </div>

      {/* preload="auto" so the narration is generated while the student reads the intro */}
      <audio
        onEnded={beginThinking}
        onError={beginThinking}
        preload="auto"
        ref={audioRef}
        src={api.probeAudioUrl(submissionId)}
      />

      {phase === "ready" && (
        <>
          <div className="alert alert-info" role="note">
            <p>
              You will hear one question about your own work. After it is read out, you have ten
              seconds to think, and then thirty seconds to speak your answer aloud.
            </p>
          </div>
          <div className="mark-actions">
            <button className="btn btn-primary" onClick={askTheQuestion} type="button">
              I am ready — ask the question
            </button>
          </div>
        </>
      )}

      {phase !== "ready" && (
        <div className="probe-card">
          <p>{probe.question}</p>
          <p className="probe-quote">“{probe.quoted_span}”</p>
        </div>
      )}

      {phase === "listening" && <p className="u-muted">Listen to the question.</p>}

      {phase === "thinking" && (
        <div className="probe-timer-block">
          <p className="u-label">Think about your answer</p>
          <p className="probe-timer u-mono">{secondsLeft}</p>
        </div>
      )}

      {phase === "speaking" && (
        <>
          <div className="probe-timer-block">
            <p className="u-label">Speak now — your answer is being written down</p>
            <p className="probe-timer u-mono">{secondsLeft}</p>
          </div>
          <div className="probe-transcript" aria-live="polite">
            {transcript || "Waiting to hear you…"}
          </div>
          <div className="mark-actions">
            <button
              className="btn btn-primary"
              disabled={busy}
              onClick={() => finishSpeaking(transcript)}
              type="button"
            >
              Send answer now
            </button>
          </div>
        </>
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
              onChange={(event) => setTranscript(event.target.value)}
              rows={5}
              value={transcript}
            />
          </div>
          <div className="mark-actions">
            <button className="btn btn-primary" disabled={busy} onClick={sendTyped} type="button">
              {busy ? "Marking…" : "Send answer"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
