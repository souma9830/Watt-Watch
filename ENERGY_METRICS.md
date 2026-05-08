# Energy Metrics Calculation Documentation

This document explains how each energy metric is calculated in the WattWatch system.

---

## 1. Estimated Power (Watts)

### Calculation Formula
```
estimated_watts = (light_watts if light_status == "ON") + (fan_watts if fan_status == "ON")
```

### Backend Implementation (api/main.py:686-688)
```python
light_watts = wattage.get("light", 40) if room.light_status == "ON" else 0
fan_watts = wattage.get("ceiling_fan", 65) if room.fan_status == "ON" else 0
estimated_watts = light_watts + fan_watts
```

### Data Source
- **Config file:** `config.yaml` - `appliance.wattage`
  - Default: `light: 40W`, `ceiling_fan: 65W`
- **Detection:** Real-time status from Roboflow API (light/fan ON/OFF)
- **Status:** ✅ **Dynamic & Production-Ready**

### Frontend Display (App.jsx:213-215)
```javascript
const estimatedWatts = connected && energyMetrics.estimated_watts 
  ? energyMetrics.estimated_watts 
  : (lightStatus === 'ON' ? 40 : 0) + (fanStatus === 'ON' ? 65 : 0)
```
Shows API data when connected, demo fallback when disconnected.

---

## 2. Cost Per Hour ($/hr)

### Calculation Formula
```
cost_per_hour = (estimated_watts / 1000) * electricity_rate
```

### Backend Implementation (api/main.py:690-691)
```python
cost_per_hour = (estimated_watts / 1000) * electricity_rate
```

### Data Source
- **Wattage:** From formula above (sum of active appliances in watts)
- **Conversion:** Divide by 1000 to convert watts to kilowatts
- **Electricity rate:** `config.yaml` - `appliance.electricity_rate`
  - Default: `$0.12` per kWh (configurable)
- **Status:** ✅ **Dynamic & Production-Ready**

### Frontend Display (App.jsx:216-218)
```javascript
const costPerHour = connected && energyMetrics.cost_per_hour 
  ? energyMetrics.cost_per_hour 
  : estimatedWatts / 1000 * 0.12
```

---

## 3. Waste Events

### What It Shows
The count of detected waste events (alerts when room is empty but appliances are ON).

### Backend Implementation
Waste events are tracked by `AlertManager` (src/alert_manager.py):
- Initial delay: 300 seconds (5 minutes) before first alert
- Repeat interval: 3600 seconds (1 hour) for repeat alerts

### Frontend Display (App.jsx:389)
```javascript
<span className="energy-value warning">{alertEvents.length || 0}</span>
```

### Data Source
- **API Endpoint:** `/api/alerts/events?limit=5`
- **Storage:** `output/waste_events.json` (persisted)
- **Status:** ✅ **Dynamic - counts actual events from AlertManager**

---

## 4. Potential Savings ($/hr)

### Calculation Formula
```
potential_savings_per_hour = cost_per_hour (only when room status == "waste")
```

### Backend Implementation (api/main.py:714)
```python
"potential_savings_per_hour": round(cost_per_hour, 4) if room.status == "waste" else 0
```

### Logic
- When room is in **waste state** (empty + appliances ON): shows the hourly cost of running appliances
- When room is **normal**: shows $0.00
- **Status:** ✅ **Dynamic - based on actual room status**

### Frontend Display (App.jsx:220-222)
```javascript
const potentialSavings = connected && energyMetrics.potential_savings_per_hour 
  ? energyMetrics.potential_savings_per_hour 
  : (roomStatus === 'waste' ? costPerHour : 0)
```

---

## 5. Waste Duration

### What It Shows
Total time the room has been in waste state (empty but appliances ON).

### Backend Implementation (api/main.py:694-696)
```python
waste_duration = 0
if detector.alert_manager:
    waste_duration = detector.alert_manager.get_waste_duration(room_id)
```

### Frontend Display (App.jsx:393)
```javascript
<span className="energy-value">{Math.floor(wasteDuration / 60)}m</span>
```

### Data Source
- **API Endpoint:** `/api/alerts/status` returns `waste_duration_seconds`
- **Status:** ✅ **Dynamic - tracked by AlertManager**

---

## 6. Cumulative Cost ($)

### Calculation Formula
```
cumulative_cost = cost_per_hour * waste_hours
```

### Backend Implementation (api/main.py:698-700)
```python
waste_hours = waste_duration / 3600
cumulative_cost = cost_per_hour * waste_hours
```

### Logic
- Tracks total cost incurred due to energy waste over time
- Only accumulates when room is in waste state
- **Status:** ✅ **Dynamic - accumulates actual waste time**

### Frontend Display (App.jsx:219)
```javascript
const cumulativeCost = connected && energyMetrics.cumulative_cost ? energyMetrics.cumulative_cost : 0
```

---

## Configuration (config.yaml)

```yaml
appliance:
  enabled: true
  wattage:
    light: 40         # LED bulb wattage
    ceiling_fan: 65   # Fan wattage
  electricity_rate: 0.12  # $/kWh (make this configurable per region)
```

---

## API Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/energy/metrics` | Full energy metrics per room |
| `GET /api/alerts/status` | Room status, waste duration |
| `GET /api/alerts/events` | List of waste events |

---

## Data Flow

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Roboflow API   │─────▶│  FastAPI Backend │─────▶│  React Frontend │
│  (light/fan ON) │      │  (config-based)  │      │  (real data)    │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │  AlertManager    │
                     │  (waste duration)│
                     └──────────────────┘
```

---

## Production Readiness Status

| Metric | Status | Notes |
|--------|--------|-------|
| Estimated Power | ✅ Ready | Config-based wattage, real detection |
| Cost/Hour | ✅ Ready | Configurable rate, dynamic calculation |
| Waste Events | ✅ Ready | Event count from AlertManager |
| Potential Savings | ✅ Ready | Dynamic based on room status |
| Waste Duration | ✅ Ready | Tracked by AlertManager |
| Cumulative Cost | ✅ Ready | Time-based accumulation |

---

## How to Customize

### 1. Change Appliance Wattage
Edit `config.yaml`:
```yaml
appliance:
  wattage:
    light: 60        # Change to your LED bulb wattage
    ceiling_fan: 75  # Change to your fan wattage
```

### 2. Change Electricity Rate
Edit `config.yaml`:
```yaml
appliance:
  electricity_rate: 0.15  # Your local rate ($/kWh)
```

### 3. Add More Appliances
Extend the wattage config and update API calculation in `api/main.py`.