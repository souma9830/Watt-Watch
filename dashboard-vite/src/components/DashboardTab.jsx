import React from 'react'

export default function DashboardTab({ energyDashboard, fetchEnergyDashboard }) {
  return (
    <div className="dashboard-grid">
      <aside className="sidebar-left">
        <section className="ctrl-group">
          <h4 className="section-title">ENERGY_SUMMARY</h4>
          <p style={{ fontSize: '11px', opacity: 0.7, marginBottom: '12px' }}>
            Stakeholder one-slide energy impact report
          </p>
          <button className="btn btn-primary" onClick={fetchEnergyDashboard} style={{ width: '100%' }}>
            REFRESH
          </button>
        </section>
      </aside>

      <main className="main-viewport">
        <div style={{ padding: '20px' }}>
          <div className="glass-card" style={{ background: 'linear-gradient(135deg, #1a3a2a 0%, #0d2818 100%)' }}>
            <h4 className="card-title">◈ ANNUAL_PROJECTIONS</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginTop: '16px' }}>
              <div style={{ textAlign: 'center', padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#4ade80' }}>
                  {energyDashboard.projections?.kwh_per_day || 0}
                </div>
                <div style={{ fontSize: '12px', opacity: 0.7, marginTop: '8px' }}>kWh / DAY</div>
              </div>
              <div style={{ textAlign: 'center', padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#fbbf24' }}>
                  ₹{energyDashboard.projections?.inr_per_year || 0}
                </div>
                <div style={{ fontSize: '12px', opacity: 0.7, marginTop: '8px' }}>SAVINGS / YEAR (INR)</div>
              </div>
              <div style={{ textAlign: 'center', padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#60a5fa' }}>
                  {energyDashboard.projections?.co2_per_year_kg || 0}
                </div>
                <div style={{ fontSize: '12px', opacity: 0.7, marginTop: '8px' }}>kg CO₂ / YEAR</div>
              </div>
            </div>
          </div>

          <div className="glass-card" style={{ marginTop: '16px' }}>
            <h4 className="card-title">◈ LAST_30_DAYS</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginTop: '12px' }}>
              <div><span className="l">ENERGY_SAVED</span><span className="v">{energyDashboard.total_energy_saved_kwh || 0} kWh</span></div>
              <div><span className="l">COST_(INR)</span><span className="v">₹{energyDashboard.total_cost_saved_inr || 0}</span></div>
              <div><span className="l">COST_(INR)</span><span className="v">₹{energyDashboard.total_cost_saved_inr || 0}</span></div>
              <div><span className="l">CO2_SAVED</span><span className="v">{energyDashboard.total_co2_saved_kg || 0} kg</span></div>
            </div>
          </div>

          <div style={{ marginTop: '16px' }}>
            <h4 className="section-title" style={{ marginBottom: '12px' }}>◈ BY_ROOM</h4>
            {Object.keys(energyDashboard.rooms || {}).length > 0 ? (
              Object.entries(energyDashboard.rooms).map(([roomId, data]) => (
                <div key={roomId} className="glass-card" style={{ marginBottom: '8px', padding: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 'bold' }}>{roomId.toUpperCase()}</span>
                    <div style={{ display: 'flex', gap: '20px', fontSize: '11px' }}>
                      <span><span style={{ opacity: 0.6 }}>kWh/d:</span> {data.kwh_per_day}</span>
                      <span><span style={{ opacity: 0.6 }}>₹/yr:</span> ₹{data.inr_per_year}</span>
                      <span><span style={{ opacity: 0.6 }}>CO₂/yr:</span> {data.co2_per_year_kg}kg</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="glass-card" style={{ textAlign: 'center', opacity: 0.6 }}>
                No room data available yet
              </div>
            )}
          </div>
        </div>
      </main>

      <aside className="sidebar-right">
        <div className="glass-card">
          <h4 className="card-title">◈ CONFIG</h4>
          <div style={{ fontSize: '11px', lineHeight: '1.8' }}>
            <p><span style={{ opacity: 0.6 }}>Rate (INR):</span> ₹{energyDashboard.config?.electricity_rate_inr || 6.50}/kWh</p>
            <p><span style={{ opacity: 0.6 }}>Rate (INR):</span> ₹{energyDashboard.config?.electricity_rate_inr || 6.50}/kWh</p>
            <p><span style={{ opacity: 0.6 }}>CO₂ Factor:</span> {energyDashboard.config?.co2_factor_kg_per_kwh || 0.71} kg/kWh</p>
            <hr style={{ borderColor: 'rgba(255,255,255,0.1)', margin: '12px 0' }} />
            <p><span style={{ opacity: 0.6 }}>Total Load:</span> {energyDashboard.config?.total_appliance_watts || 140}W</p>
            <p style={{ fontSize: '10px', opacity: 0.5 }}>Light: {energyDashboard.config?.wattage_breakdown?.light || 40}W | Fan: {energyDashboard.config?.wattage_breakdown?.ceiling_fan || 65}W | Monitor: {energyDashboard.config?.wattage_breakdown?.monitor || 35}W</p>
          </div>
        </div>
      </aside>
    </div>
  )
}
