import { formatRubAmount } from '../../formatters.js';

export function buildRecentEvents({ guest, visit, lookup, pours }) {
  if (!guest) return [];
  const items = [];
  if (lookup?.is_lost) {
    items.push({ title: 'Карта в статусе lost', description: lookup.lost_card?.comment || 'Нужна проверка и перевыпуск карты.', timestamp: lookup.lost_card?.reported_at });
  }
  if (visit) {
    items.push({ title: 'Активный визит открыт', description: visit.active_tap_id ? `Сейчас есть лок на кране #${visit.active_tap_id}.` : 'Визит активен, локов сейчас нет.', timestamp: visit.opened_at || visit.updated_at });
  }
  for (const pour of (pours || []).slice(0, 4)) {
    items.push({
      title: `Налив ${pour.beverage?.name || ''}`.trim(),
      description: `${pour.tap?.display_name || `Кран #${pour.tap_id || '—'}`} · ${formatRubAmount(pour.amount_charged || 0)}`,
      timestamp: pour.poured_at,
    });
  }
  for (const tx of (guest.transactions || []).slice(0, 3)) {
    items.push({
      title: tx.type || 'Операция по балансу',
      description: `${formatRubAmount(tx.amount || 0)}`,
      timestamp: tx.created_at,
    });
  }
  return items.filter((item) => item.timestamp).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 6);
}
