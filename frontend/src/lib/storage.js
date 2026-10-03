// Everything the app keeps in this browser (localStorage). All access is wrapped,
// so a blocked or full storage never breaks the UI.

const HISTORY_KEY = "docuguide.history";
const CHECKS_KEY = "docuguide.checks";
export const MAX_HISTORY = 20;

export const loadHistory = () => {
  try {
    const list = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
};

// pinned conversations first (in their current order), then the most recent others
export const orderHistory = (list) => [...list.filter((h) => h.pinned), ...list.filter((h) => !h.pinned)];

export const saveHistory = (list) => {
  const ordered = orderHistory(list);
  const pinned = ordered.filter((h) => h.pinned);
  const rest = ordered.filter((h) => !h.pinned).slice(0, Math.max(MAX_HISTORY - pinned.length, 5));
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify([...pinned, ...rest]));
  } catch {
    /* storage unavailable: history is just not kept */
  }
};

// Document checklist ticks, keyed by guide + document name
export const loadChecks = () => {
  try {
    return JSON.parse(localStorage.getItem(CHECKS_KEY) || "{}") || {};
  } catch {
    return {};
  }
};

export const saveChecks = (checks) => {
  try {
    localStorage.setItem(CHECKS_KEY, JSON.stringify(checks));
  } catch {
    /* storage unavailable: the ticks just are not remembered */
  }
};
