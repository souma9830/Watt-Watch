import { useState, useEffect, useRef } from 'react'
import { API_URL, WS_URL } from '../config'

export default function useRoom(roomId, defaultUrl) {
  const [url, setUrl] = useState(defaultUrl)
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [fps, setFps] = useState(0)
  const [frame, setFrame] = useState(null)
  const [rawFrame, setRawFrame] = useState(null)
  
  const [personCount, setPersonCount] = useState(0)
  const [lightStatus, setLightStatus] = useState('OFF')
  const [fanStatus, setFanStatus] = useState('OFF')
  const [monitorStatus, setMonitorStatus] = useState('OFF')
  const [roomStatus, setRoomStatus] = useState('secure')
  const [processingTime, setProcessingTime] = useState(0)
  const [avgBrightness, setAvgBrightness] = useState(0)
  
  const [microzoneData, setMicrozoneData] = useState(null)
  
  const wsRef = useRef(null)
  const fpsCounter = useRef({ count: 0, lastTime: Date.now() })
  
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
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.frame) setFrame(data.frame)
          if (data.raw_frame) setRawFrame(data.raw_frame)
          setPersonCount(data.person_count)
          setLightStatus(data.light_status)
          setFanStatus(data.fan_status)
          setMonitorStatus(data.monitor_status || 'OFF')
          
          if (data.processing_time_ms !== undefined) {
            const serverTime = data.timestamp * 1000
            const now = Date.now()
            const realLatency = Math.max(0, now - serverTime)
            setProcessingTime(realLatency)
          }
          if (data.avg_brightness !== undefined) setAvgBrightness(data.avg_brightness)
          if (data.microzone) setMicrozoneData(data.microzone)
          
          const isWaste = data.person_count === 0 && (data.light_status === 'ON' || data.fan_status === 'ON' || data.monitor_status === 'ON')
          setRoomStatus(isWaste ? 'waste' : 'secure')
          
          fpsCounter.current.count++
          const now = Date.now()
          if (now - fpsCounter.current.lastTime >= 1000) {
            setFps(fpsCounter.current.count)
            fpsCounter.current.count = 0
            fpsCounter.current.lastTime = now
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
    setFrame(null)
  }

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  return {
    roomId, url, setUrl, connected, connecting, fps, frame, rawFrame,
    personCount, lightStatus, fanStatus, monitorStatus, roomStatus, setRoomStatus, 
    processingTime, avgBrightness, microzoneData, connect, disconnect
  }
}
