import React from 'react'

export default function DatabaseTab({ 
  dbSchema, dbInfo, 
  browsedTable, setBrowsedTable, 
  fetchDatabaseData, fetchDatabaseRows, 
  browsing, browsedRows 
}) {
  return (
    <div className="dashboard-grid">
      <aside className="sidebar-left">
        <section className="ctrl-group">
          <h4 className="section-title">DATABASE_EXPLORER</h4>
          <button 
            className={`btn ${!browsedTable ? 'btn-primary' : 'btn-outline'}`} 
            onClick={() => {setBrowsedTable(null); fetchDatabaseData()}}
            style={{ width: '100%', marginBottom: '8px' }}
          >
            SCHEMA_VIEW
          </button>
          <p style={{ fontSize: '10px', opacity: 0.6 }}>SELECT_TABLE_TO_BROWSE:</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px' }}>
            {(dbSchema.tables || []).map(t => (
              <button 
                key={t.name}
                className={`btn ${browsedTable === t.name ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => fetchDatabaseRows(t.name)}
                style={{ fontSize: '9px', textAlign: 'left', padding: '8px' }}
              >
                {t.name.toUpperCase()}
              </button>
            ))}
          </div>
        </section>
      </aside>

      <main className="main-viewport">
        {!browsedTable ? (
          /* Schema View */
          <div style={{ padding: '20px' }}>
            <div className="glass-card" style={{ borderLeft: '3px solid var(--accent-neon)' }}>
              <h4 className="card-title">◈ ACTIVE_STORAGE_LOCATION</h4>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '4px', fontFamily: 'monospace', fontSize: '11px', color: 'var(--accent-neon)' }}>
                {dbInfo.db_path || 'data/wattwatch.db'}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginTop: '20px' }}>
              {Object.entries(dbInfo.tables || {}).map(([name, count]) => (
                <div key={name} className="glass-card" style={{ textAlign: 'center', cursor: 'pointer' }} onClick={() => fetchDatabaseRows(name)}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{count}</div>
                  <div style={{ fontSize: '9px', opacity: 0.5, marginTop: '4px' }}>{name.toUpperCase()}</div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '20px' }}>
              <h4 className="section-title">◈ SCHEMA_MAP</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                {(dbSchema.tables || []).map((table) => (
                  <div key={table.name} className="glass-card" style={{ padding: '0' }}>
                    <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px 12px', fontSize: '10px', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between' }}>
                      <span>TABLE: {table.name.toUpperCase()}</span>
                    </div>
                    <div style={{ padding: '10px' }}>
                      {table.columns.slice(0, 5).map((col) => (
                        <div key={col.name} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', marginBottom: '4px', opacity: 0.8 }}>
                          <span>{col.name}</span>
                          <span style={{ opacity: 0.4 }}>{col.type}</span>
                        </div>
                      ))}
                      {table.columns.length > 5 && <div style={{ fontSize: '9px', opacity: 0.3, textAlign: 'center' }}>+ {table.columns.length - 5} MORE</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Data Browser View */
          <div style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <h4 className="section-title" style={{ margin: 0 }}>◈ BROWSER // {browsedTable.toUpperCase()}</h4>
              <button className="btn btn-outline" style={{ fontSize: '9px' }} onClick={() => fetchDatabaseRows(browsedTable)}>REFRESH_ROWS</button>
            </div>

            <div className="glass-card" style={{ flex: 1, padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              {browsing ? (
                <div style={{ padding: '40px', textAlign: 'center', opacity: 0.5 }}>FETCHING_RECORDS...</div>
              ) : browsedRows.length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center', opacity: 0.5 }}>NO_RECORDS_FOUND</div>
              ) : (
                <div style={{ overflow: 'auto', flex: 1 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px', textAlign: 'left' }}>
                    <thead style={{ position: 'sticky', top: 0, background: '#111', zIndex: 10 }}>
                      <tr>
                        {Object.keys(browsedRows[0] || {}).map(k => (
                          <th key={k} style={{ padding: '10px', borderBottom: '1px solid rgba(255,255,255,0.1)', opacity: 0.6 }}>{k.toUpperCase()}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {browsedRows.map((row, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                          {Object.values(row).map((v, j) => (
                            <td key={j} style={{ padding: '8px 10px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '150px' }}>
                              {typeof v === 'number' && v > 1000000000 ? new Date(v * 1000).toLocaleTimeString() : String(v)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <aside className="sidebar-right">
        <div className="glass-card">
          <h4 className="card-title">◈ DB_HEALTH</h4>
          <div style={{ fontSize: '11px', lineHeight: '1.8' }}>
            <p><span style={{ opacity: 0.6 }}>IO_STATUS:</span> <span style={{ color: '#4ade80' }}>OPTIMIZED</span></p>
            <p><span style={{ opacity: 0.6 }}>JOURNAL:</span> {dbInfo.journal_mode}</p>
            <hr style={{ borderColor: 'rgba(255,255,255,0.1)', margin: '12px 0' }} />
            <p style={{ fontSize: '9px', opacity: 0.5 }}>
              The browser displays the last 50 entries. Timestamps are automatically converted to local time for readability.
            </p>
          </div>
        </div>
        {browsedTable && (
          <div className="glass-card" style={{ marginTop: '15px' }}>
            <h4 className="card-title">◈ TABLE_INFO</h4>
            <div style={{ fontSize: '10px', opacity: 0.8 }}>
              <p>NAME: {browsedTable}</p>
              <p>RECORDS_LOADED: {browsedRows.length}</p>
              <button className="btn btn-outline" style={{ width: '100%', marginTop: '10px', fontSize: '9px' }} onClick={() => setBrowsedTable(null)}>CLOSE_BROWSER</button>
            </div>
          </div>
        )}
      </aside>
    </div>
  )
}
