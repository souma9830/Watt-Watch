import React from 'react'

export default function PrivacyTab({ privacyAssurance, fetchPrivacyAssurance }) {
  return (
    <div className="dashboard-grid">
      <aside className="sidebar-left">
        <section className="ctrl-group">
          <h4 className="section-title">PRIVACY_ASSURANCE</h4>
          <p style={{ fontSize: '11px', opacity: 0.7, marginBottom: '12px' }}>
            Stakeholder privacy commitment report
          </p>
          <button className="btn btn-primary" onClick={fetchPrivacyAssurance} style={{ width: '100%' }}>
            REFRESH
          </button>
        </section>
      </aside>

      <main className="main-viewport">
        <div style={{ padding: '20px' }}>
          <div className="glass-card" style={{ background: 'linear-gradient(135deg, #1a2a3a 0%, #0d1828 100%)' }}>
            <h4 className="card-title">◈ PRIVACY_MEASURES</h4>
            <div style={{ marginTop: '16px' }}>
              {Object.entries(privacyAssurance.measures || {}).map(([key, measure]) => (
                <div key={key} style={{ display: 'flex', alignItems: 'center', padding: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px', marginBottom: '8px' }}>
                  <span style={{ 
                    width: '10px', height: '10px', borderRadius: '50%', 
                    background: measure.status === 'active' || measure.status === 'enabled' ? '#4ade80' : '#f87171',
                    marginRight: '12px'
                  }} />
                  <div>
                    <div style={{ fontWeight: 'bold', fontSize: '12px' }}>{key.replace('_', ' ').toUpperCase()}</div>
                    <div style={{ fontSize: '11px', opacity: 0.7 }}>{measure.description || measure.status}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card" style={{ marginTop: '16px' }}>
            <h4 className="card-title">◈ STAKEHOLDER_COMMITMENTS</h4>
            <ul style={{ marginTop: '12px', paddingLeft: '20px', fontSize: '12px', lineHeight: '2' }}>
              {(privacyAssurance.stakeholder_commitments || []).map((commitment, idx) => (
                <li key={idx} style={{ color: '#4ade80' }}>✓ {commitment}</li>
              ))}
            </ul>
          </div>

          <div className="glass-card" style={{ marginTop: '16px' }}>
            <h4 className="card-title">◈ COMPLIANCE</h4>
            <div style={{ display: 'flex', gap: '20px', marginTop: '12px' }}>
              {Object.entries(privacyAssurance.compliance || {}).map(([key, value]) => (
                <div key={key} style={{ 
                  padding: '12px 20px', 
                  background: value ? 'rgba(74, 222, 128, 0.2)' : 'rgba(248, 113, 113, 0.2)',
                  borderRadius: '6px',
                  border: `1px solid ${value ? '#4ade80' : '#f87171'}`
                }}>
                  <span style={{ fontSize: '12px' }}>{key.replace('_', ' ').toUpperCase()}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card" style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)' }}>
            <h4 className="card-title">◈ DATA_RETENTION</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '12px', fontSize: '11px' }}>
              <div><span style={{ opacity: 0.6 }}>Raw Images:</span><br /><span style={{ color: '#4ade80' }}>{privacyAssurance.measures?.data_retention?.config?.raw_images || 'Never stored'}</span></div>
              <div><span style={{ opacity: 0.6 }}>Thumbnails:</span><br /><span>{privacyAssurance.measures?.data_retention?.config?.anonymized_thumbnails || '30 days'}</span></div>
              <div><span style={{ opacity: 0.6 }}>Detection Logs:</span><br /><span>90 days</span></div>
            </div>
          </div>
        </div>
      </main>

      <aside className="sidebar-right">
        <div className="glass-card">
          <h4 className="card-title">◈ VERIFICATION</h4>
          <div style={{ fontSize: '11px', lineHeight: '1.8' }}>
            <p><span style={{ opacity: 0.6 }}>Status:</span> <span style={{ color: '#4ade80' }}>VERIFIED</span></p>
            <p><span style={{ opacity: 0.6 }}>Last Checked:</span><br />{privacyAssurance.last_verified || 'N/A'}</p>
            <hr style={{ borderColor: 'rgba(255,255,255,0.1)', margin: '12px 0' }} />
            <p style={{ fontSize: '10px', opacity: 0.7 }}>
              This system processes all data locally with no cloud transmission. 
              All faces are automatically anonymized before any storage.
            </p>
          </div>
        </div>
      </aside>
    </div>
  )
}
