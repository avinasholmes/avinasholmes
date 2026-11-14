export const signalScore = raw => typeof raw === 'number' && Number.isFinite(raw) ? Math.max(0, Math.min(100, 50 + raw / 2)) : null;
export function direction(score) {return score === null ? 'missing' : Math.round(score) >= 55 ? 'bullish' : Math.round(score) <= 45 ? 'bearish' : 'neutral';}
export function freshness(snapshot, now = Date.now()) {
  if(snapshot.mode==='awaiting_feed') return 'unconfigured';
  const age = now - Date.parse(snapshot.as_of);
  if (!Number.isFinite(age) || age < -60000) return 'invalid';
  if (snapshot.mode !== 'live') return 'historical';
  return age > 120000 ? 'stale' : 'live';
}
export function validateSnapshot(data) {
  if (!data || data.schema_version !== 1 || !Array.isArray(data.rows) || !Number.isFinite(Date.parse(data.as_of))) throw new Error('Unsupported snapshot format');
  const seen = new Set();
  for (const row of data.rows) {
    const key = `${row.ticker}:${row.horizon_minutes}`;
    if (!row.ticker || !row.name || !row.sector || ![5,10].includes(row.horizon_minutes) || seen.has(key)) throw new Error('Invalid or duplicate stock record');
    if (row.score !== null && (typeof row.score !== 'number' || !Number.isFinite(row.score) || Math.abs(row.score)>100)) throw new Error('Invalid score');
    if (row.score === null && !row.reason) throw new Error('Missing exclusion reason');
    if (Date.parse(row.as_of)!==Date.parse(data.as_of) || Date.parse(row.forecast_end)!==Date.parse(row.as_of)+row.horizon_minutes*60000) throw new Error('Inconsistent forecast window');
    seen.add(key);
  }
  if (data.rows.length !== data.universe_count * 2) throw new Error('Incomplete universe coverage');
  return data;
}
