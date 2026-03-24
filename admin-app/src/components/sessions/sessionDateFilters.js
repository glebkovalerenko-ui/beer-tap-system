function startOfDay(localDate) {
  const date = new Date(localDate);
  date.setHours(0, 0, 0, 0);
  return date;
}

function endOfDay(localDate) {
  const date = new Date(localDate);
  date.setHours(23, 59, 59, 999);
  return date;
}

function parseFilterDay(value, boundary) {
  if (!value) return null;
  const day = new Date(`${value}T00:00:00`);
  if (Number.isNaN(day.getTime())) return null;
  return boundary === 'end' ? endOfDay(day) : startOfDay(day);
}

export function resolveDateBounds(filters, getPeriodBounds) {
  const preset = filters?.periodPreset || 'today';
  const base = preset === 'range' ? filters : { ...filters, ...getPeriodBounds(preset) };
  const start = parseFilterDay(base?.dateFrom, 'start');
  const end = parseFilterDay(base?.dateTo, 'end');

  if (!start && !end) return null;
  if (!start) return { start: startOfDay(end), end };
  if (!end) return { start, end: endOfDay(start) };
  if (start.getTime() <= end.getTime()) return { start, end };

  return { start: startOfDay(end), end: endOfDay(start) };
}

function toSessionDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function matchesSessionDateRange(item, bounds, now = new Date()) {
  if (!bounds) return true;

  const openedAt = toSessionDate(item?.opened_at || item?.lifecycle?.opened_at);
  const lastEventAt = toSessionDate(
    item?.last_event_at
      || item?.lifecycle?.last_event_at
      || item?.lifecycle?.last_pour_ended_at
      || item?.updated_at
      || item?.opened_at
  );

  const intervalStart = openedAt || lastEventAt;
  if (!intervalStart) return false;

  // Product rule: active sessions are shown if their active interval intersects the selected period.
  // This keeps a long-lived active visit visible even when history is pre-filtered by the backend.
  const intervalEnd = item?.isActive ? (lastEventAt && lastEventAt > now ? lastEventAt : now) : (lastEventAt || openedAt);

  return intervalStart.getTime() <= bounds.end.getTime() && intervalEnd.getTime() >= bounds.start.getTime();
}
