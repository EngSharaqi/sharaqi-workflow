// An append-only store. Event ids are unique.
export function createStore() {
  return { events: [], ids: new Set() };
}

export function append(store, event) {
  if (store.ids.has(event.id)) throw new Error(`duplicate event id: ${event.id}`);
  store.ids.add(event.id);
  store.events.push(event);
  return store;
}

const byTime = (a, b) => (a.at < b.at ? -1 : a.at > b.at ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0);

export function all(store) {
  return [...store.events].sort(byTime);
}

export function byUser(store, userId) {
  return all(store).filter((e) => e.userId === userId);
}
