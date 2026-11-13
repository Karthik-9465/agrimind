import React, { useState, useEffect, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('agrimind_token') || '');
  const [user, setUser] = useState(null);
  const [farms, setFarms] = useState([]);
  const [selectedFarm, setSelectedFarm] = useState(null);
  const [selectedCrop, setSelectedCrop] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [language, setLanguage] = useState('en');

  // Service Health States
  const [geminiStatus, setGeminiStatus] = useState(null);
  const [gnaniStatus, setGnaniStatus] = useState(null);
  const [integrationsStatus, setIntegrationsStatus] = useState(null);
  const [isRefreshingHealth, setIsRefreshingHealth] = useState(false);

  // Auth States
  const [isSignup, setIsSignup] = useState(false);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authFullName, setAuthFullName] = useState('');
  const [authError, setAuthError] = useState('');

  // Farm Creation Form State
  const [farmName, setFarmName] = useState('');
  const [farmLocation, setFarmLocation] = useState('Mandya, Karnataka');
  const [farmArea, setFarmArea] = useState('2.5');
  const [soilType, setSoilType] = useState('Loam');

  // Crop Creation State
  const [cropName, setCropName] = useState('Tomato');
  const [cropVariety, setCropVariety] = useState('Arka Rakshak (F1)');
  const [cropDate, setCropDate] = useState('2026-03-01');

  // Chat & AI Assistant States
  const initialGreetingMessage = {
    sender: 'agent',
    isInitialGreeting: true,
    text: 'Hello! I am your AgriMind AI Assistant. Ask any agriculture-related question via text, upload a leaf photo for disease diagnosis, or click the microphone to speak in English, Telugu, or Hindi.'
  };
  const [chatMessages, setChatMessages] = useState([initialGreetingMessage]);
  const [chatInput, setChatInput] = useState('');
  const [selectedImageB64, setSelectedImageB64] = useState('');
  const [imagePreviewUrl, setImagePreviewUrl] = useState('');
  const [loadingText, setLoadingText] = useState('');
  const [diseaseHistory, setDiseaseHistory] = useState([]);

  // Voice Interaction States
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceProcessingText, setVoiceProcessingText] = useState('');
  const [selectedVoice, setSelectedVoice] = useState('Avinash');
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const stopRequestedRef = useRef(false);
  const isTranscribingRef = useRef(false);

  // Tool Specific Dedicated Views States
  const [weatherData, setWeatherData] = useState(null);
  const [weatherLocation, setWeatherLocation] = useState('Mandya, India');

  // Irrigation Calculator State
  const [irrCrop, setIrrCrop] = useState('Tomato');
  const [irrSoil, setIrrSoil] = useState('Loam');
  const [irrStage, setIrrStage] = useState('mid_season');
  const [irrMethod, setIrrMethod] = useState('drip');
  const [irrArea, setIrrArea] = useState('2.5');
  const [irrResult, setIrrResult] = useState(null);

  // Fertilizer Planner State
  const [fertCrop, setFertCrop] = useState('Tomato');
  const [fertSoil, setFertSoil] = useState('Loam');
  const [fertStage, setFertStage] = useState('basal');
  const [fertPh, setFertPh] = useState('6.8');
  const [fertArea, setFertArea] = useState('2.5');
  const [fertN, setFertN] = useState('medium');
  const [fertP, setFertP] = useState('medium');
  const [fertK, setFertK] = useState('medium');
  const [fertResult, setFertResult] = useState(null);

  // Market Price Search State
  const [mktCommodity, setMktCommodity] = useState('Tomato');
  const [mktLocation, setMktLocation] = useState('Mandya');
  const [mktResult, setMktResult] = useState(null);

  useEffect(() => {
    if (token) {
      fetchUser();
      fetchFarms();
      fetchDiseaseHistory();
    }
    checkHealth();
    fetchWeather(weatherLocation);
  }, [token]);

  const checkHealth = async (forceRefresh = false) => {
    try {
      if (forceRefresh) setIsRefreshingHealth(true);
      const url = forceRefresh 
        ? `${API_BASE}/health/integrations?refresh=true` 
        : `${API_BASE}/health/integrations`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setIntegrationsStatus(data);
        if (data.providers) {
          setGeminiStatus(data.providers.gemini_vision);
          setGnaniStatus(data.providers.gnani_ai);
        }
      } else {
        const gRes = await fetch(`${API_BASE}/health/gemini${forceRefresh ? '?refresh=true' : ''}`);
        if (gRes.ok) setGeminiStatus(await gRes.json());
        const gnRes = await fetch(`${API_BASE}/health/gnani`);
        if (gnRes.ok) setGnaniStatus(await gnRes.json());
      }
    } catch (e) {
      console.error("Health check error", e);
    } finally {
      if (forceRefresh) setIsRefreshingHealth(false);
    }
  };

  const fetchUser = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setUser(await res.json());
      } else {
        handleLogout();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchFarms = async () => {
    try {
      const res = await fetch(`${API_BASE}/farms`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setFarms(data);
        if (data.length > 0 && !selectedFarm) {
          setSelectedFarm(data[0]);
          if (data[0].location) setWeatherLocation(data[0].location);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDiseaseHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/reports`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setDiseaseHistory(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchWeather = async (loc) => {
    try {
      const res = await fetch(`${API_BASE}/agent/weather?location=${encodeURIComponent(loc || 'Mandya, India')}`);
      if (res.ok) setWeatherData(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    const endpoint = isSignup ? `${API_BASE}/auth/signup` : `${API_BASE}/auth/login`;
    const payload = isSignup 
      ? { email: authEmail, password: authPassword, full_name: authFullName }
      : { email: authEmail, password: authPassword };

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        setAuthError(data.detail || 'Authentication failed');
        return;
      }
      localStorage.setItem('agrimind_token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      setActiveTab('dashboard');
    } catch (e) {
      setAuthError('Connection error to backend');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('agrimind_token');
    setToken('');
    setUser(null);
    setFarms([]);
    setSelectedFarm(null);
    setSelectedCrop(null);
    setDiseaseHistory([]);
  };

  // --------------------------------------------------------------------------
  // Voice Recording & Gnani STT / TTS Handlers
  // --------------------------------------------------------------------------
  const stopActiveMediaTracks = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => {
        try {
          track.stop();
        } catch (_) {
          // Ignore track stop errors during cleanup
        }
      });
      mediaStreamRef.current = null;
    }
  };

  const startRecording = async () => {
    if (isRecording || isTranscribingRef.current) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];
      stopRequestedRef.current = false;

      // Determine browser-supported audio MIME type
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
      }
      const options = mimeType ? { mimeType } : {};
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const finalizedChunks = [...audioChunksRef.current];
        audioChunksRef.current = [];
        stopActiveMediaTracks();
        mediaRecorderRef.current = null;

        const actualMime = mediaRecorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(finalizedChunks, { type: actualMime });

        if (audioBlob.size < 300) {
          alert("Audio recording was too short or empty. Please hold the mic and speak for at least 1-2 seconds.");
          setVoiceProcessingText('');
          return;
        }

        let ext = 'webm';
        if (actualMime.includes('ogg')) ext = 'ogg';
        else if (actualMime.includes('wav')) ext = 'wav';
        else if (actualMime.includes('mp4')) ext = 'mp4';

        await handleAudioUpload(audioBlob, `farmer_voice.${ext}`, actualMime);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setVoiceProcessingText('Listening to your speech (Click mic to finish)...');
    } catch (err) {
      stopActiveMediaTracks();
      alert("Microphone access was denied or is unavailable. Please allow microphone permissions in your browser.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording && !stopRequestedRef.current) {
      stopRequestedRef.current = true;
      setIsRecording(false);
      setVoiceProcessingText('Finalizing audio & transcribing with Gnani AI Prisma...');
      if (mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
    }
  };

  const handleAudioUpload = async (audioBlob, filename = 'farmer_voice.webm', mimeType = 'audio/webm') => {
    if (isTranscribingRef.current) return;
    isTranscribingRef.current = true;
    setIsTranscribing(true);

    const formData = new FormData();
    formData.append('file', audioBlob, filename);
    formData.append('language', language);

    try {
      const res = await fetch(`${API_BASE}/agent/voice/transcribe`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json().catch(() => ({}));
      setVoiceProcessingText('');

      if (res.ok && data.text) {
        setChatInput(data.text);
        // Automatically dispatch transcribed question to agent
        handleSendChat(data.text);
      } else if (res.ok && !data.text) {
        alert("Audio received, but no intelligible speech detected. Please speak clearly into your microphone.");
      } else {
        alert(data.detail || `Voice transcription failed (HTTP ${res.status}).`);
      }
    } catch (e) {
      setVoiceProcessingText('');
      alert("Network error communicating with Gnani Speech service: " + e.message);
    } finally {
      isTranscribingRef.current = false;
      setIsTranscribing(false);
    }
  };

  const playSpeechAudio = async (textToSpeak, customVoice = null) => {
    if (isSynthesizing) return;
    setIsSynthesizing(true);
    try {
      const voiceToUse = customVoice || selectedVoice;
      const res = await fetch(`${API_BASE}/agent/voice/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToSpeak,
          language: language,
          voice: voiceToUse,
          speed: 1.0
        })
      });
      if (res.ok) {
        const contentType = res.headers.get('content-type') || 'audio/wav';
        const blob = await res.blob();
        const typedBlob = blob.type ? blob : new Blob([blob], { type: contentType });
        const audioUrl = URL.createObjectURL(typedBlob);
        const audio = new Audio();
        audio.src = audioUrl;
        audio.playbackRate = 1.0;
        audio.preservesPitch = true;
        audio.onended = () => URL.revokeObjectURL(audioUrl);
        audio.onerror = (e) => {
          URL.revokeObjectURL(audioUrl);
          console.error("Playback error:", e);
          alert("Error during audio playback in browser.");
        };
        await audio.play();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || `Speech synthesis failed with status ${res.status}`);
      }
    } catch (e) {
      console.error("Audio playback error", e);
      alert("Network error while generating speech: " + e.message);
    } finally {
      setIsSynthesizing(false);
    }
  };

  // --------------------------------------------------------------------------
  // Chat Dispatch
  // --------------------------------------------------------------------------
  const handleImageFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      alert('Only JPEG, PNG, and WEBP formats are accepted.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert('Image file size must be under 10 MB.');
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      setSelectedImageB64(reader.result);
      setImagePreviewUrl(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleSendChat = async (promptOverride) => {
    const textMsg = promptOverride || chatInput;
    if (!textMsg.trim() && !selectedImageB64) return;

    const userMsg = {
      sender: 'user',
      text: textMsg || 'Please analyze this uploaded crop image.',
      imagePreview: imagePreviewUrl || null
    };

    const historyPayload = chatMessages
      .filter(m => !m.isInitialGreeting && !m.isErrorBanner && m.text)
      .slice(-8)
      .map(m => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text,
        tool_used: m.toolUsed || null
      }));

    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    const currentImg = selectedImageB64;
    setSelectedImageB64('');
    setImagePreviewUrl('');

    setLoadingText('AgriMind AI analyzing your agricultural question...');

    try {
      const res = await fetch(`${API_BASE}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: textMsg || 'Please diagnose the crop condition in this image.',
          image_b64: currentImg || null,
          farm_id: selectedFarm ? selectedFarm.id : null,
          crop_id: selectedCrop ? selectedCrop.id : null,
          language: language,
          history: historyPayload
        })
      });

      setLoadingText('');
      const data = await res.json();
      if (!res.ok) {
        setChatMessages(prev => [...prev, {
          sender: 'agent',
          isErrorBanner: true,
          text: `⚠️ ${data.detail || 'Error processing request.'}`
        }]);
        return;
      }

      setChatMessages(prev => [...prev, {
        sender: 'agent',
        text: data.reply,
        toolUsed: data.tool_used,
        assessment: data.assessment,
        irrigation: data.irrigation,
        fertilizer: data.fertilizer,
        weather: data.weather,
        market: data.market,
        knowledge: data.knowledge
      }]);

      if (data.assessment) fetchDiseaseHistory();
    } catch (err) {
      setLoadingText('');
      setChatMessages(prev => [...prev, {
        sender: 'agent',
        isErrorBanner: true,
        text: '⚠️ Network connection failure with backend.'
      }]);
    }
  };

  // --------------------------------------------------------------------------
  // Direct Dedicated Tool Invocations
  // --------------------------------------------------------------------------
  const runIrrigationCalculator = async () => {
    const formData = new FormData();
    formData.append('crop', irrCrop);
    formData.append('soil_type', irrSoil);
    formData.append('growth_stage', irrStage);
    formData.append('location', weatherLocation);
    formData.append('irrigation_method', irrMethod);
    formData.append('field_area_acres', irrArea);

    try {
      const res = await fetch(`${API_BASE}/agent/irrigation/calculate`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) setIrrResult(await res.json());
    } catch (e) {
      alert("Error calculating irrigation schedule.");
    }
  };

  const runFertilizerPlanner = async () => {
    const formData = new FormData();
    formData.append('crop', fertCrop);
    formData.append('soil_type', fertSoil);
    formData.append('growth_stage', fertStage);
    formData.append('soil_ph', fertPh);
    formData.append('soil_n_status', fertN);
    formData.append('soil_p_status', fertP);
    formData.append('soil_k_status', fertK);
    formData.append('field_area_acres', fertArea);

    try {
      const res = await fetch(`${API_BASE}/agent/fertilizer/calculate`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) setFertResult(await res.json());
    } catch (e) {
      alert("Error generating fertilizer plan.");
    }
  };

  const runMarketSearch = async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/market/prices?commodity=${encodeURIComponent(mktCommodity)}&location=${encodeURIComponent(mktLocation)}`);
      if (res.ok) setMktResult(await res.json());
    } catch (e) {
      alert("Error searching market prices.");
    }
  };

  const handleCreateFarm = async (e) => {
    e.preventDefault();
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/farms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          name: farmName,
          location: farmLocation,
          area_acres: parseFloat(farmArea),
          soil_type: soilType
        })
      });
      if (res.ok) {
        const newFarm = await res.json();
        setFarms([...farms, newFarm]);
        setSelectedFarm(newFarm);
        setFarmName('');
        alert("Farm holding saved successfully!");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddCrop = async (e) => {
    e.preventDefault();
    if (!selectedFarm || !token) return;
    try {
      const res = await fetch(`${API_BASE}/farms/${selectedFarm.id}/crops`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          name: cropName,
          variety: cropVariety,
          planting_date: cropDate,
          status: 'Healthy'
        })
      });
      if (res.ok) {
        const newCrop = await res.json();
        const updatedFarm = {
          ...selectedFarm,
          crops: [...(selectedFarm.crops || []), newCrop]
        };
        setSelectedFarm(updatedFarm);
        setFarms(farms.map(f => f.id === updatedFarm.id ? updatedFarm : f));
        alert("Crop registered successfully!");
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="brand">
          <span className="brand-icon">🌱</span>
          <div>
            <h1 className="brand-title">AgriMind AI</h1>
            <span className="brand-subtitle">Agentic Smart Agriculture Assistant • Deployment Ready</span>
          </div>
        </div>

        <div className="nav-actions">
          {/* Language Selector */}
          <select 
            className="lang-select" 
            value={language} 
            onChange={e => setLanguage(e.target.value)}
            title="Preferred Language"
          >
            <option value="en">🌐 English</option>
            <option value="te">🇮🇳 తెలుగు (Telugu)</option>
            <option value="hi">🇮🇳 हिन्दी (Hindi)</option>
          </select>

          {/* AI Connectivity Badges */}
          {geminiStatus && (
            <span
              className={`badge ${
                geminiStatus.mode === 'CONNECTED' || geminiStatus.mode === 'LIVE'
                  ? 'badge-success'
                  : geminiStatus.mode === 'INVALID_KEY' || geminiStatus.mode === 'AUTH_FAILED' || geminiStatus.mode === 'MODEL_ERROR'
                  ? 'badge-danger'
                  : 'badge-warning'
              }`}
              title={geminiStatus.status_detail || ''}
            >
              Gemini Vision: {
                geminiStatus.mode === 'CONNECTED' || geminiStatus.mode === 'LIVE'
                  ? 'Live (2.5 Flash)'
                  : geminiStatus.mode === 'INVALID_KEY'
                  ? 'Invalid Key'
                  : geminiStatus.mode === 'MODEL_ERROR'
                  ? 'Model Error'
                  : geminiStatus.mode === 'CONNECTION_ERROR'
                  ? 'Connection Error'
                  : geminiStatus.mode === 'NOT_CONFIGURED'
                  ? 'NOT CONFIGURED'
                  : geminiStatus.mode || 'Dev Mock Mode'
              }
            </span>
          )}
          {gnaniStatus && (
            <span
              className={`badge ${
                gnaniStatus.mode === 'LIVE' || (gnaniStatus.mode !== 'AUTH_FAILED' && gnaniStatus.gnani_configured)
                  ? 'badge-success'
                  : gnaniStatus.mode === 'AUTH_FAILED'
                  ? 'badge-danger'
                  : 'badge-info'
              }`}
              title={gnaniStatus.status_detail || ''}
            >
              Gnani Voice: {gnaniStatus.mode === 'LIVE' ? 'Live (Prisma/Timbre)' : (gnaniStatus.mode || (gnaniStatus.gnani_configured ? 'Live Ready' : 'Dev Mock Mode'))}
            </span>
          )}

          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                👨‍🌾 {user.full_name || user.email}
              </span>
              <button className="btn btn-secondary" onClick={handleLogout}>Logout</button>
            </div>
          ) : (
            <button className="btn btn-primary" onClick={() => setActiveTab('settings')}>Sign In / Register</button>
          )}
        </div>
      </header>

      {/* Navigation Tabs Bar */}
      <nav className="tab-header">
        <button className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
          🏠 Dashboard
        </button>
        <button className={`tab-btn ${activeTab === 'assistant' ? 'active' : ''}`} onClick={() => setActiveTab('assistant')}>
          🤖 AI Agronomist Chat
        </button>
        <button className={`tab-btn ${activeTab === 'disease' ? 'active' : ''}`} onClick={() => setActiveTab('disease')}>
          🌿 Disease Detection
        </button>
        <button className={`tab-btn ${activeTab === 'weather' ? 'active' : ''}`} onClick={() => setActiveTab('weather')}>
          🌦️ Weather
        </button>
        <button className={`tab-btn ${activeTab === 'irrigation' ? 'active' : ''}`} onClick={() => setActiveTab('irrigation')}>
          💧 Smart Irrigation
        </button>
        <button className={`tab-btn ${activeTab === 'fertilizer' ? 'active' : ''}`} onClick={() => setActiveTab('fertilizer')}>
          🧪 Fertilizer Planner
        </button>
        <button className={`tab-btn ${activeTab === 'market' ? 'active' : ''}`} onClick={() => setActiveTab('market')}>
          📊 Market Prices
        </button>
        <button className={`tab-btn ${activeTab === 'farms' ? 'active' : ''}`} onClick={() => setActiveTab('farms')}>
          🌾 Farm Holdings
        </button>
        <button className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
          ⚙️ Settings
        </button>
      </nav>

      {/* --------------------------------------------------------------------- */}
      {/* 1. DASHBOARD VIEW */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'dashboard' && (
        <div>
          <div className="card" style={{ background: 'linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%)', borderColor: '#86efac' }}>
            <h2 style={{ fontSize: '20px', color: '#166534', marginBottom: '6px' }}>
              Welcome back{user?.full_name ? `, ${user.full_name}` : ''}! 🌾
            </h2>
            <p style={{ color: '#374151', fontSize: '14px' }}>
              Your farm telemetry, microclimate advisories, and AI agronomic insights are synced in real time.
            </p>
          </div>

          <div className="grid-4" style={{ marginBottom: '20px' }}>
            <div className="stat-box">
              <div className="stat-value">{farms.length}</div>
              <div className="stat-label">Registered Farms</div>
            </div>
            <div className="stat-box">
              <div className="stat-value">{weatherData ? `${weatherData.temperature_c}°C` : '--'}</div>
              <div className="stat-label">{weatherData ? weatherData.forecast : 'Fetching Weather'}</div>
            </div>
            <div className="stat-box">
              <div className="stat-value">{diseaseHistory.length}</div>
              <div className="stat-label">Crop Diagnoses</div>
            </div>
            <div className="stat-box">
              <div className="stat-value">Active</div>
              <div className="stat-label">Gnani & Gemini Engines</div>
            </div>
          </div>

          <div className="grid-2">
            {/* Quick Actions */}
            <div className="card">
              <h3 className="card-title">⚡ Quick Agricultural Actions</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <button className="btn btn-outline" onClick={() => setActiveTab('disease')}>
                  📷 Upload Leaf for Disease Check
                </button>
                <button className="btn btn-outline" onClick={() => setActiveTab('irrigation')}>
                  💧 Run Irrigation Calculation
                </button>
                <button className="btn btn-outline" onClick={() => setActiveTab('fertilizer')}>
                  🌱 Calculate N-P-K Fertilizer Plan
                </button>
                <button className="btn btn-outline" onClick={() => setActiveTab('market')}>
                  📈 Check APMC Mandi Prices
                </button>
              </div>
            </div>

            {/* Weather Snapshot */}
            <div className="card">
              <h3 className="card-title">
                <span>🌦️ Local Microclimate Snapshot</span>
                <span className="badge badge-info">{weatherLocation}</span>
              </h3>
              {weatherData ? (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#15803d' }}>
                      {weatherData.temperature_c}°C
                    </div>
                    <div style={{ textAlign: 'right', fontSize: '13px', color: '#64748b' }}>
                      Humidity: {weatherData.humidity_percent}% • Wind: {weatherData.wind_speed_kmh} km/h
                    </div>
                  </div>
                  <div className="disclaimer-box" style={{ background: '#f0fdf4', borderColor: '#22c55e', color: '#166534' }}>
                    💡 <strong>Spray Window Advisory</strong>: {weatherData.agricultural_advisory}
                  </div>
                  <div style={{ fontSize: '11.5px', color: '#94a3b8', marginTop: '8px' }}>
                    Source: {weatherData.source} • Synced: {new Date(weatherData.retrieved_at).toLocaleTimeString()}
                  </div>
                </div>
              ) : (
                <p>Loading weather telemetry...</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 2. AI AGRONOMIST CHAT VIEW (WITH VOICE & VISION) */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'assistant' && (
        <div className="grid-2">
          {/* Main Chat Panel */}
          <div>
            <div className="card">
              <div className="card-title">
                <span>🤖 AI Agronomist Chat & Voice Engine</span>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {selectedFarm && <span className="badge badge-info">{selectedFarm.name}</span>}
                  {token && chatMessages.length > 1 && (
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: '11px', padding: '3px 8px' }}
                      onClick={() => setChatMessages([initialGreetingMessage])}
                      title="Start a fresh conversation thread"
                    >
                      🗑️ Clear Chat
                    </button>
                  )}
                </div>
              </div>

              {!token ? (
                <div style={{ padding: '24px', textAlign: 'center' }}>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>
                    Please log in to chat with the AI Agronomist and run voice interactions.
                  </p>
                  <button className="btn btn-primary" onClick={() => setActiveTab('settings')}>
                    Go to Sign In
                  </button>
                </div>
              ) : (
                <div>
                  {/* Quick Query Pills */}
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '5px 8px' }} onClick={() => handleSendChat('What is the recommended irrigation schedule for my tomato crop?')}>
                      💧 Irrigation Schedule
                    </button>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '5px 8px' }} onClick={() => handleSendChat('Give me a basal NPK fertilizer recommendation for tomato.')}>
                      🌱 Fertilizer Dose
                    </button>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '5px 8px' }} onClick={() => handleSendChat('What is the weather forecast and spraying advisory?')}>
                      🌤️ Weather Forecast
                    </button>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '5px 8px' }} onClick={() => handleSendChat('What are current Mandi market prices for tomato?')}>
                      📊 Mandi Market Rates
                    </button>
                  </div>

                  {/* Chat Messages */}
                  <div className="chat-thread">
                    {chatMessages.map((msg, index) => (
                      <div key={index} style={{ display: 'flex', flexDirection: 'column' }}>
                        <div className={`chat-bubble ${msg.sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-agent'}`}>
                          {msg.imagePreview && (
                            <img 
                              src={msg.imagePreview} 
                              alt="Crop photo" 
                              style={{ width: '160px', height: '110px', objectFit: 'cover', borderRadius: '8px', marginBottom: '8px', display: 'block' }} 
                            />
                          )}
                          <div>{msg.text}</div>
                          {msg.sender === 'agent' && (
                            <div style={{ marginTop: '8px' }}>
                              <button 
                                className="btn btn-secondary" 
                                style={{ fontSize: '11px', padding: '3px 8px' }}
                                onClick={() => playSpeechAudio(msg.text)}
                                disabled={isSynthesizing}
                                title="Listen with Gnani AI Timbre TTS"
                              >
                                {isSynthesizing ? '⏳ Generating Audio...' : '🔊 Listen (Gnani Voice)'}
                              </button>
                            </div>
                          )}
                        </div>

                        {/* Tool Assessment Result Cards */}
                        {msg.assessment && (
                          <div className="assessment-card">
                            <div className="assessment-header">
                              <div>
                                <div className="assessment-title">🩺 {msg.assessment.possible_condition}</div>
                                <div style={{ fontSize: '13px', color: '#64748b' }}>
                                  Severity: <strong>{msg.assessment.severity}</strong> • Likelihood: <strong>{msg.assessment.assessment_level}</strong>
                                </div>
                              </div>
                              {msg.assessment.is_mock && <span className="badge badge-mock">Dev Mock Mode</span>}
                            </div>
                            <div className="assessment-section">
                              <div className="assessment-subtitle">Recommended Organic & Cultural Control</div>
                              <ul className="assessment-list">
                                {msg.assessment.treatment?.map((t, i) => <li key={i}>{t}</li>)}
                              </ul>
                            </div>
                            <div className="disclaimer-box">⚠️ {msg.assessment.disclaimer}</div>
                          </div>
                        )}

                        {msg.irrigation && (
                          <div className="assessment-card" style={{ background: '#f0f9ff', borderColor: '#bae6fd' }}>
                            <div className="assessment-title" style={{ color: '#0369a1' }}>💧 Smart Irrigation Schedule</div>
                            <p style={{ marginTop: '4px' }}><strong>Water Requirement:</strong> {msg.irrigation.water_requirement}</p>
                            <p><strong>Recommended Interval:</strong> {msg.irrigation.irrigation_interval}</p>
                            <p style={{ marginTop: '6px' }}>{msg.irrigation.recommended_action}</p>
                          </div>
                        )}

                        {msg.fertilizer && (
                          <div className="assessment-card" style={{ background: '#f0fdf4', borderColor: '#bbf7d0' }}>
                            <div className="assessment-title" style={{ color: '#15803d' }}>🧪 N-P-K Nutrient Plan ({msg.fertilizer.crop} • {msg.fertilizer.growth_stage})</div>
                            <p style={{ marginTop: '4px' }}><strong>Nutrient Focus:</strong> {msg.fertilizer.nutrient_focus}</p>
                            <ul className="assessment-list">
                              {msg.fertilizer.recommendation?.map((r, i) => <li key={i}>{r}</li>)}
                            </ul>
                          </div>
                        )}

                        {msg.weather && (
                          <div className="assessment-card" style={{ background: '#f8fafc', borderColor: '#cbd5e1' }}>
                            <div className="assessment-title" style={{ color: '#0f172a' }}>🌦️ Weather Advisory ({msg.weather.location})</div>
                            <p style={{ marginTop: '4px' }}><strong>Conditions:</strong> {msg.weather.temperature_c}°C • Humidity {msg.weather.humidity_percent}% • {msg.weather.forecast}</p>
                            <p style={{ marginTop: '4px' }}>{msg.weather.agricultural_advisory}</p>
                          </div>
                        )}

                        {msg.market && (
                          <div className="assessment-card" style={{ background: '#fffbeb', borderColor: '#fde68a' }}>
                            <div className="assessment-title" style={{ color: '#92400e' }}>📊 Mandi Price Reference ({msg.market.commodity})</div>
                            <p style={{ marginTop: '4px' }}><strong>Modal Price:</strong> ₹{msg.market.modal_price} ({msg.market.unit}) • {msg.market.mandi}</p>
                            <p style={{ marginTop: '4px' }}>{msg.market.advisory}</p>
                          </div>
                        )}

                        {msg.knowledge && (
                          <div className="assessment-card" style={{ background: '#faf5ff', borderColor: '#e9d5ff' }}>
                            <div className="assessment-title" style={{ color: '#6b21a8' }}>📚 {msg.knowledge.source_document}</div>
                            <p style={{ marginTop: '4px', fontSize: '13px' }}>{msg.knowledge.relevant_section}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {loadingText && (
                    <div style={{ color: '#15803d', fontSize: '13px', marginBottom: '10px' }}>
                      ⏳ {loadingText}
                    </div>
                  )}

                  {voiceProcessingText && (
                    <div style={{ color: '#0284c7', fontSize: '13px', marginBottom: '10px' }}>
                      🎙️ {voiceProcessingText}
                    </div>
                  )}

                  {/* Image Preview Thumbnail */}
                  {imagePreviewUrl && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                      <img src={imagePreviewUrl} alt="Preview" style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: '6px' }} />
                      <span style={{ fontSize: '12px', color: '#64748b' }}>Leaf photo attached.</span>
                      <button className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => { setSelectedImageB64(''); setImagePreviewUrl(''); }}>Remove</button>
                    </div>
                  )}

                  {/* Input Controls & Voice Record Button */}
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {/* Microphone Record Button */}
                    <button 
                      className={`btn-mic ${isRecording ? 'recording' : ''}`}
                      onClick={isRecording ? stopRecording : startRecording}
                      disabled={isTranscribing}
                      style={isTranscribing ? { opacity: 0.6, cursor: 'not-allowed' } : undefined}
                      title={
                        isTranscribing
                          ? "Transcribing speech..."
                          : isRecording
                            ? "Stop Recording & Transcribe"
                            : "Click to Speak (Gnani AI STT)"
                      }
                    >
                      🎤
                    </button>

                    {/* Image Attachment Button */}
                    <label className="btn btn-secondary" style={{ cursor: 'pointer', padding: '10px 12px' }} title="Attach Leaf Image">
                      📷
                      <input type="file" accept="image/*" onChange={handleImageFileChange} style={{ display: 'none' }} />
                    </label>

                    {/* Text Input */}
                    <input 
                      className="form-input"
                      placeholder={`Ask question in ${language === 'te' ? 'Telugu' : language === 'hi' ? 'Hindi' : 'English'}...`}
                      value={chatInput}
                      onChange={e => setChatInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleSendChat()}
                    />

                    <button className="btn btn-primary" onClick={() => handleSendChat()}>Send</button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Side Context Panel */}
          <div>
            <div className="card">
              <h3 className="card-title">🌾 Active Cadastral Context</h3>
              {selectedFarm ? (
                <div>
                  <p><strong>Farm:</strong> {selectedFarm.name}</p>
                  <p><strong>Location:</strong> {selectedFarm.location}</p>
                  <p><strong>Soil:</strong> {selectedFarm.soil_type}</p>
                  <p><strong>Area:</strong> {selectedFarm.area_acres} Acres</p>
                  <div style={{ marginTop: '12px' }}>
                    <span className="badge badge-success">Context Auto-Injected into AI</span>
                  </div>
                </div>
              ) : (
                <p style={{ color: '#64748b' }}>No farm holding selected. Please register a farm in Farm Holdings tab.</p>
              )}
            </div>

            <div className="card">
              <h3 className="card-title">🎙️ Gnani Voice Interaction</h3>
              <p style={{ fontSize: '13px', color: '#475569', lineHeight: '1.5' }}>
                AgriMind integrates official <strong>Gnani AI Prisma (STT)</strong> and <strong>Timbre (TTS)</strong> for seamless Indian regional language interaction in <strong>Telugu</strong>, <strong>Hindi</strong>, and <strong>Indian English</strong>.
              </p>
              <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#334155' }}>Voice Profile:</label>
                  <select 
                    value={selectedVoice} 
                    onChange={e => setSelectedVoice(e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '12px' }}
                  >
                    <option value="Avinash">Avinash (Male - Recommended All-Language)</option>
                    <option value="Shivani">Shivani (Female - Hindi/English/Telugu)</option>
                    <option value="Lakshmi">Lakshmi (Female - Telugu)</option>
                    <option value="Kalpana">Kalpana (Female - Telugu)</option>
                    <option value="Shubham">Shubham (Male - Hindi)</option>
                    <option value="Prakash">Prakash (Male)</option>
                    <option value="Devansh">Devansh (Male)</option>
                  </select>
                </div>
                <div>
                  <button 
                    className="btn btn-outline" 
                    disabled={isSynthesizing}
                    onClick={() => playSpeechAudio(
                      language === 'te' 
                        ? "నమస్కారం! అగ్రిమైండ్ మీకు వ్యవసాయ సహాయం చేయడానికి సిద్ధంగా ఉంది." 
                        : language === 'hi' 
                        ? "नमस्ते! एग्रीमाइंड आपको कृषि सहायता प्रदान करने के लिए तैयार है।" 
                        : "Hello! AgriMind is ready to assist you with smart farming guidance."
                    )}
                  >
                    {isSynthesizing ? '⏳ Generating Audio...' : `🔊 Test Voice (${selectedVoice})`}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 3. CROP DISEASE DETECTION VIEW */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'disease' && (
        <div>
          <div className="card">
            <h2 className="card-title">🌿 Google Gemini Vision — Crop Leaf Pathology Workspace</h2>
            <p style={{ color: '#475569', fontSize: '14px', marginBottom: '16px' }}>
              Upload a clear photograph of the affected plant leaf or stem. The Gemini 2.5 Flash Vision engine analyzes visual lesions, symptoms, severity, and generates ICAR-compliant biological and chemical treatments.
            </p>

            <div className="grid-2">
              <div>
                <div style={{ border: '2px dashed #86efac', padding: '30px', borderRadius: '10px', textAlign: 'center', background: '#f0fdf4' }}>
                  <input type="file" accept="image/*" onChange={handleImageFileChange} style={{ marginBottom: '12px' }} />
                  <p style={{ fontSize: '13px', color: '#166534' }}>
                    Accepted formats: JPEG, PNG, WEBP (Max: 10 MB)
                  </p>
                  {imagePreviewUrl && (
                    <img src={imagePreviewUrl} alt="Leaf" style={{ width: '100%', maxHeight: '240px', objectFit: 'contain', marginTop: '12px', borderRadius: '8px' }} />
                  )}
                </div>
                <div style={{ marginTop: '14px' }}>
                  <button 
                    className="btn btn-primary" 
                    style={{ width: '100%', justifyContent: 'center' }}
                    onClick={() => handleSendChat('Diagnose this crop leaf photo and provide complete management practices.')}
                  >
                    Run Gemini Vision Diagnosis
                  </button>
                </div>
              </div>

              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 'bold', marginBottom: '12px' }}>📜 Diagnostic History ({diseaseHistory.length})</h3>
                {diseaseHistory.length === 0 ? (
                  <p style={{ color: '#64748b', fontSize: '13px' }}>No previous diagnoses recorded for this account.</p>
                ) : (
                  <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
                    {diseaseHistory.map(rep => (
                      <div key={rep.id} style={{ padding: '12px', border: '1px solid #e2e8f0', borderRadius: '8px', marginBottom: '10px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
                          <span>{rep.possible_condition}</span>
                          <span className={`badge ${rep.is_mock ? 'badge-mock' : 'badge-success'}`}>
                            {rep.is_mock ? 'Mock' : 'Gemini'}
                          </span>
                        </div>
                        <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                          Date: {new Date(rep.created_at).toLocaleDateString()} • Likelihood: {rep.assessment_level}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 4. WEATHER DASHBOARD VIEW */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'weather' && (
        <div>
          <div className="card">
            <h2 className="card-title">
              <span>🌦️ Hyperlocal Agro-Meteorological Weather Dashboard</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input 
                  className="form-input" 
                  style={{ width: '220px', padding: '6px 10px', fontSize: '13px' }} 
                  value={weatherLocation} 
                  onChange={e => setWeatherLocation(e.target.value)} 
                  placeholder="Enter location..."
                />
                <button className="btn btn-primary" style={{ padding: '6px 12px' }} onClick={() => fetchWeather(weatherLocation)}>
                  Refresh
                </button>
              </div>
            </h2>

            {weatherData ? (
              <div>
                <div className="grid-4" style={{ marginBottom: '20px' }}>
                  <div className="stat-box">
                    <div className="stat-value">{weatherData.temperature_c}°C</div>
                    <div className="stat-label">Air Temperature</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-value">{weatherData.humidity_percent}%</div>
                    <div className="stat-label">Relative Humidity</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-value">{weatherData.rainfall_mm} mm</div>
                    <div className="stat-label">Precipitation Active</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-value">{weatherData.wind_speed_kmh} km/h</div>
                    <div className="stat-label">Wind Velocity</div>
                  </div>
                </div>

                <div className="card" style={{ background: '#f8fafc', borderColor: '#e2e8f0' }}>
                  <h3 style={{ fontSize: '15px', color: '#0f172a', marginBottom: '8px' }}>
                    🌾 Delta T & Chemical Spray Window Recommendation
                  </h3>
                  <p style={{ color: '#334155', fontSize: '14px', lineHeight: '1.5' }}>
                    {weatherData.agricultural_advisory}
                  </p>
                  <div style={{ marginTop: '12px', fontSize: '12px', color: '#64748b' }}>
                    Telemetry Source: <strong>{weatherData.source}</strong> • Forecast Condition: <strong>{weatherData.forecast}</strong>
                  </div>
                </div>
              </div>
            ) : (
              <p>Loading weather telemetry...</p>
            )}
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 5. SMART IRRIGATION VIEW */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'irrigation' && (
        <div className="grid-2">
          <div className="card">
            <h2 className="card-title">💧 FAO-56 Penman-Monteith Smart Irrigation Engine</h2>
            <div className="form-group">
              <label className="form-label">Select Crop</label>
              <select className="form-select" value={irrCrop} onChange={e => setIrrCrop(e.target.value)}>
                <option value="Tomato">Tomato (Hybrid)</option>
                <option value="Rice">Rice (Paddy)</option>
                <option value="Wheat">Wheat</option>
                <option value="Cotton">Cotton</option>
                <option value="Maize">Maize (Corn)</option>
                <option value="Chilli">Chilli</option>
                <option value="Sugarcane">Sugarcane</option>
                <option value="Potato">Potato</option>
              </select>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Soil Type</label>
                <select className="form-select" value={irrSoil} onChange={e => setIrrSoil(e.target.value)}>
                  <option value="Loam">Loam Soil</option>
                  <option value="Clay">Clay Soil</option>
                  <option value="Black Clay">Black Cotton Soil</option>
                  <option value="Sandy">Sandy Soil</option>
                  <option value="Red Sandy">Red Sandy Loam</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Growth Stage</label>
                <select className="form-select" value={irrStage} onChange={e => setIrrStage(e.target.value)}>
                  <option value="initial">Initial / Seedling</option>
                  <option value="vegetative">Vegetative Canopy</option>
                  <option value="mid_season">Mid-Season / Flowering</option>
                  <option value="late_season">Late Season / Ripening</option>
                </select>
              </div>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Irrigation System</label>
                <select className="form-select" value={irrMethod} onChange={e => setIrrMethod(e.target.value)}>
                  <option value="drip">Drip Irrigation (90% Eff)</option>
                  <option value="sprinkler">Sprinkler Irrigation (75% Eff)</option>
                  <option value="furrow">Furrow / Border (60% Eff)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Field Area (Acres)</label>
                <input className="form-input" type="number" step="0.5" value={irrArea} onChange={e => setIrrArea(e.target.value)} />
              </div>
            </div>

            <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={runIrrigationCalculator}>
              Compute Scientific Irrigation Schedule
            </button>
          </div>

          <div>
            <div className="card">
              <h3 className="card-title">📊 Irrigation Prescription Output</h3>
              {irrResult ? (
                <div>
                  <div className="stat-box" style={{ background: '#f0f9ff', borderColor: '#bae6fd', marginBottom: '16px' }}>
                    <div className="stat-value" style={{ color: '#0369a1', fontSize: '20px' }}>
                      {irrResult.water_requirement}
                    </div>
                    <div className="stat-label">Net Water Requirement</div>
                  </div>
                  <p><strong>Irrigation Interval:</strong> {irrResult.irrigation_interval}</p>
                  <p><strong>Soil Moisture State:</strong> {irrResult.soil_moisture_status}</p>
                  <div className="disclaimer-box" style={{ background: '#f8fafc', borderColor: '#0284c7', color: '#0f172a', marginTop: '12px' }}>
                    <strong>Scientific Reasoning:</strong> {irrResult.reasoning}
                  </div>
                  <p style={{ marginTop: '10px', fontSize: '13px' }}><strong>Action:</strong> {irrResult.recommended_action}</p>
                </div>
              ) : (
                <p style={{ color: '#64748b', fontSize: '13px' }}>Click 'Compute' to calculate FAO-56 Penman-Monteith crop water requirements.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 6. FERTILIZER PLANNER VIEW */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'fertilizer' && (
        <div className="grid-2">
          <div className="card">
            <h2 className="card-title">🧪 ICAR STCR Fertilizer Recommendation Engine</h2>
            <div className="form-group">
              <label className="form-label">Select Crop</label>
              <select className="form-select" value={fertCrop} onChange={e => setFertCrop(e.target.value)}>
                <option value="Tomato">Tomato</option>
                <option value="Rice">Rice (Paddy)</option>
                <option value="Wheat">Wheat</option>
                <option value="Cotton">Cotton</option>
                <option value="Maize">Maize</option>
                <option value="Chilli">Chilli</option>
              </select>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Application Stage</label>
                <select className="form-select" value={fertStage} onChange={e => setFertStage(e.target.value)}>
                  <option value="basal">Basal (At Sowing / Transplanting)</option>
                  <option value="vegetative">Vegetative (Top Dressing)</option>
                  <option value="flowering">Flowering / Fruit Setting</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Soil pH</label>
                <input className="form-input" type="number" step="0.1" value={fertPh} onChange={e => setFertPh(e.target.value)} />
              </div>
            </div>

            <div className="grid-3">
              <div className="form-group">
                <label className="form-label">Soil N Rating</label>
                <select className="form-select" value={fertN} onChange={e => setFertN(e.target.value)}>
                  <option value="low">Low (+25%)</option>
                  <option value="medium">Medium</option>
                  <option value="high">High (-25%)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Soil P Rating</label>
                <select className="form-select" value={fertP} onChange={e => setFertP(e.target.value)}>
                  <option value="low">Low (+25%)</option>
                  <option value="medium">Medium</option>
                  <option value="high">High (-25%)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Soil K Rating</label>
                <select className="form-select" value={fertK} onChange={e => setFertK(e.target.value)}>
                  <option value="low">Low (+25%)</option>
                  <option value="medium">Medium</option>
                  <option value="high">High (-25%)</option>
                </select>
              </div>
            </div>

            <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={runFertilizerPlanner}>
              Calculate N-P-K Commercial Dosages
            </button>
          </div>

          <div>
            <div className="card">
              <h3 className="card-title">📋 Fertilizer Prescription Sheet</h3>
              {fertResult ? (
                <div>
                  <p><strong>Crop:</strong> {fertResult.crop} • <strong>Stage:</strong> {fertResult.growth_stage}</p>
                  <p style={{ marginTop: '4px' }}><strong>Nutrient Focus:</strong> {fertResult.nutrient_focus}</p>
                  <div style={{ marginTop: '12px' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '6px' }}>Commercial Mineral Fertilizer Doses:</div>
                    <ul className="assessment-list">
                      {fertResult.recommendation?.map((rec, i) => <li key={i}>{rec}</li>)}
                    </ul>
                  </div>
                  <div style={{ marginTop: '12px' }}>
                    <strong>Organic Alternative:</strong> {fertResult.organic_option}
                  </div>
                  <div className="disclaimer-box" style={{ marginTop: '12px' }}>
                    <strong>Soil Considerations:</strong> {fertResult.soil_considerations}
                  </div>
                </div>
              ) : (
                <p style={{ color: '#64748b', fontSize: '13px' }}>Click 'Calculate' to generate ICAR STCR fertilizer dosages.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 7. MARKET PRICES VIEW */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'market' && (
        <div>
          <div className="card">
            <h2 className="card-title">
              <span>📊 Real-Time APMC Mandi Market Intelligence</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <select className="form-select" style={{ width: '150px' }} value={mktCommodity} onChange={e => setMktCommodity(e.target.value)}>
                  <option value="Tomato">Tomato</option>
                  <option value="Rice">Rice (Paddy)</option>
                  <option value="Wheat">Wheat</option>
                  <option value="Cotton">Cotton</option>
                  <option value="Chilli">Chilli</option>
                  <option value="Onion">Onion</option>
                  <option value="Potato">Potato</option>
                  <option value="Soybean">Soybean</option>
                </select>
                <button className="btn btn-primary" onClick={runMarketSearch}>Lookup Rates</button>
              </div>
            </h2>

            {mktResult ? (
              <div>
                <div className="grid-3" style={{ marginBottom: '16px' }}>
                  <div className="stat-box">
                    <div className="stat-value" style={{ color: '#15803d' }}>₹{mktResult.modal_price?.toLocaleString()}</div>
                    <div className="stat-label">Modal Price ({mktResult.unit})</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-value">₹{mktResult.minimum_price?.toLocaleString()} - ₹{mktResult.maximum_price?.toLocaleString()}</div>
                    <div className="stat-label">Price Range ({mktResult.unit})</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-value" style={{ fontSize: '18px' }}>{mktResult.trend}</div>
                    <div className="stat-label">7-Day Price Trend</div>
                  </div>
                </div>

                <div className="card" style={{ background: '#f8fafc', borderColor: '#e2e8f0' }}>
                  <p><strong>Mandi:</strong> {mktResult.mandi} ({mktResult.state})</p>
                  <p style={{ marginTop: '6px' }}><strong>Commercial Harvest Advisory:</strong> {mktResult.advisory}</p>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '10px' }}>
                    Data Source: <strong>{mktResult.source}</strong> • Bulletin Date: {mktResult.data_date}
                  </div>
                </div>
              </div>
            ) : (
              <p style={{ color: '#64748b' }}>Select a commodity and click 'Lookup Rates'.</p>
            )}
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 8. FARM MANAGEMENT VIEW */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'farms' && (
        <div className="grid-2">
          <div>
            <div className="card">
              <h2 className="card-title">🌱 Add New Cadastral Farm Holding</h2>
              <form onSubmit={handleCreateFarm}>
                <div className="form-group">
                  <label className="form-label">Farm Holding Name</label>
                  <input className="form-input" placeholder="e.g. Green Valley Farm" value={farmName} onChange={e => setFarmName(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Location / District</label>
                  <input className="form-input" placeholder="e.g. Mandya, Karnataka" value={farmLocation} onChange={e => setFarmLocation(e.target.value)} required />
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Area (Acres)</label>
                    <input className="form-input" type="number" step="0.5" value={farmArea} onChange={e => setFarmArea(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Soil Classification</label>
                    <select className="form-select" value={soilType} onChange={e => setSoilType(e.target.value)}>
                      <option value="Loam">Clay Loam</option>
                      <option value="Black Clay">Black Cotton Soil</option>
                      <option value="Red Sandy">Red Alluvial Sandy</option>
                      <option value="Silt">Silt Soil</option>
                    </select>
                  </div>
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                  + Save Farm Holding
                </button>
              </form>
            </div>

            {selectedFarm && (
              <div className="card">
                <h3 className="card-title">🌾 Register Crop for {selectedFarm.name}</h3>
                <form onSubmit={handleAddCrop}>
                  <div className="form-group">
                    <label className="form-label">Crop Name</label>
                    <input className="form-input" placeholder="e.g. Tomato" value={cropName} onChange={e => setCropName(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Variety / Hybrid</label>
                    <input className="form-input" placeholder="e.g. Arka Rakshak F1" value={cropVariety} onChange={e => setCropVariety(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Planting Date</label>
                    <input className="form-input" type="date" value={cropDate} onChange={e => setCropDate(e.target.value)} />
                  </div>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                    + Register Crop
                  </button>
                </form>
              </div>
            )}
          </div>

          <div>
            <div className="card">
              <h3 className="card-title">📍 Your Farm Holdings ({farms.length})</h3>
              {farms.length === 0 ? (
                <p style={{ color: '#64748b', fontSize: '13px' }}>No farms registered yet. Please add a farm holding on the left.</p>
              ) : (
                farms.map(f => (
                  <div 
                    key={f.id} 
                    style={{
                      padding: '14px',
                      background: selectedFarm?.id === f.id ? 'var(--primary-light)' : 'var(--bg-subtle)',
                      border: selectedFarm?.id === f.id ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                      borderRadius: '8px',
                      marginBottom: '10px',
                      cursor: 'pointer'
                    }}
                    onClick={() => { setSelectedFarm(f); setWeatherLocation(f.location); }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
                      <span>{f.name}</span>
                      <span className="badge badge-info">{f.area_acres} Acres</span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
                      📍 {f.location} • 🪨 {f.soil_type}
                    </div>
                    {f.crops && f.crops.length > 0 && (
                      <div style={{ marginTop: '8px', fontSize: '12px' }}>
                        <strong>Active Crops:</strong> {f.crops.map(c => c.name).join(', ')}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 9. SETTINGS & PROFILE VIEW */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === 'settings' && (
        <div className="grid-2">
          {!user ? (
            <div className="card">
              <h2 className="card-title">{isSignup ? 'Create Farmer Account' : 'Farmer Sign In'}</h2>
              {authError && <div style={{ color: '#ef4444', marginBottom: '10px', fontSize: '13px' }}>⚠️ {authError}</div>}
              <form onSubmit={handleAuthSubmit}>
                {isSignup && (
                  <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input className="form-input" placeholder="Ramesh Kumar" value={authFullName} onChange={e => setAuthFullName(e.target.value)} required />
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <input className="form-input" type="email" placeholder="farmer@agrimind.ai" value={authEmail} onChange={e => setAuthEmail(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Password</label>
                  <input className="form-input" type="password" placeholder="••••••••" value={authPassword} onChange={e => setAuthPassword(e.target.value)} required />
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                  {isSignup ? 'Sign Up' : 'Log In'}
                </button>
              </form>
              <div style={{ marginTop: '14px', textAlign: 'center', fontSize: '13px', color: '#64748b' }}>
                {isSignup ? 'Already registered?' : "Don't have an account?"}{' '}
                <button 
                  onClick={() => setIsSignup(!isSignup)} 
                  style={{ background: 'none', border: 'none', color: '#15803d', cursor: 'pointer', fontWeight: 'bold' }}
                >
                  {isSignup ? 'Log In' : 'Sign Up'}
                </button>
              </div>
            </div>
          ) : (
            <div className="card">
              <h2 className="card-title">👨‍🌾 Farmer Profile</h2>
              <p><strong>Name:</strong> {user.full_name || 'Farmer'}</p>
              <p style={{ marginTop: '4px' }}><strong>Email:</strong> {user.email}</p>
              <p style={{ marginTop: '4px' }}><strong>Role:</strong> {user.role}</p>
              <div style={{ marginTop: '16px' }}>
                <button className="btn btn-danger" onClick={handleLogout}>Log Out</button>
              </div>
            </div>
          )}

          <div className="card">
            <h3 className="card-title">⚙️ System Integrations & Health</h3>
            <p style={{ fontSize: '13px', marginBottom: '8px' }}>
              <strong>API Base URL:</strong> <code>{API_BASE}</code>
            </p>
            <p style={{ fontSize: '13px', marginBottom: '8px' }}>
              <strong>Gemini Vision:</strong>{' '}
              <span
                className={`badge ${
                  geminiStatus?.mode === 'CONNECTED' || geminiStatus?.mode === 'LIVE'
                    ? 'badge-success'
                    : geminiStatus?.mode === 'INVALID_KEY' || geminiStatus?.mode === 'AUTH_FAILED' || geminiStatus?.mode === 'MODEL_ERROR'
                    ? 'badge-danger'
                    : 'badge-warning'
                }`}
              >
                {geminiStatus?.mode || 'NOT_CONFIGURED'}
              </span>{' '}
              {geminiStatus?.status_detail || ''}
            </p>
            <div style={{ margin: '8px 0 12px 0' }}>
              <button 
                className="btn btn-secondary" 
                style={{ fontSize: '11px', padding: '3px 8px' }}
                disabled={isRefreshingHealth}
                onClick={() => checkHealth(true)}
              >
                {isRefreshingHealth ? '⏳ Probing AI Services...' : '🔄 Re-test AI Connectivity'}
              </button>
            </div>
            <p style={{ fontSize: '13px', marginBottom: '8px' }}>
              <strong>Gnani AI Voice:</strong> <span className={`badge ${gnaniStatus?.mode === 'LIVE' ? 'badge-success' : gnaniStatus?.mode === 'AUTH_FAILED' ? 'badge-danger' : 'badge-info'}`}>{gnaniStatus?.mode || (gnaniStatus?.gnani_configured ? 'LIVE' : 'DEMO')}</span> {gnaniStatus?.status_detail || ''}
            </p>
            <p style={{ fontSize: '13px', marginBottom: '8px' }}>
              <strong>Weather Engine:</strong> <span className="badge badge-success">LIVE</span> Open-Meteo & OpenWeatherMap
            </p>
            <p style={{ fontSize: '13px', marginBottom: '8px' }}>
              <strong>Irrigation Engine:</strong> <span className="badge badge-success">OPERATIONAL</span> FAO-56 Penman-Monteith (ETc = ETo × Kc)
            </p>
            <p style={{ fontSize: '13px', marginBottom: '8px' }}>
              <strong>Fertilizer Engine:</strong> <span className="badge badge-success">OPERATIONAL</span> ICAR Soil Test Crop Response (STCR)
            </p>
            <p style={{ fontSize: '13px', marginBottom: '8px' }}>
              <strong>Mandi Benchmark:</strong> <span className="badge badge-success">OPERATIONAL</span> APMC Mandi Dataset (Agmarknet Aligned)
            </p>
            <div className="disclaimer-box" style={{ marginTop: '14px' }}>
              This platform runs in dual-mode: with configured API keys, all calls interact with live Gemini Vision and Gnani APIs; without keys, it operates in transparent development mock mode.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
