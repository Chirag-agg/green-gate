import { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { Mic, Square, Upload, PlayCircle, Loader2 } from 'lucide-react';
import { processVoiceAudio, synthesizeVoiceResponse } from '../utils/api';

export default function VoiceTest() {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [localAudioUrl, setLocalAudioUrl] = useState('');
  const [ttsAudioUrl, setTtsAudioUrl] = useState('');
  const [result, setResult] = useState(null);
  const [callActive, setCallActive] = useState(false);
  const [turnCount, setTurnCount] = useState(0);
  const [sessionId, setSessionId] = useState('');
  const [conversationData, setConversationData] = useState({
    electricity_kwh: null,
    diesel_liters: null,
    month: null,
  });

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const callActiveRef = useRef(false);

  useEffect(() => {
    callActiveRef.current = callActive;
  }, [callActive]);

  useEffect(() => {
    return () => {
      if (localAudioUrl) URL.revokeObjectURL(localAudioUrl);
      if (ttsAudioUrl) URL.revokeObjectURL(ttsAudioUrl);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [localAudioUrl, ttsAudioUrl]);

  const getSupportedMimeType = () => {
    // Try formats supported by Whisper: wav, mp3, m4a, ogg
    const candidates = [
      'audio/wav',
      'audio/ogg; codecs=opus',
      'audio/ogg; codecs=vorbis',
      'audio/ogg',
      'audio/mp4',
      'audio/webm; codecs=opus',
      'audio/webm'
    ];

    for (const mimeType of candidates) {
      if (MediaRecorder.isTypeSupported(mimeType)) {
        return mimeType;
      }
    }

    // Fallback to default (usually webm, but we tried to avoid it)
    return candidates[0];
  };

  const getFileExtension = (mimeType) => {
    if (mimeType.includes('wav')) return 'wav';
    if (mimeType.includes('mp4') || mimeType.includes('m4a')) return 'm4a';
    if (mimeType.includes('ogg')) return 'ogg';
    if (mimeType.includes('webm')) return 'webm';
    return 'wav';
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mimeType = getSupportedMimeType();
      const recorder = new MediaRecorder(stream, { mimeType });
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const ext = getFileExtension(mimeType);
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const file = new File([blob], `voice_input.${ext}`, { type: mimeType });
        setSelectedFile(file);
        if (localAudioUrl) URL.revokeObjectURL(localAudioUrl);
        setLocalAudioUrl(URL.createObjectURL(blob));
      };

      recorder.start();
      setRecording(true);
    } catch (err) {
      toast.error('Microphone access denied or unavailable');
    }
  };

  const stopRecording = () => {
    if (!recorderRef.current) return;
    recorderRef.current.stop();
    setRecording(false);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const onFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    if (localAudioUrl) URL.revokeObjectURL(localAudioUrl);
    setLocalAudioUrl(URL.createObjectURL(file));
  };

  const isConversationComplete = (payload) => {
    const data = payload?.data || {};
    return (
      data.electricity_kwh !== null
      && data.electricity_kwh !== undefined
      && data.diesel_liters !== null
      && data.diesel_liters !== undefined
      && data.month
    );
  };

  const captureAudioOnce = (durationMs = 5500) => new Promise(async (resolve, reject) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mimeType = getSupportedMimeType();
      const recorder = new MediaRecorder(stream, { mimeType });
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        try {
          const ext = getFileExtension(mimeType);
          const blob = new Blob(chunksRef.current, { type: mimeType });
          const file = new File([blob], `voice_turn.${ext}`, { type: mimeType });
          setSelectedFile(file);
          if (localAudioUrl) URL.revokeObjectURL(localAudioUrl);
          setLocalAudioUrl(URL.createObjectURL(blob));
          resolve(file);
        } finally {
          setRecording(false);
          if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
          }
        }
      };

      recorder.start();
      setRecording(true);

      window.setTimeout(() => {
        if (recorder.state !== 'inactive') recorder.stop();
      }, durationMs);
    } catch (err) {
      reject(err);
    }
  });

  const playTTSAndWait = async (ttsBlob) => {
    if (ttsAudioUrl) URL.revokeObjectURL(ttsAudioUrl);
    const url = URL.createObjectURL(ttsBlob);
    setTtsAudioUrl(url);

    const audio = new Audio(url);
    audio.volume = 1.0;  // Ensure volume is at max

    try {
      const playPromise = audio.play();

      // Handle autoplay policy blocking
      if (playPromise !== undefined) {
        try {
          await playPromise;
        } catch (err) {
          console.warn('Autoplay blocked by browser policy (this is normal). Audio is ready to play.', err);
          toast.error('Audio autoplay blocked. Click the play button below to hear the response.');
          return;
        }
      }

      // Wait for audio to finish playing
      await new Promise((resolve) => {
        audio.onended = resolve;
        audio.onerror = (err) => {
          console.error('Audio playback error:', err);
          resolve();
        };
        // Safety timeout: if audio doesn't end, resolve after 30 seconds
        setTimeout(resolve, 30000);
      });
    } catch (err) {
      console.error('TTS playback error:', err);
      toast.error('Could not play audio response');
    }
  };

  const processAudioFile = async (file, currentSessionId = null) => {
    setProcessing(true);
    try {
      const processRes = await processVoiceAudio(file, currentSessionId);
      const payload = processRes.data;
      setResult(payload);
      if (payload?.state?.session_id) {
        setSessionId(payload.state.session_id);
      }
      if (payload?.state?.data) {
        setConversationData({
          electricity_kwh: payload.state.data.electricity_kwh ?? null,
          diesel_liters: payload.state.data.diesel_liters ?? null,
          month: payload.state.data.month ?? null,
        });
      }

      // TTS endpoint returns audio/wav blob
      const ttsRes = await synthesizeVoiceResponse(
        payload.response_text || payload.text || 'ठीक है',
        payload.response_language || payload.detected_language || null,
      );
      const audioBlob = ttsRes.data;

      await playTTSAndWait(audioBlob);
      return payload;
    } catch (err) {
      console.error('processAudioFile error:', err);
      throw err;
    } finally {
      setProcessing(false);
    }
  };

  const runPipeline = async () => {
    if (!selectedFile) {
      toast.error('Please record or upload an audio file first');
      return;
    }

    setProcessing(true);
    setResult(null);

    try {
      await processAudioFile(selectedFile);

      toast.success('Voice pipeline completed');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Voice processing failed');
    } finally {
      setProcessing(false);
    }
  };

  const startCallMode = async () => {
    if (processing) return;

    setCallActive(true);
    setTurnCount(0);
    setResult(null);
    const activeSessionId = sessionId || (window.crypto?.randomUUID?.() ?? `session_${Date.now()}`);
    setSessionId(activeSessionId);
    let runningData = { electricity_kwh: null, diesel_liters: null, month: null };
    setConversationData(runningData);
    setProcessing(true);

    try {
      const maxTurns = 8;

      for (let i = 0; i < maxTurns; i += 1) {
        if (!callActiveRef.current) {
          toast('कॉल रोक दिया गया', { icon: '🛑' });
          break;
        }

        setTurnCount(i + 1);
        toast.loading(`🎤 सुन रहा हूं... (टर्न ${i + 1}/${maxTurns})`, { duration: Infinity });

        try {
          const audioFile = await captureAudioOnce(5500);
          toast.dismiss();

          const payload = await processAudioFile(audioFile, activeSessionId);

          runningData = payload?.state?.data
            ? {
              electricity_kwh: payload.state.data.electricity_kwh ?? runningData.electricity_kwh,
              diesel_liters: payload.state.data.diesel_liters ?? runningData.diesel_liters,
              month: payload.state.data.month ?? runningData.month,
            }
            : {
              electricity_kwh: payload?.data?.electricity_kwh ?? runningData.electricity_kwh,
              diesel_liters: payload?.data?.diesel_liters ?? runningData.diesel_liters,
              month: payload?.data?.month ?? runningData.month,
            };
          setConversationData(runningData);

          if (isConversationComplete(payload)) {
            toast.success('✅ कॉल पूरी हो गई। सभी डेटा मिल गया।');
            break;
          }
        } catch (turnErr) {
          toast.dismiss();
          toast.error(`टर्न ${i + 1} विफल: ${turnErr.message || 'कोशिश फिर से करें'}`);

          if (turnErr.response?.status === 401) {
            throw new Error('Authentication failed');
          }
          // Continue to next turn on other errors (microphone timeout, API issues, etc)
        }
      }
    } catch (err) {
      toast.dismiss();
      const errorMsg = err.response?.data?.detail || err.message || 'Voice call failed. Check microphone permissions.';
      toast.error(errorMsg);
      console.error('startCallMode error:', err);
    } finally {
      setCallActive(false);
      setProcessing(false);
      setRecording(false);
      toast.dismiss();
    }
  };

  const stopCallMode = () => {
    callActiveRef.current = false;
    setCallActive(false);
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setRecording(false);
    setSessionId('');
    toast('Call stopped');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">
      <div className="card p-6 sm:p-8">
        <h1 className="text-3xl font-bold text-surface-900 mb-2">Voice AI Test</h1>
        <p className="text-surface-600 mb-6">
          Record or upload audio, run the carbon voice pipeline, and play the generated TTS response.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <button
            onClick={callActive ? stopCallMode : startCallMode}
            className={`btn-primary !py-4 gap-2 ${callActive ? '!bg-red-600 hover:!bg-red-700' : ''}`}
            type="button"
            disabled={processing && !callActive}
          >
            {callActive ? <Square className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            {callActive ? `End Hindi Voice Call (Turn ${turnCount})` : 'Start Hindi Voice Call'}
          </button>

          <button
            onClick={recording ? stopRecording : startRecording}
            className={`btn-primary !py-4 gap-2 ${recording ? '!bg-red-600 hover:!bg-red-700' : ''}`}
            type="button"
            disabled={callActive || processing}
          >
            {recording ? <Square className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            {recording ? 'Stop Recording' : 'Start Recording'}
          </button>

          <label className="btn-secondary !py-4 gap-2 cursor-pointer justify-center">
            <Upload className="w-5 h-5" /> Upload Audio (wav/mp3/m4a/ogg/webm)
            <input
              type="file"
              accept="audio/*"
              onChange={onFileChange}
              className="hidden"
              disabled={callActive || processing}
            />
          </label>
        </div>

        {callActive && (
          <div className="rounded-xl border border-green-200 bg-green-50 p-4 mb-6 text-green-800">
            <p className="font-semibold">Live Hindi Call is active</p>
            <p className="text-sm">Assistant will keep asking follow-up questions until electricity, diesel, and month are captured.</p>
          </div>
        )}

        {selectedFile && (
          <div className="rounded-xl border border-surface-200 bg-surface-50 p-4 mb-6">
            <p className="text-sm text-surface-700 mb-2">
              Selected file: <span className="font-semibold">{selectedFile.name}</span>
            </p>
            {localAudioUrl && <audio controls src={localAudioUrl} className="w-full" />}
          </div>
        )}

        <button
          onClick={runPipeline}
          disabled={processing}
          className="btn-primary !py-4 gap-2"
          type="button"
        >
          {processing ? <Loader2 className="w-5 h-5 animate-spin" /> : <PlayCircle className="w-5 h-5" />}
          {processing ? 'Processing Voice...' : 'Run Voice Pipeline'}
        </button>
      </div>

      {result && (
        <div className="card p-6 sm:p-8 mt-6">
          <h2 className="text-2xl font-bold text-surface-900 mb-4">Pipeline Output</h2>

          <div className="space-y-3 text-sm sm:text-base">
            <p><span className="font-semibold text-surface-800">Transcript:</span> {result.transcript || '-'}</p>
            <p><span className="font-semibold text-surface-800">Detected Language:</span> {result.detected_language || '-'}</p>
            <p><span className="font-semibold text-surface-800">Validation:</span> {result.validation || '-'}</p>
            <p><span className="font-semibold text-surface-800">Response Text:</span> {result.response_text || result.text || '-'}</p>
          </div>

          <div className="mt-4 rounded-xl border border-surface-200 bg-surface-50 p-4 overflow-x-auto">
            <pre className="text-xs sm:text-sm text-surface-700">
              {JSON.stringify(result.data || {}, null, 2)}
            </pre>
          </div>

          {ttsAudioUrl && (
            <div className="mt-5">
              <p className="font-semibold text-surface-800 mb-2">Generated Voice Response</p>
              <audio controls src={ttsAudioUrl} className="w-full" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
