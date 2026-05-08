import React from 'react'

export default function MonitorTab({ 
  room1, room2, 
  privacyEnabled, setPrivacyEnabled, 
  demoMode, startDemo, showRaw, 
  energyMetrics, alertEvents 
}) {

  const renderRoomControls = (room, nameLabel) => (
    <section className="ctrl-group">
      <h4 className="section-title">{nameLabel}</h4>
      <div className="input-row">
        <input type="text" value={room.url} onChange={(e) => room.setUrl(e.target.value)} disabled={room.connected} />
        {!room.connected ? (
          <button className="btn btn-primary" onClick={room.connect} disabled={room.connecting}>{room.connecting ? '...' : 'CONNECT'}</button>
        ) : (
          <button className="btn btn-danger" onClick={room.disconnect}>DISCONNECT</button>
        )}
      </div>
    </section>
  )

  const renderVideoContainer = (room, title) => {
    const isEnergyWaste = room.roomStatus === 'waste'
    const rMetrics = energyMetrics[room.roomId] || {}
    const potentialWatts = isEnergyWaste && rMetrics.estimated_watts ? rMetrics.estimated_watts : 0

    return (
      <div className="video-container">
        <div className="video-header">
          <span className="v-tag">{title}</span>
          <span className={`v-alert ${room.roomStatus}`}>{room.roomStatus === 'waste' ? '!!! WASTE_DETECTED !!!' : 'SECURE'}</span>
        </div>
        <div className="video-frame">
          {room.frame || demoMode ? (
            <img src={showRaw && room.rawFrame ? room.rawFrame : room.frame} alt={`${title} feed`} className="pixel-stream" />
          ) : (
            <div className="placeholder">OFFLINE</div>
          )}
          <div className="scanline" />
          <div className="corner tl" /><div className="corner tr" />
          <div className="corner bl" /><div className="corner br" />
        </div>
        {isEnergyWaste && (
          <div className="ticker-wrap">
            <div className="ticker-text">WASTE_DETECTION_ACTIVE: REDUCE LOAD BY {potentialWatts}W IMMEDIATELY // TERM_IDLE_APPLIANCES</div>
          </div>
        )}
      </div>
    )
  }

  const renderRoomAnalytics = (room, title) => {
    const rMetrics = energyMetrics[room.roomId] || {}
    const estimatedWatts = room.connected && rMetrics.estimated_watts ? rMetrics.estimated_watts : 0
    const cumulativeCost = room.connected && rMetrics.cumulative_cost ? rMetrics.cumulative_cost : 0
    
    return (
      <div className="glass-card" style={{ marginBottom: '12px' }}>
        <h4 className="card-title">◈ {title} STATS</h4>
        <div className="obj-grid" style={{ marginBottom: '8px' }}>
          <div className="obj-item major"><span className="l">OCCUPANTS</span><span className="v">{room.personCount.toString().padStart(2, '0')}</span></div>
          <div className="obj-item"><span className="l">LUMINANCE</span><span className={`v ${room.lightStatus === 'ON' ? 'on' : ''}`}>{room.lightStatus}</span></div>
          <div className="obj-item"><span className="l">VENTILATION</span><span className={`v ${room.fanStatus === 'ON' ? 'on' : ''}`}>{room.fanStatus}</span></div>
        </div>
        <div className="metrics-stack">
          <div className="m-row"><span className="l">LOAD</span><span className="v">{estimatedWatts}W</span></div>
          <div className={`m-row waste ${cumulativeCost > 0 ? 'active' : ''}`}><span className="l">CUMULATIVE_WASTE</span><span className="v">₹{cumulativeCost.toFixed(4)}</span></div>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-grid">
      <aside className="sidebar-left">
        {renderRoomControls(room1, 'SOURCE // ROOM_101')}
        {renderRoomControls(room2, 'SOURCE // ROOM_102')}

        <section className="ctrl-group">
          <h4 className="section-title">SECURE_FILTERS</h4>
          <div className={`filter-card ${privacyEnabled ? 'active' : ''}`}>
            <label className="checkbox-wrap">
              <input type="checkbox" checked={privacyEnabled} onChange={(e) => setPrivacyEnabled(e.target.checked)} />
              <span className="check-label">GHOST_MODE</span>
            </label>
            <p className="filter-desc">{privacyEnabled ? 'PIXEL_PROTECT_ENABLED' : 'RAW_FEED_EXPOSED'}</p>
          </div>
        </section>

        <section className="ctrl-group">
          <h4 className="section-title">TEST_SEQUENCES</h4>
          <div className="demo-btns">
            <button className="btn btn-outline" onClick={() => startDemo('empty-room-appliances-on')}>EMIT_WASTE</button>
            <button className="btn btn-outline" onClick={() => startDemo('occupied-normal')}>EMIT_NORMAL</button>
          </div>
        </section>
      </aside>

      <main className="main-viewport multi-room">
        {renderVideoContainer(room1, 'ROOM_101 // WEST_WING')}
        {renderVideoContainer(room2, 'ROOM_102 // EAST_WING')}
      </main>

      <aside className="sidebar-right">
        {renderRoomAnalytics(room1, 'ROOM_101')}
        {renderRoomAnalytics(room2, 'ROOM_102')}

        <div className="glass-card history">
          <h4 className="card-title">◈ RECENT_ALERTS</h4>
          <div className="event-list">
            {alertEvents.length > 0 ? alertEvents.map((e, i) => (
              <div key={i} className="event-item">
                <span className="t">[{new Date(e.timestamp * 1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false})}] {e.room_id}</span>
                <span className="d">{Math.floor(e.duration_seconds)}S</span>
              </div>
            )) : (
              <div className="event-item" style={{ borderLeftColor: 'transparent', textAlign: 'center' }}>
                <span className="t" style={{width: '100%', opacity: 0.5}}>NO ALERTS DETECTED</span>
              </div>
            )}
          </div>
        </div>
      </aside>
    </div>
  )
}
