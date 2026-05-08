import { useState, useEffect } from 'react'

export default function CalibrationStudio({ room1, room2, calibrationData, onUpdate, onRefresh, loading }) {
  const [selectedRoomId, setSelectedRoomId] = useState('room-101')
  const [mode, setMode] = useState('day') // 'day' or 'night'
  
  const currentRoom = selectedRoomId === 'room-101' ? room1 : room2
  const roomCalib = (calibrationData.rooms || {})[selectedRoomId] || {}
  
  const [dark, setDark] = useState(80)
  const [medium, setMedium] = useState(160)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const data = mode === 'day' ? roomCalib.day : roomCalib.night
    setDark(data?.dark_threshold || (mode === 'day' ? 80 : 40))
    setMedium(data?.medium_threshold || (mode === 'day' ? 160 : 100))
  }, [roomCalib, mode])

  const handleSave = () => {
    const dDark = mode === 'day' ? dark : (roomCalib.day?.dark_threshold || 80)
    const dMed = mode === 'day' ? medium : (roomCalib.day?.medium_threshold || 160)
    const nDark = mode === 'night' ? dark : (roomCalib.night?.dark_threshold || 40)
    const nMed = mode === 'night' ? medium : (roomCalib.night?.medium_threshold || 100)
    
    onUpdate(selectedRoomId, dDark, dMed, nDark, nMed)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const luminancePercent = (currentRoom.avgBrightness / 255) * 100

  return (
    <div className="calib-studio">
      <div className="calib-preview-panel">
        <header>
          <h2 className="studio-title">LUMINANCE_STUDIO_V1</h2>
          <p className="studio-subtitle">REAL_TIME_THRESHOLD_CALIBRATION // {selectedRoomId.toUpperCase()}</p>
        </header>

        <div className="video-container" style={{ flex: 1, maxHeight: '60%' }}>
          <div className="video-header">
            <span className="v-tag">LIVE_FEED // CALIBRATION_REFERENCE</span>
            <span className="v-alert secure">LUM: {currentRoom.avgBrightness?.toFixed(1)}</span>
          </div>
          <div className="video-frame">
            {currentRoom.frame ? (
              <img src={currentRoom.frame} alt="Calibration feed" className="pixel-stream" />
            ) : (
              <div className="placeholder">CONNECT CAMERA TO VIEW LIVE LUMINANCE</div>
            )}
            <div className="scanline" />
          </div>
        </div>

        <div className="glass-card">
          <h4 className="card-title">◈ LIVE_LUMINANCE_METER</h4>
          <div style={{ padding: '20px 0 10px 0' }}>
            <div className="meter-strip">
              <div className="meter-fill" style={{ width: `${luminancePercent}%` }} />
              <div className="meter-cursor" style={{ left: `${luminancePercent}%` }} />
              
              {/* Threshold Markers */}
              <div className="threshold-marker dark" style={{ left: `${(dark/255)*100}%` }}>
                <span className="threshold-label" style={{ color: '#f87171' }}>DARK_{dark}</span>
              </div>
              <div className="threshold-marker medium" style={{ left: `${(medium/255)*100}%` }}>
                <span className="threshold-label" style={{ color: '#60a5fa' }}>MED_{medium}</span>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', opacity: 0.5, marginTop: '5px' }}>
            <span>0 (TOTAL_DARK)</span>
            <span>128</span>
            <span>255 (BLINDING)</span>
          </div>
        </div>
      </div>

      <div className="sidebar-right" style={{ background: 'transparent', border: 'none', padding: 0 }}>
        <div className="calib-controls-scroll">
          <section className="glass-card">
            <h4 className="card-title">◈ SELECT_ROOM</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <button 
                className={`btn ${selectedRoomId === 'room-101' ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => setSelectedRoomId('room-101')}
              >
                ROOM_101
              </button>
              <button 
                className={`btn ${selectedRoomId === 'room-102' ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => setSelectedRoomId('room-102')}
              >
                ROOM_102
              </button>
            </div>
          </section>

          <section className="glass-card">
            <h4 className="card-title">◈ CALIBRATION_MODE</h4>
            <div className="mode-selector">
              <button className={`mode-btn ${mode === 'day' ? 'active' : ''}`} onClick={() => setMode('day')}>DAY_SET</button>
              <button className={`mode-btn ${mode === 'night' ? 'active' : ''}`} onClick={() => setMode('night')}>NIGHT_SET</button>
            </div>
            
            <div className="range-wrap">
              <div className="range-header">
                <span className="l">DARK_THRESHOLD</span>
                <span className="v">{dark}</span>
              </div>
              <input 
                type="range" className="custom-slider" 
                min="0" max="255" value={dark} 
                onChange={(e) => setDark(parseInt(e.target.value))} 
              />
            </div>

            <div className="range-wrap">
              <div className="range-header">
                <span className="l">MEDIUM_THRESHOLD</span>
                <span className="v">{medium}</span>
              </div>
              <input 
                type="range" className="custom-slider" 
                min="0" max="255" value={medium} 
                onChange={(e) => setMedium(parseInt(e.target.value))} 
              />
            </div>

            <button 
              className={`btn ${saved ? 'btn-primary' : 'btn-danger'}`} 
              onClick={handleSave}
              style={{ background: saved ? '' : '#ff003c', color: '#fff' }}
            >
              {saved ? 'SETTINGS_APPLIED' : 'COMMIT_CHANGES'}
            </button>
          </section>

          <section className="glass-card">
            <h4 className="card-title">◈ SYSTEM_STATUS</h4>
            <div style={{ fontSize: '11px', lineHeight: '1.8' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ opacity: 0.6 }}>Current Lum:</span>
                <span style={{ color: 'var(--accent-neon)' }}>{currentRoom.avgBrightness?.toFixed(1)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ opacity: 0.6 }}>Classification:</span>
                <span style={{ color: currentRoom.avgBrightness < dark ? '#f87171' : currentRoom.avgBrightness < medium ? '#60a5fa' : '#4ade80' }}>
                  {currentRoom.avgBrightness < dark ? 'DARK' : currentRoom.avgBrightness < medium ? 'MEDIUM' : 'BRIGHT'}
                </span>
              </div>
              <button 
                className="btn btn-outline" 
                onClick={onRefresh} 
                style={{ marginTop: '12px', fontSize: '9px' }}
                disabled={loading}
              >
                {loading ? 'RE-SYNCING...' : 'SYNC_FROM_HARDWARE'}
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
