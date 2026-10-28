import { createItem } from './item.js';

export class Shelf {
  constructor() {
    this.items = new Map();
    this.nextId = 1;
  }

  add(input) {
    const item = { id: this.nextId, ...createItem(input) };
    this.items.set(item.id, item);
    this.nextId += 1;
    return item;
  }

  get(id) {
    return this.items.get(id) ?? null;
  }

  remove(id) {
    return this.items.delete(id);
  }

  list() {
    return [...this.items.values()];
  }

  get size() {
    return this.items.size;
  }
}
