import { useState, useEffect, useRef, useCallback } from 'react'
import { API_URL, WS_URL } from '../config'

export default function useRoom(roomId, defaultUrl) {
  const [url, setUrl] = useState(defaultUrl)
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [fps, setFps] = useState(0)
  
  // Direct DOM ref for the <img> element — frame is painted without React re-render
  const imgRef = useRef(null)
  const rawImgRef = useRef(null)
  // Keep last frame src accessible for initial render / fallback
  const frameSrcRef = useRef(null)
  
  const [personCount, setPersonCount] = useState(0)
  const [lightStatus, setLightStatus] = useState('OFF')
  const [fanStatus, setFanStatus] = useState('OFF')
  const [monitorStatus, setMonitorStatus] = useState('OFF')
  const [roomStatus, setRoomStatus] = useState('secure')
  const [processingTime, setProcessingTime] = useState(0)
  const [avgBrightness, setAvgBrightness] = useState(0)
  const [hasFrame, setHasFrame] = useState(false)
  
  const [microzoneData, setMicrozoneData] = useState(null)
  
  const wsRef = useRef(null)
  const fpsCounter = useRef({ count: 0, lastTime: Date.now() })
  // Throttle metadata state updates to ~10 per second to reduce re-renders
  const metaThrottle = useRef(0)
  
  const connect = async () => {
    setConnecting(true)
    try {
      const response = await fetch(`${API_URL}/api/camera/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, room_id: roomId })
      })
      if (!response.ok) { setConnecting(false); return; }
      
      setConnected(true)
      setConnecting(false)
      const ws = new WebSocket(`${WS_URL}/ws/stream/${roomId}`)
      wsRef.current = ws
      ws.binaryType = 'arraybuffer' // no effect here but ensures WS is in optimal mode
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // === ZERO-LATENCY FRAME PAINT: bypass React state entirely ===
          if (data.frame) {
            frameSrcRef.current = data.frame
            if (imgRef.current) {
              imgRef.current.src = data.frame
            }
            if (!hasFrame) setHasFrame(true)
          }
          if (data.raw_frame && rawImgRef.current) {
            rawImgRef.current.src = data.raw_frame
          }

          // === FPS counter (no state, just ref) ===
          fpsCounter.current.count++
          const nowMs = Date.now()
          if (nowMs - fpsCounter.current.lastTime >= 1000) {
            setFps(fpsCounter.current.count)
            fpsCounter.current.count = 0
            fpsCounter.current.lastTime = nowMs
          }

          // === Throttled metadata updates (every ~100ms) ===
          if (nowMs - metaThrottle.current >= 100) {
            metaThrottle.current = nowMs
            setPersonCount(data.person_count)
            setLightStatus(data.light_status)
            setFanStatus(data.fan_status)
            setMonitorStatus(data.monitor_status || 'OFF')
            if (data.avg_brightness !== undefined) setAvgBrightness(data.avg_brightness)
            if (data.microzone) setMicrozoneData(data.microzone)
            if (data.processing_time_ms !== undefined) {
              const serverTime = data.timestamp * 1000
              const realLatency = Math.max(0, nowMs - serverTime)
              setProcessingTime(realLatency)
            }
            const isWaste = data.person_count === 0 && (
              data.light_status === 'ON' || data.fan_status === 'ON' || data.monitor_status === 'ON'
            )
            setRoomStatus(isWaste ? 'waste' : 'secure')
          }
        } catch (err) {}
      }
      ws.onclose = () => setConnected(false)
    } catch (err) { setConnecting(false) }
  }

  const disconnect = async () => {
    if (wsRef.current) wsRef.current.close()
    try { 
      await fetch(`${API_URL}/api/camera/disconnect`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_id: roomId })
      }) 
    } catch (e) {}
    setConnected(false)
    setHasFrame(false)
    frameSrcRef.current = null
    if (imgRef.current) imgRef.current.src = ''
  }

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  return {
    roomId, url, setUrl, connected, connecting, fps,
    imgRef, rawImgRef, frameSrcRef, hasFrame,
    personCount, lightStatus, fanStatus, monitorStatus, roomStatus, setRoomStatus, 
    processingTime, avgBrightness, microzoneData, connect, disconnect
  }
}
