import { useState, useEffect, useRef } from 'react'
import './App.css'
import { API_URL } from './config'
import useRoom from './hooks/useRoom'

import CalibrationStudio from './components/CalibrationStudio'
import MonitorTab from './components/MonitorTab'
import DashboardTab from './components/DashboardTab'
import PrivacyTab from './components/PrivacyTab'
import DatabaseTab from './components/DatabaseTab'

function App() {
  const [activeTab, setActiveTab] = useState('monitor')
  const [runningTime, setRunningTime] = useState(0)
  const [calibrationData, setCalibrationData] = useState({})
  const [calibrationLoading, setCalibrationLoading] = useState(false)
  const [energyDashboard, setEnergyDashboard] = useState({})
  const [privacyAssurance, setPrivacyAssurance] = useState({})
  const [dbInfo, setDbInfo] = useState({})
  const [dbSchema, setDbSchema] = useState({ tables: [] })
  const [browsedTable, setBrowsedTable] = useState(null)
  const [browsedRows, setBrowsedRows] = useState([])
  const [browsing, setBrowsing] = useState(false)
  
  const room1 = useRoom('room-101', 'http://192.168.0.154:8080/video')
  const room2 = useRoom('room-102', 'http://192.168.0.155:8080/video')
  
  const [demoMode, setDemoMode] = useState(false)
  const [privacyEnabled, setPrivacyEnabled] = useState(true)
  const [showRaw, setShowRaw] = useState(false)
  
  const [alertEvents, setAlertEvents] = useState([])
  const [energyMetrics, setEnergyMetrics] = useState({})
  
  const startTime = useRef(Date.now())

  useEffect(() => {
    const timer = setInterval(() => {
      setRunningTime(Math.floor((Date.now() - startTime.current) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (activeTab === 'calibration') {
      fetchCalibration()
    }
    if (activeTab === 'dashboard') {
      fetchEnergyDashboard()
    }
    if (activeTab === 'privacy') {
      fetchPrivacyAssurance()
    }
    if (activeTab === 'database') {
      fetchDatabaseData()
    }
  }, [activeTab])

  const fetchEnergyDashboard = async () => {
    try {
      const res = await fetch(`${API_URL}/api/energy/dashboard`)
      const data = await res.json()
      setEnergyDashboard(data)
    } catch (err) {
      console.error('Failed to fetch energy dashboard:', err)
    }
  }

  const fetchPrivacyAssurance = async () => {
    try {
      const res = await fetch(`${API_URL}/api/privacy/assurance`)
      const data = await res.json()
      setPrivacyAssurance(data)
    } catch (err) {
      console.error('Failed to fetch privacy assurance:', err)
    }
  }

  const fetchDatabaseData = async () => {
    try {
      const [infoRes, schemaRes] = await Promise.all([
        fetch(`${API_URL}/api/database/info`),
        fetch(`${API_URL}/api/database/schema`)
      ])
      const info = await infoRes.json()
      const schema = await schemaRes.json()
      setDbInfo(info)
      setDbSchema(schema)
    } catch (err) {
      console.error('Failed to fetch database data:', err)
    }
  }

  const fetchDatabaseRows = async (tableName) => {
    setBrowsing(true)
    setBrowsedTable(tableName)
    try {
      const res = await fetch(`${API_URL}/api/database/rows/${tableName}`)
      const data = await res.json()
      setBrowsedRows(data.rows || [])
    } catch (err) {
      console.error('Failed to browse table:', err)
    } finally {
      setBrowsing(false)
    }
  }

  const fetchCalibration = async () => {
    setCalibrationLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/calibration`)
      const data = await res.json()
      setCalibrationData(data)
    } catch (err) {
      console.error('Failed to fetch calibration:', err)
    }
    setCalibrationLoading(false)
  }

  const updateCalibration = async (roomId, dayDark, dayMedium, nightDark, nightMedium) => {
    try {
      const res = await fetch(`${API_URL}/api/calibration`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id: roomId,
          day_dark: dayDark,
          day_medium: dayMedium,
          night_dark: nightDark,
          night_medium: nightMedium
        })
      })
      const data = await res.json()
      if (data.status === 'success') {
        fetchCalibration()
      }
    } catch (err) {
      console.error('Failed to update calibration:', err)
    }
  }

  useEffect(() => {
    // Only fetch alerts/metrics if at least one room is connected
    if (!room1.connected && !room2.connected) return
    const fetchData = async () => {
      try {
        const [eventsRes, metricsRes] = await Promise.all([
          fetch(`${API_URL}/api/alerts/events?limit=8`),
          fetch(`${API_URL}/api/energy/metrics`)
        ])
        const eventsData = await eventsRes.json()
        setAlertEvents(eventsData.events || [])
        const metricsData = await metricsRes.json()
        setEnergyMetrics(metricsData.rooms || {})
      } catch (err) {}
    }
    fetchData()
    const interval = setInterval(fetchData, 4000)
    return () => clearInterval(interval)
  }, [room1.connected, room2.connected])

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const startDemo = (scenario) => {
    setDemoMode(true)
    const stat = scenario === 'empty-room-appliances-on' ? 'waste' : 'secure'
    room1.setRoomStatus(stat)
    room2.setRoomStatus(stat)
  }

  const stopDemo = () => setDemoMode(false)

  return (
    <div className="dashboard">
      <header className="main-header">
        <div className="branding">
          <div className="logo-section">
            <span className="logo-main">CAM SENSE</span>
            <span className="logo-sub">INTEL_MONITORING V2.0</span>
          </div>
          <div className="status-badge pulse">SYSTEM_ACTIVE</div>
        </div>

        <div className="telemetry">
          <div className="tele-item">
            <span className="label">UPTIME</span>
            <span className="val">{formatTime(runningTime)}</span>
          </div>
          <div className="tele-item">
            <span className="label">AVG_FPS</span>
            <span className="val">{Math.max(room1.fps, room2.fps)}</span>
          </div>
          <div className="tele-item">
            <span className="label">LATENCY</span>
            <span className="val">{(room1.connected || room2.connected) ? `${Math.max(room1.processingTime, room2.processingTime).toFixed(0)}ms` : '---'}</span>
          </div>
        </div>

        <nav className="header-nav">
          <button className={`nav-btn ${activeTab === 'monitor' ? 'active' : ''}`} onClick={() => setActiveTab('monitor')}>◈ MONITOR</button>
          <button className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>◈ SUMMARY</button>
          <button className={`nav-btn ${activeTab === 'privacy' ? 'active' : ''}`} onClick={() => setActiveTab('privacy')}>◈ PRIVACY</button>
          <button className={`nav-btn ${activeTab === 'calibration' ? 'active' : ''}`} onClick={() => setActiveTab('calibration')}>◈ CALIBRATE</button>
          <button className={`nav-btn ${activeTab === 'database' ? 'active' : ''}`} onClick={() => setActiveTab('database')}>◈ DATABASE</button>
        </nav>
      </header>

      {activeTab === 'monitor' && (
        <MonitorTab 
          room1={room1} room2={room2}
          privacyEnabled={privacyEnabled} setPrivacyEnabled={setPrivacyEnabled}
          demoMode={demoMode} startDemo={startDemo} showRaw={showRaw}
          energyMetrics={energyMetrics} alertEvents={alertEvents}
        />
      )}

      {activeTab === 'calibration' && (
        <CalibrationStudio 
          room1={room1} 
          room2={room2} 
          calibrationData={calibrationData} 
          onUpdate={updateCalibration}
          onRefresh={fetchCalibration}
          loading={calibrationLoading}
        />
      )}

      {activeTab === 'dashboard' && (
        <DashboardTab energyDashboard={energyDashboard} fetchEnergyDashboard={fetchEnergyDashboard} />
      )}

      {activeTab === 'privacy' && (
        <PrivacyTab privacyAssurance={privacyAssurance} fetchPrivacyAssurance={fetchPrivacyAssurance} />
      )}

      {activeTab === 'database' && (
        <DatabaseTab 
          dbSchema={dbSchema} dbInfo={dbInfo} 
          browsedTable={browsedTable} setBrowsedTable={setBrowsedTable} 
          fetchDatabaseData={fetchDatabaseData} fetchDatabaseRows={fetchDatabaseRows} 
          browsing={browsing} browsedRows={browsedRows} 
        />
      )}
    </div>
  )
}

export default App