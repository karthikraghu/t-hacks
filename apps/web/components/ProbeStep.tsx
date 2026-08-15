"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { SubmissionExchange } from "@/lib/types";

/** Maximum seconds of spoken answer; whatever was heard is sent when this runs out. */
const ANSWER_SECONDS = 30;

type Phase = "ready" | "listening" | "answering" | "waiting" | "typing";

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
  submissionId: string;
}

/* Mounted once per question — the parent keys this component by the exchange index,
   so every new question starts the listen-then-answer cycle afresh. */
export function ProbeStep({ busy, exchange, index, onAnswer, submissionId }: Props) {
  const [phase, setPhase] = useState<Phase>("ready");
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [note, setNote] = useState<string | null>(null);
  // What the microphone heard. Deliberately never rendered while speaking: watching
  // your own words appear mid-sentence derails the answer. It only becomes visible
  // in the typed fallback.
  const [transcript, setTranscript] = useState("");

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

  function fallBackToTyping(reason: string) {
    stopRecognition();
    setNote(reason);
    setPhase("typing");
  }

  function beginAnswering() {
    if (phaseRef.current === "answering") return;
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
      setTranscript(heard.trim());
    };
    recognition.onerror = (event) => {
      if (["not-allowed", "service-not-allowed", "audio-capture"].includes(event.error)) {
        fallBackToTyping("The microphone is not available, so type your answer instead.");
      }
    };
    // Chrome ends recognition after short silences; keep listening for the whole window.
    recognition.onend = () => {
      if (phaseRef.current === "answering" && recognitionRef.current === recognition) {
        try {
          recognition.start();
        } catch {
          fallBackToTyping("Listening stopped unexpectedly, so type your answer instead.");
        }
      }
    };
    recognitionRef.current = recognition;
    recognition.start();
    setPhase("answering");
    setSecondsLeft(ANSWER_SECONDS);
  }

  function send(answer: string) {
    if (sentRef.current) return;
    sentRef.current = true;
    setPhase("waiting");
    // On success the parent moves to the next question or the mark, which replaces
    // this component; if the call fails the guard is released and the words are
    // shown in the typed box so they can simply be sent again.
    void onAnswer(answer).finally(() => {
      sentRef.current = false;
      setPhase("typing");
    });
  }

  function finishAnswering(spoken: string) {
    stopRecognition();
    const answer = spoken.trim();
    if (!answer) {
      setNote("Nothing was heard, so type your answer instead.");
      setPhase("typing");
      return;
    }
    setNote(null);
    send(answer);
  }

  function askTheQuestion() {
    // Surface the microphone prompt now, not mid-answer while the clock is running.
    navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((stream) => stream.getTracks().forEach((track) => track.stop()))
      .catch(() => undefined);
    const audio = audioRef.current;
    if (!audio) {
      beginAnswering();
      return;
    }
    setPhase("listening");
    audio.play().catch(() => beginAnswering());
  }

  // Follow-up questions start speaking on their own so the conversation flows; if
  // the browser refuses the unprompted playback, the ready button remains.
  useEffect(() => {
    if (index === 0) return;
    const audio = audioRef.current;
    if (!audio) return;
    setPhase("listening");
    audio.play().catch(() => setPhase("ready"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index]);

  // One clock for the answering window. The transition at zero happens in the
  // effect below so a re-render can never skip it.
  useEffect(() => {
    if (phase !== "answering") return;
    const timer = setInterval(() => {
      setSecondsLeft((current) => (current > 0 ? current - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [phase]);

  useEffect(() => {
    if (secondsLeft > 0 || phase !== "answering") return;
    finishAnswering(transcript);
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
        <p className="u-label">Question {index + 1} of up to 3</p>
        <h1 className="u-display">About your own reasoning</h1>
      </div>

      {/* preload="auto" so the narration is generated while the student reads the intro */}
      <audio
        onEnded={beginAnswering}
        onError={beginAnswering}
        preload="auto"
        ref={audioRef}
        src={api.probeAudioUrl(submissionId, index)}
      />

      {phase === "ready" && (
        <>
          {index === 0 && (
            <div className="alert alert-info" role="note">
              <p>
                You will have a short spoken conversation about your own work — up to three
                questions. Each question is read aloud, and you then have thirty seconds to
                answer it out loud.
              </p>
            </div>
          )}
          <div className="mark-actions">
            <button className="btn btn-primary" onClick={askTheQuestion} type="button">
              {index === 0 ? "I am ready — ask the question" : "Hear the next question"}
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

      {phase === "listening" && <p className="u-muted">Listen to the question.</p>}

      {phase === "answering" && (
        <>
          <div className="probe-timer-block">
            <p className="probe-recording">Speak your answer aloud</p>
            <p className="probe-timer u-mono">{secondsLeft}</p>
          </div>
          <div className="mark-actions">
            <button
              className="btn btn-primary"
              disabled={busy}
              onClick={() => finishAnswering(transcript)}
              type="button"
            >
              I have finished answering
            </button>
          </div>
        </>
      )}

      {phase === "waiting" && <p className="u-muted">One moment…</p>}

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
              {busy ? "One moment…" : "Send answer"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
