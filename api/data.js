// Supabase 데이터를 서버(Vercel)에서 조회해 전달하는 API.
// 브라우저가 Supabase에 직접 접속하지 않으므로 CORS/네트워크 차단 문제를 피할 수 있다.
const SUPABASE_URL = process.env.SUPABASE_URL || 'https://prndaklscarhlhkkylce.supabase.co';
const SUPABASE_KEY = process.env.SUPABASE_KEY || 'sb_publishable_trNU_a81MDiyAQ3WfPR0aA_b8H45RfQ';
const PAGE = 1000;

async function fetchAll(table, select) {
  const rows = [];
  for (let from = 0; ; from += PAGE) {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}?select=${encodeURIComponent(select)}`, {
      headers: { apikey: SUPABASE_KEY, Range: `${from}-${from + PAGE - 1}` },
    });
    const text = await res.text();
    if (!res.ok) {
      if ([520, 521, 522, 523, 540, 544].includes(res.status)) {
        throw new Error(`Supabase 서버가 응답하지 않습니다 (HTTP ${res.status}). 프로젝트가 일시정지 상태이거나 복구 중입니다. 잠시 후 새로고침하세요.`);
      }
      throw new Error(`${table} 조회 실패 (HTTP ${res.status}): ${text.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').slice(0, 200)}`);
    }
    const batch = JSON.parse(text);
    rows.push(...batch);
    if (batch.length < PAGE) return rows;
  }
}

module.exports = async (req, res) => {
  try {
    const [stats, pool] = await Promise.all([
      fetchAll('channel_stats', 'id,channel_id,subscriber_count,view_count,avg_views,avg_comments,engagement_rate,country,category,collected_at'),
      fetchAll('youtuber_pool', 'channel_id,channel_title'),
    ]);
    res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate=60');
    res.status(200).json({ stats, pool });
  } catch (e) {
    const cause = e.cause ? ` (${e.cause.code || e.cause.message || e.cause})` : '';
    console.error('Supabase 조회 오류:', e.message + cause);
    res.status(502).json({ error: e.message + cause });
  }
};
