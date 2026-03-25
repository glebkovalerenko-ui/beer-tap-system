const DEFAULT_TONE = 'neutral';

export function createQuickActionDescriptor({
  id,
  title,
  description,
  disabled = false,
  tone = DEFAULT_TONE,
  priority = 0,
}) {
  return {
    id,
    title,
    description,
    disabled,
    tone,
    priority,
  };
}

export function orderQuickActionDescriptors(actions = [], orderedIds = []) {
  const orderMap = new Map(orderedIds.map((id, index) => [id, index]));
  return [...actions].sort((left, right) => {
    const leftOrder = orderMap.get(left.id) ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = orderMap.get(right.id) ?? Number.MAX_SAFE_INTEGER;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    return (left.priority ?? 0) - (right.priority ?? 0);
  });
}
