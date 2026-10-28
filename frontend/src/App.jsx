import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000/api/v1';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('agrimind_token') || '');
  const [user, setUser] = useState(null);
  const [farms, setFarms] = useState([]);
  const [selectedFarm, setSelectedFarm] = useState(null);
  const [selectedCrop, setSelectedCrop] = useState(null);
  const [geminiStatus, setGeminiStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('agent'); // 'agent' | 'farms'

  // Auth Form State
  const [isSignup, setIsSignup] = useState(false);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authFullName, setAuthFullName] = useState('');
  const [authError, setAuthError] = useState('');

  // Farm & Crop Creation State
  const [farmName, setFarmName] = useState('');
  const [farmLocation, setFarmLocation] = useState('');
  const [farmArea, setFarmArea] = useState('5.0');
  const [soilType, setSoilType] = useState('Loam');

  const [cropName, setCropName] = useState('');
  const [cropVariety, setCropVariety] = useState('');
  const [cropDate, setCropDate] = useState('2026-03-01');

  // Chat & Agent State
  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'agent',
      text: 'Hello! I am your AI Agronomist assistant. You can ask me agronomic questions, check Mandi market prices, calculate irrigation/fertilizer schedules, check weather alerts, or upload a photo of an affected leaf for disease diagnosis.',
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [selectedImageB64, setSelectedImageB64] = useState('');
  const [imagePreviewUrl, setImagePreviewUrl] = useState('');
  const [loadingStateText, setLoadingStateText] = useState('');
  const [diseaseHistory, setDiseaseHistory] = useState([]);

  useEffect(() => {
    if (token) {
      fetchUser();
      fetchFarms();
      fetchDiseaseHistory();
    }
    checkGeminiHealth();
  }, [token]);

  const checkGeminiHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health/gemini`);
      const data = await res.json();
      setGeminiStatus(data);
    } catch (e) {
      setGeminiStatus({ status: 'offline', message: 'Backend unreachable' });
    }
  };

  const fetchUser = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
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
      if (res.ok) {
        const data = await res.json();
        setDiseaseHistory(data);
      }
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

  const handleImageFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      alert('Only JPEG and PNG image formats are supported.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert('Image file size must be under 10 MB.');
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      const b64 = reader.result;
      setSelectedImageB64(b64);
      setImagePreviewUrl(b64);
    };
    reader.readAsDataURL(file);
  };

  const removeSelectedImage = () => {
    setSelectedImageB64('');
    setImagePreviewUrl('');
  };

  const sendQueryText = (text) => {
    setChatInput(text);
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!chatInput.trim() && !selectedImageB64) return;
    if (!token) {
      alert('Please log in to chat with the AI Agronomist.');
      return;
    }

    const userMsg = {
      sender: 'user',
      text: chatInput || (selectedImageB64 ? '[Uploaded Leaf Photo for Disease Diagnosis]' : ''),
      imagePreview: imagePreviewUrl
    };

    setChatMessages(prev => [...prev, userMsg]);
    const currentPrompt = chatInput;
    const currentImg = selectedImageB64;

    setChatInput('');
    removeSelectedImage();

    setLoadingStateText('Analyzing request & routing to domain tool...');
    const t1 = setTimeout(() => setLoadingStateText('Running agronomy engine calculation...'), 1000);

    try {
      const res = await fetch(`${API_BASE}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: currentPrompt || 'Please diagnose the crop condition in this image.',
          image_b64: currentImg || null,
          farm_id: selectedFarm ? selectedFarm.id : null,
          crop_id: selectedCrop ? selectedCrop.id : null
        })
      });

      clearTimeout(t1);
      setLoadingStateText('');

      const data = await res.json();
      if (!res.ok) {
        setChatMessages(prev => [...prev, {
          sender: 'agent',
          text: `⚠️ ${data.detail || 'Service error occurred while processing request.'}`
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

      if (data.assessment) {
        fetchDiseaseHistory();
      }

    } catch (err) {
      clearTimeout(t1);
      setLoadingStateText('');
      setChatMessages(prev => [...prev, {
        sender: 'agent',
        text: '⚠️ Network error communicating with backend.'
      }]);
    }
  };

  const handleCreateFarm = async (e) => {
    e.preventDefault();
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/farms`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
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
        setFarmLocation('');
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
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
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
        setCropName('');
        setCropVariety('');
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="navbar">
        <div className="brand">
          <span className="brand-icon">🌱</span>
          <div>
            <h1 className="brand-title">Agrimind Agentic</h1>
            <span className="brand-subtitle">Farmer AI Platform • Phase 3 Orchestration</span>
          </div>
        </div>

        <div className="nav-actions">
          {geminiStatus && (
            <span className={`badge ${geminiStatus.status === 'healthy' ? 'badge-success' : 'badge-warning'}`}>
              Gemini API: {geminiStatus.status === 'healthy' ? 'Live Ready' : 'DEMO / MOCK Mode'}
            </span>
          )}
          {user ? (
            <div style={{ display: 'flex', items: 'center', gap: '12px' }}>
              <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                👨‍🌾 {user.full_name || user.email}
              </span>
              <button className="btn btn-secondary" onClick={handleLogout}>Logout</button>
            </div>
          ) : (
            <span className="badge badge-info">Guest Mode</span>
          )}
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="tab-header">
        <button 
          className={`tab-btn ${activeTab === 'agent' ? 'active' : ''}`}
          onClick={() => setActiveTab('agent')}
        >
          🤖 AI Agronomist & 6-Domain Tools
        </button>
        <button 
          className={`tab-btn ${activeTab === 'farms' ? 'active' : ''}`}
          onClick={() => setActiveTab('farms')}
        >
          🌾 Farm Profiles & Crop Records
        </button>
      </div>

      {/* TAB 1: AI AGRONOMIST CHAT */}
      {activeTab === 'agent' && (
        <main className="grid-2">
          {/* Main Chat Panel */}
          <div>
            <div className="card">
              <div className="card-title">
                <span>🤖 AI Agronomist Chat Engine</span>
                {selectedFarm && (
                  <span className="badge badge-info" style={{ fontSize: '11px' }}>
                    Context: {selectedFarm.name}
                  </span>
                )}
              </div>

              {!token ? (
                <div style={{ padding: '24px', textAlign: 'center' }}>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>
                    Please log in to chat with the AI Agronomist and run domain tools.
                  </p>
                  <button className="btn btn-primary" onClick={() => setActiveTab('farms')}>
                    Go to Login Page
                  </button>
                </div>
              ) : (
                <div>
                  {/* Quick Action Intent Buttons */}
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '14px' }}>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '6px 10px' }} onClick={() => sendQueryText('What is the recommended irrigation schedule for my tomato crop?')}>
                      💧 Irrigation Schedule
                    </button>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '6px 10px' }} onClick={() => sendQueryText('Give me a basal NPK fertilizer recommendation for tomato.')}>
                      🌱 Fertilizer Plan
                    </button>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '6px 10px' }} onClick={() => sendQueryText('What is the weather forecast and spraying advisory?')}>
                      🌤️ Weather Forecast
                    </button>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '6px 10px' }} onClick={() => sendQueryText('What are current Mandi market prices for tomato?')}>
                      📊 Mandi Market Rates
                    </button>
                    <button className="btn btn-outline" style={{ fontSize: '12px', padding: '6px 10px' }} onClick={() => sendQueryText('Search knowledge guide on tomato planting depth and soil preparation.')}>
                      📚 Agri Guide (RAG)
                    </button>
                  </div>

                  {/* Chat Messages Thread */}
                  <div className="chat-thread">
                    {chatMessages.map((msg, index) => (
                      <div key={index} style={{ display: 'flex', flexDirection: 'column' }}>
                        <div className={`chat-bubble ${msg.sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-agent'}`}>
                          {msg.imagePreview && (
                            <img 
                              src={msg.imagePreview} 
                              alt="Crop leaf photo" 
                              style={{ width: '160px', height: '120px', objectFit: 'cover', borderRadius: '8px', marginBottom: '8px', display: 'block' }} 
                            />
                          )}
                          <div>{msg.text}</div>
                        </div>

                        {/* Disease Assessment Card */}
                        {msg.assessment && (
                          <div className="assessment-card">
                            <div className="assessment-header">
                              <div>
                                <div className="assessment-title">🩺 {msg.assessment.possible_condition}</div>
                                <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                                  Likelihood: <strong>{msg.assessment.assessment_level}</strong>
                                </div>
                              </div>
                              {msg.assessment.is_mock && <span className="badge badge-mock">DEMO / MOCK Mode</span>}
                            </div>
                            <div className="assessment-section">
                              <div className="assessment-subtitle">Recommended Management</div>
                              <ul className="assessment-list">
                                {msg.assessment.treatment?.map((t, i) => <li key={i}>{t}</li>)}
                              </ul>
                            </div>
                            <div className="disclaimer-box">⚠️ {msg.assessment.disclaimer}</div>
                          </div>
                        )}

                        {/* Irrigation Card */}
                        {msg.irrigation && (
                          <div className="assessment-card" style={{ background: '#f0f9ff', borderColor: '#bae6fd' }}>
                            <div className="assessment-title" style={{ color: '#0369a1' }}>💧 Irrigation Schedule</div>
                            <div style={{ fontSize: '14px', marginTop: '6px' }}>
                              <strong>Water Requirement:</strong> {msg.irrigation.water_requirement}<br />
                              <strong>Interval:</strong> {msg.irrigation.irrigation_interval}<br />
                              <strong>Action:</strong> {msg.irrigation.recommended_action}<br />
                              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Engine: {msg.irrigation.data_source}</span>
                            </div>
                          </div>
                        )}

                        {/* Fertilizer Card */}
                        {msg.fertilizer && (
                          <div className="assessment-card" style={{ background: '#f0fdf4', borderColor: '#bbf7d0' }}>
                            <div className="assessment-title" style={{ color: '#15803d' }}>🌱 Fertilizer Plan ({msg.fertilizer.growth_stage} stage)</div>
                            <div style={{ fontSize: '14px', marginTop: '6px' }}>
                              <strong>Nutrient Focus:</strong> {msg.fertilizer.nutrient_focus}<br />
                              <strong>Recommended Dosage:</strong> {msg.fertilizer.recommendation.join(', ')}<br />
                              <strong>Organic Alternative:</strong> {msg.fertilizer.organic_option}<br />
                              <div className="disclaimer-box" style={{ marginTop: '8px' }}>⚠️ {msg.fertilizer.disclaimer}</div>
                            </div>
                          </div>
                        )}

                        {/* Weather Card */}
                        {msg.weather && (
                          <div className="assessment-card" style={{ background: '#fefce8', borderColor: '#fef08a' }}>
                            <div className="assessment-header">
                              <div className="assessment-title" style={{ color: '#854d0e' }}>🌤️ Weather Forecast — {msg.weather.location}</div>
                              {msg.weather.is_mock && <span className="badge badge-warning">DEMO / MOCK</span>}
                            </div>
                            <div style={{ fontSize: '14px', marginTop: '6px' }}>
                              🌡️ {msg.weather.temperature_c}°C • 💧 {msg.weather.humidity_percent}% Humidity • 💨 {msg.weather.wind_speed_kmh} km/h<br />
                              <strong>Forecast:</strong> {msg.weather.forecast}<br />
                              <strong>Agricultural Advisory:</strong> {msg.weather.agricultural_advisory}<br />
                              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Source: {msg.weather.source}</span>
                            </div>
                          </div>
                        )}

                        {/* Market Card */}
                        {msg.market && (
                          <div className="assessment-card" style={{ background: '#fff7ed', borderColor: '#ffedd5' }}>
                            <div className="assessment-header">
                              <div className="assessment-title" style={{ color: '#c2410c' }}>📊 Mandi Market Price — {msg.market.commodity}</div>
                              <span className="badge badge-warning">DEMO MARKET DATA</span>
                            </div>
                            <div style={{ fontSize: '14px', marginTop: '6px' }}>
                              <strong>Modal Price:</strong> ₹{msg.market.modal_price.toLocaleString()} / quintal<br />
                              <strong>Range:</strong> ₹{msg.market.minimum_price.toLocaleString()} - ₹{msg.market.maximum_price.toLocaleString()} / quintal<br />
                              <strong>Location:</strong> {msg.market.mandi} ({msg.market.state})<br />
                              <strong>Trend:</strong> {msg.market.trend}<br />
                              <strong>Advisory:</strong> {msg.market.advisory}<br />
                              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Source: {msg.market.source} ({msg.market.data_date})</span>
                            </div>
                          </div>
                        )}

                        {/* Knowledge RAG Card */}
                        {msg.knowledge && (
                          <div className="assessment-card" style={{ background: '#faf5ff', borderColor: '#e9d5ff' }}>
                            <div className="assessment-title" style={{ color: '#6b21a8' }}>📚 Agronomy Advisory Knowledge</div>
                            <div style={{ fontSize: '14px', marginTop: '6px', whiteSpace: 'pre-line' }}>
                              {msg.knowledge.answer}
                            </div>
                            <div style={{ fontSize: '12px', color: '#7e22ce', marginTop: '8px', fontWeight: 'bold' }}>
                              📖 Source Document: {msg.knowledge.source_document} ({msg.knowledge.relevant_section})
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Loading Progression Indicator */}
                  {loadingStateText && (
                    <div className="loading-indicator">
                      <span>⏳</span>
                      <span>{loadingStateText}</span>
                    </div>
                  )}

                  {/* Input Form */}
                  <form onSubmit={handleSendMessage}>
                    {imagePreviewUrl && (
                      <div className="image-preview-container">
                        <img src={imagePreviewUrl} alt="Preview" className="image-preview-img" />
                        <button type="button" className="image-remove-btn" onClick={removeSelectedImage}>✕</button>
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                      <label className="btn btn-secondary" style={{ cursor: 'pointer', flexShrink: 0 }}>
                        📷 Attach Photo
                        <input 
                          type="file" 
                          accept="image/jpeg,image/png"
                          style={{ display: 'none' }}
                          onChange={handleImageFileChange}
                        />
                      </label>
                      <input 
                        className="form-input"
                        placeholder="Ask about crops, weather, market rates, irrigation, or attach a leaf photo..."
                        value={chatInput}
                        onChange={e => setChatInput(e.target.value)}
                      />
                      <button type="submit" className="btn btn-primary" style={{ flexShrink: 0 }}>
                        Send
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Disease Reports & Context */}
          <div>
            <div className="card">
              <h2 className="card-title">📜 Saved Disease Reports ({diseaseHistory.length})</h2>
              {!user ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Log in to view saved reports.</p>
              ) : diseaseHistory.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No saved disease reports yet.</p>
              ) : (
                <div style={{ maxHeight: '450px', overflowY: 'auto' }}>
                  {diseaseHistory.map((rep) => (
                    <div key={rep.id} style={{ padding: '14px', background: 'var(--bg-subtle)', borderRadius: '8px', marginBottom: '10px', border: '1px solid var(--border-color)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '15px' }}>
                        <span>🩺 {rep.possible_condition}</span>
                        <span className="badge badge-info">{rep.assessment_level}</span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        📅 {new Date(rep.created_at).toLocaleString()}
                        {rep.is_mock && <span style={{ marginLeft: '8px', color: '#b91c1c' }}>(DEMO / MOCK)</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </main>
      )}

      {/* TAB 2: FARM PROFILES & CROPS */}
      {activeTab === 'farms' && (
        <main className="grid-2">
          {/* Auth & Farm Creation */}
          <div>
            {!user ? (
              <div className="card">
                <h2 className="card-title">
                  {isSignup ? 'Create Farmer Account' : 'Farmer Sign In'}
                </h2>
                {authError && (
                  <div style={{ color: '#ef4444', marginBottom: '12px', fontSize: '14px' }}>
                    ⚠️ {authError}
                  </div>
                )}
                <form onSubmit={handleAuthSubmit}>
                  {isSignup && (
                    <div className="form-group">
                      <label className="form-label">Full Name</label>
                      <input 
                        className="form-input" 
                        placeholder="e.g. Ramesh Kumar"
                        value={authFullName}
                        onChange={e => setAuthFullName(e.target.value)}
                        required
                      />
                    </div>
                  )}
                  <div className="form-group">
                    <label className="form-label">Email Address</label>
                    <input 
                      className="form-input" 
                      type="email" 
                      placeholder="farmer@agrimind.ai"
                      value={authEmail}
                      onChange={e => setAuthEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Password</label>
                    <input 
                      className="form-input" 
                      type="password" 
                      placeholder="••••••••"
                      value={authPassword}
                      onChange={e => setAuthPassword(e.target.value)}
                      required
                    />
                  </div>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                    {isSignup ? 'Sign Up' : 'Log In'}
                  </button>
                </form>
                <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '13px', color: 'var(--text-muted)' }}>
                  {isSignup ? 'Already registered?' : "Don't have an account?"}{' '}
                  <button 
                    onClick={() => setIsSignup(!isSignup)} 
                    style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontWeight: 'bold' }}
                  >
                    {isSignup ? 'Log In' : 'Sign Up'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="card">
                <h2 className="card-title">🌱 Add New Farm Profile</h2>
                <form onSubmit={handleCreateFarm}>
                  <div className="form-group">
                    <label className="form-label">Farm Name</label>
                    <input 
                      className="form-input" 
                      placeholder="e.g. Green River Acres"
                      value={farmName}
                      onChange={e => setFarmName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Location</label>
                    <input 
                      className="form-input" 
                      placeholder="e.g. Mandya, Karnataka"
                      value={farmLocation}
                      onChange={e => setFarmLocation(e.target.value)}
                      required
                    />
                  </div>
                  <div className="grid-2">
                    <div className="form-group">
                      <label className="form-label">Area (Acres)</label>
                      <input 
                        className="form-input" 
                        type="number"
                        step="0.5"
                        value={farmArea}
                        onChange={e => setFarmArea(e.target.value)}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Soil Type</label>
                      <select 
                        className="form-select"
                        value={soilType}
                        onChange={e => setSoilType(e.target.value)}
                      >
                        <option value="Loam">Clay Loam</option>
                        <option value="Black Clay">Black Cotton Soil</option>
                        <option value="Red Sandy">Red Alluvial</option>
                        <option value="Silt">Silt Soil</option>
                      </select>
                    </div>
                  </div>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                    + Save Farm Profile
                  </button>
                </form>
              </div>
            )}
          </div>

          {/* Farms & Crops */}
          <div>
            <div className="card">
              <h2 className="card-title">🌾 Registered Farms ({farms.length})</h2>
              {!user ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Please log in to manage your farms.</p>
              ) : farms.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No farms registered yet.</p>
              ) : (
                <div>
                  {farms.map(farm => (
                    <div 
                      key={farm.id} 
                      style={{
                        padding: '14px',
                        background: selectedFarm?.id === farm.id ? 'var(--primary-light)' : 'var(--bg-subtle)',
                        border: selectedFarm?.id === farm.id ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                        borderRadius: '8px',
                        marginBottom: '10px',
                        cursor: 'pointer'
                      }}
                      onClick={() => setSelectedFarm(farm)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
                        <span>{farm.name}</span>
                        <span className="badge badge-info">{farm.area_acres} Acres</span>
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        📍 {farm.location} • 🪨 {farm.soil_type}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedFarm && (
              <div className="card">
                <h2 className="card-title">🌽 Add Crops for {selectedFarm.name}</h2>
                <form onSubmit={handleAddCrop}>
                  <div className="grid-2">
                    <div className="form-group">
                      <input 
                        className="form-input" 
                        placeholder="Crop Name (e.g. Tomato, Wheat)"
                        value={cropName}
                        onChange={e => setCropName(e.target.value)}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <input 
                        className="form-input" 
                        placeholder="Variety"
                        value={cropVariety}
                        onChange={e => setCropVariety(e.target.value)}
                      />
                    </div>
                  </div>
                  <button type="submit" className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center' }}>
                    + Add Crop Record
                  </button>
                </form>
              </div>
            )}
          </div>
        </main>
      )}
    </div>
  );
}
