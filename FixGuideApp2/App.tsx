import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  PermissionsAndroid,
  Platform,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { CactusLM, type CactusLMMessage } from 'cactus-react-native';
import { Camera } from 'react-native-camera-kit';
import Voice from '@react-native-voice/voice';
import Tts from 'react-native-tts';

const GEMINI_KEY = 'AIzaSyDg9hVo4LMfffjPcOnXq1oU6VMIh7uT2G8';
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_KEY}`;

const SYSTEM_PROMPT = `You are FixGuide — a calm, knowledgeable friend who is an expert in home repair, plumbing, electrical work, HVAC, and anything physical.
You are having a live conversation with someone who needs help. Speak naturally, like a real person — warm, clear, confident. Short sentences. Never robotic.
Guide them conversationally, one thing at a time. After guiding, check in: "Give that a try and tell me what happens."
If something is dangerous, say so immediately and firmly but calmly.
Keep responses under 80 words. Never use bullet points or numbered lists. Just talk.`;

type AgentState = 'idle' | 'downloading' | 'listening' | 'thinking' | 'speaking';
type Verdict = 'handle' | 'specialist' | 'danger' | null;
interface Message { role: 'user' | 'assistant'; content: string; }

export default function App() {
  const [state, setState] = useState<AgentState>('idle');
  const [verdict, setVerdict] = useState<Verdict>(null);
  const [response, setResponse] = useState('');
  const [history, setHistory] = useState<Message[]>([]);
  const [modelReady, setModelReady] = useState(false);
  const [modelStatus, setModelStatus] = useState('Tap Start to load model');
  const [downloadPct, setDownloadPct] = useState(0);
  const [agentRunning, setAgentRunning] = useState(false);
  const [error, setError] = useState('');
  const [ttsReady, setTtsReady] = useState(false);
  const lmRef = useRef<CactusLM | null>(null);
  const runningRef = useRef(false);

  useEffect(() => {
    requestPermissions();
    Tts.getInitStatus()
      .then(() => {
        Tts.setDefaultRate(0.52);
        Tts.setDefaultLanguage('en-US');
        setTtsReady(true);
      })
      .catch(() => {
        Tts.setDefaultRate(0.52);
        Tts.setDefaultLanguage('en-US');
        setTtsReady(true);
      });
    return () => {
      Voice.destroy().then(Voice.removeAllListeners);
      lmRef.current?.destroy?.();
    };
  }, []);

  async function requestPermissions() {
    if (Platform.OS === 'android') {
      await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        PermissionsAndroid.PERMISSIONS.CAMERA,
      ]);
    }
  }

  async function loadModel() {
    setState('downloading');
    setModelStatus('Downloading Gemma 270M...');
    try {
      const lm = new CactusLM({ model: 'functiongemma-270m-it' });
      await lm.download({
        onProgress: (p) => {
          setDownloadPct(Math.round(p * 100));
          setModelStatus(`Downloading ${Math.round(p * 100)}%`);
        },
      });
      lmRef.current = lm;
      setModelReady(true);
      setModelStatus('⚡ Gemma 270M · on-device via Cactus');
    } catch {
      setModelStatus('☁️  Cloud · Gemini 2.0 Flash');
    }
    setState('idle');
  }

  async function inferOnDevice(msgs: Message[]): Promise<string> {
    const messages: CactusLMMessage[] = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...msgs.map(m => ({ role: m.role as 'user' | 'assistant', content: m.content })),
    ];
    const result = await lmRef.current!.complete({ messages, options: { maxTokens: 150, temperature: 0.7 } });
    return result.response.trim();
  }

  async function inferCloud(msgs: Message[]): Promise<string> {
    const res = await fetch(GEMINI_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
        contents: msgs.map(m => ({ role: m.role === 'user' ? 'user' : 'model', parts: [{ text: m.content }] })),
      }),
    });
    const data = await res.json();
    return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? 'Sorry, try again.';
  }

  async function infer(msgs: Message[]): Promise<string> {
    if (modelReady && lmRef.current) {
      try { return await inferOnDevice(msgs); } catch {}
    }
    return await inferCloud(msgs);
  }

  function detectVerdict(text: string): Verdict {
    const u = text.toUpperCase();
    if (['DANGER', 'HAZARD', 'ELECTRIC SHOCK', 'GAS LEAK', 'STOP IMMEDIATELY', 'DO NOT TOUCH', 'FIRE RISK'].some(p => u.includes(p))) return 'danger';
    if (['CALL A ', 'CALL AN ', 'HIRE A ', 'NEED A SPECIALIST', 'ELECTRICIAN', 'LICENSED PLUMBER'].some(p => u.includes(p))) return 'specialist';
    return 'handle';
  }

  function listenOnce(): Promise<string> {
    return new Promise(resolve => {
      let done = false;
      const finish = (v: string) => { if (!done) { done = true; resolve(v); } };
      Voice.onSpeechResults = e => finish(e.value?.[0] ?? '');
      Voice.onSpeechError = () => finish('');
      Voice.onSpeechEnd = () => setTimeout(() => finish(''), 600);
      Voice.start('en-US').catch(() => finish(''));
      setTimeout(() => { Voice.stop().catch(() => {}); }, 10000);
    });
  }

  function speakAndWait(text: string): Promise<void> {
    return new Promise(resolve => {
      Tts.stop();
      const sub = Tts.addEventListener('tts-finish', () => { sub.remove(); resolve(); });
      Tts.speak(text);
      setTimeout(resolve, text.length * 65 + 2000);
    });
  }

  async function startAgent() {
    if (!modelReady && !lmRef.current) {
      await loadModel();
    }
    runningRef.current = true;
    setAgentRunning(true);
    setError('');
    setHistory([]); setVerdict(null); setResponse('');
    setState('speaking');
    await speakAndWait("Hey, I'm here. Tell me what you see and I'll walk you through it.");
    const msgs: Message[] = [];
    while (runningRef.current) {
      setState('listening');
      const heard = await listenOnce();
      if (!runningRef.current) break;
      if (!heard.trim()) continue;
      setState('thinking');
      try {
        const nextMsgs: Message[] = [...msgs, { role: 'user', content: heard }];
        const reply = await infer(nextMsgs);
        const v = detectVerdict(reply);
        setVerdict(v);
        setResponse(reply);
        msgs.push({ role: 'user', content: heard }, { role: 'assistant', content: reply });
        setHistory([...msgs]);
        setState('speaking');
        await speakAndWait(reply);
      } catch (e: any) {
        const msg = 'Error: ' + (e?.message ?? String(e));
        setError(msg);
        await speakAndWait('Something went wrong. Please try again.');
        break;
      }
    }
    setState('idle');
  }

  function stopAgent() {
    runningRef.current = false;
    Voice.stop().catch(() => {}); Tts.stop();
    setAgentRunning(false);
    setState('idle'); setVerdict(null); setResponse(''); setHistory([]);
  }

  const vc = verdict === 'danger' ? '#ef4444' : verdict === 'specialist' ? '#f59e0b' : '#00d4aa';
  const vl = verdict === 'danger' ? '⚠️  DANGER' : verdict === 'specialist' ? '📞  CALL SPECIALIST' : '✓  HANDLE IT';
  const stateColor = { idle: '#64748b', downloading: '#f59e0b', listening: '#00d4aa', thinking: '#f59e0b', speaking: '#a78bfa' }[state];
  const stateLabel = { idle: 'Tap Start', downloading: `Downloading ${downloadPct}%`, listening: '🎤  Listening...', thinking: '🧠  Thinking...', speaking: '🔊  Speaking...' }[state];

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#040a0f" />

      {agentRunning && (
        <View style={StyleSheet.absoluteFill}>
          <Camera
            style={StyleSheet.absoluteFill}
            cameraType="back"
            flashMode="off"
            focusMode="on"
            zoomMode="off"
          />
          <View style={s.camOverlay}>
            <View style={s.camHeader}>
              <View style={s.dot} /><Text style={s.logo}>FixGuide AI</Text>
              <View style={[s.camPill, { borderColor: stateColor + '99' }]}>
                {(state === 'thinking') && <ActivityIndicator size="small" color={stateColor} style={{ marginRight: 6 }} />}
                <Text style={[s.camPillTxt, { color: stateColor }]}>{stateLabel}</Text>
              </View>
            </View>
            {state === 'listening' && (
              <View style={s.wave}>
                {[8,18,28,36,26,16,8].map((h,i) => <View key={i} style={[s.waveBar,{height:h}]}/>)}
              </View>
            )}
            <View style={s.camBottom}>
              {verdict && (
                <View style={[s.verdictBadge,{borderColor:vc+'55',backgroundColor:vc+'22'}]}>
                  <Text style={[s.verdictText,{color:vc}]}>{vl}</Text>
                </View>
              )}
              {!!response && (
                <View style={s.responseCard}>
                  <Text style={s.responseText}>{response}</Text>
                </View>
              )}
              <TouchableOpacity style={s.stopBtn} onPress={stopAgent}>
                <Text style={s.stopTxt}>⏹  Stop</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      <ScrollView contentContainerStyle={s.scroll} style={{ display: agentRunning ? 'none' : 'flex' }}>

        <View style={s.header}>
          <View style={s.dot} />
          <Text style={s.logo}>FixGuide AI</Text>
        </View>

        <View style={s.modelBadge}>
          {state === 'downloading' && <ActivityIndicator size="small" color="#00d4aa" style={{ marginRight: 6 }} />}
          <Text style={[s.modelText, { color: modelReady ? '#00d4aa' : '#64748b' }]}>{modelStatus}</Text>
        </View>

        <Text style={s.motto}>Act on what you see.</Text>
        <Text style={s.subtitle}>Point your phone at the problem, tap Start, and describe what you see — I'll guide you through it.</Text>

        <View style={s.statePill}>
          {(state === 'thinking' || state === 'downloading') && <ActivityIndicator size="small" color={stateColor} style={{ marginRight: 8 }} />}
          <Text style={[s.stateText, { color: stateColor }]}>{stateLabel}</Text>
        </View>

        {state === 'listening' && (
          <View style={s.wave}>
            {[8, 18, 28, 36, 26, 16, 8].map((h, i) => <View key={i} style={[s.waveBar, { height: h }]} />)}
          </View>
        )}

        {verdict && (
          <View style={[s.verdictBadge, { borderColor: vc + '55', backgroundColor: vc + '18' }]}>
            <Text style={[s.verdictText, { color: vc }]}>{vl}</Text>
          </View>
        )}

        {!!response && (
          <View style={s.responseCard}>
            <Text style={s.responseText}>{response}</Text>
          </View>
        )}

        <View style={s.controls}>
          {state === 'idle'
            ? <TouchableOpacity style={s.startBtn} onPress={startAgent}>
                <Text style={s.startTxt}>▶  Start Agent</Text>
              </TouchableOpacity>
            : state !== 'downloading'
              ? <TouchableOpacity style={s.stopBtn} onPress={stopAgent}>
                  <Text style={s.stopTxt}>⏹  Stop</Text>
                </TouchableOpacity>
              : null}
        </View>

        {!!error && (
          <View style={s.errorCard}>
            <Text style={s.errorText}>{error}</Text>
          </View>
        )}

        {history.length > 0 && (
          <View style={s.histWrap}>
            <Text style={s.histLabel}>CONVERSATION</Text>
            {history.map((m, i) => (
              <View key={i} style={[s.bubble, m.role === 'user' ? s.userBubble : s.aiBubble]}>
                <Text style={[s.bubbleTxt, m.role === 'user' ? s.userTxt : s.aiTxt]}>{m.content}</Text>
              </View>
            ))}
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const W = Dimensions.get('window').width;

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#040a0f' },
  scroll: { padding: 20, paddingBottom: 60 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 16 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#00d4aa' },
  logo: { color: '#e2e8f0', fontSize: 18, fontWeight: '800' },
  modelBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#0a1520', borderWidth: 1, borderColor: '#1a3a52', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, marginBottom: 24, alignSelf: 'flex-start' },
  modelText: { fontSize: 12, fontFamily: 'monospace' },
  motto: { color: '#00d4aa', fontSize: 26, fontWeight: '900', letterSpacing: -0.5, marginBottom: 8 },
  subtitle: { color: '#64748b', fontSize: 14, lineHeight: 20, marginBottom: 32 },
  statePill: { flexDirection: 'row', alignItems: 'center', alignSelf: 'center', backgroundColor: '#0a1520', borderWidth: 1, borderColor: '#1a3a52', borderRadius: 100, paddingHorizontal: 16, paddingVertical: 8, marginBottom: 20 },
  stateText: { fontSize: 14, fontFamily: 'monospace' },
  wave: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, height: 44, marginBottom: 20 },
  waveBar: { width: 4, borderRadius: 2, backgroundColor: '#00d4aa' },
  verdictBadge: { alignSelf: 'center', borderWidth: 1, borderRadius: 100, paddingHorizontal: 16, paddingVertical: 6, marginBottom: 16 },
  verdictText: { fontSize: 12, fontWeight: '800', letterSpacing: 1.5 },
  responseCard: { backgroundColor: '#0a1520', borderWidth: 1, borderColor: '#1a3a52', borderRadius: 14, padding: 18, marginBottom: 28 },
  responseText: { color: '#e2e8f0', fontSize: 15, lineHeight: 24 },
  controls: { alignItems: 'center', marginBottom: 32 },
  startBtn: { backgroundColor: '#00d4aa', paddingHorizontal: 48, paddingVertical: 18, borderRadius: 100 },
  startTxt: { color: '#040a0f', fontSize: 17, fontWeight: '800' },
  stopBtn: { backgroundColor: '#0a1520', paddingHorizontal: 48, paddingVertical: 16, borderRadius: 100, borderWidth: 1, borderColor: '#1a3a52' },
  stopTxt: { color: '#e2e8f0', fontSize: 16, fontWeight: '700' },
  errorCard: { backgroundColor: '#2d0a0a', borderWidth: 1, borderColor: '#ef4444', borderRadius: 10, padding: 14, marginTop: 8 },
  errorText: { color: '#ef4444', fontSize: 12, fontFamily: 'monospace' },
  camOverlay: { flex: 1, justifyContent: 'space-between', padding: 20, paddingBottom: 48 },
  camHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8, backgroundColor: 'rgba(4,10,15,0.6)', borderRadius: 12, padding: 10 },
  camPill: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(4,10,15,0.75)', borderWidth: 1, borderRadius: 100, paddingHorizontal: 12, paddingVertical: 5, marginLeft: 'auto' },
  camPillTxt: { fontSize: 12, fontFamily: 'monospace' },
  camBottom: { gap: 12 },
  histWrap: { gap: 10 },
  histLabel: { color: '#64748b', fontSize: 11, fontFamily: 'monospace', letterSpacing: 1, marginBottom: 4 },
  bubble: { borderRadius: 12, padding: 12, maxWidth: W * 0.85 },
  userBubble: { backgroundColor: '#0f1e2d', alignSelf: 'flex-end' },
  aiBubble: { backgroundColor: '#0a1520', borderWidth: 1, borderColor: '#1a3a52', alignSelf: 'flex-start' },
  bubbleTxt: { fontSize: 14, lineHeight: 20 },
  userTxt: { color: '#94a3b8' },
  aiTxt: { color: '#e2e8f0' },
});
