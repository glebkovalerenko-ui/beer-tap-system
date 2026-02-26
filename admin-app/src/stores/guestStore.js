// src/stores/guestStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeError } from '../lib/errorUtils';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createGuestStore() {
  const { subscribe, set, update } = writable({
    guests: [],
    loading: false,
    error: null,
  });

  return {
    subscribe,

    fetchGuests: async () => {
      const token = get(sessionStore).token;
      if (!token) {
        set({ guests: [], loading: false, error: null });
        console.warn('fetchGuests called without a token. Aborting.');
        return;
      }

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const guests = await invoke('get_guests', { token });
        set({ guests, loading: false, error: null });
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.fetchGuests', error);
        set({ guests: [], loading: false, error: errorMessage });
      }
    },

    createGuest: async (guestData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const newGuest = await invoke('create_guest', { token, guestData });
        update((s) => ({
          ...s,
          guests: [...s.guests, newGuest].sort((a, b) => a.last_name.localeCompare(b.last_name)),
          loading: false,
        }));
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.createGuest', error);
        update((s) => ({ ...s, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    updateGuest: async (guestId, guestData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const updatedGuest = await invoke('update_guest', { token, guestId, guestData });
        update((s) => {
          const updatedGuests = s.guests.map((g) => (g.guest_id === guestId ? updatedGuest : g));
          return { ...s, guests: updatedGuests, loading: false };
        });
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.updateGuest', error);
        update((s) => ({ ...s, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    bindCardToGuest: async (guestId, cardUid) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      update((s) => ({ ...s, error: null }));
      try {
        const updatedGuest = await invoke('bind_card_to_guest', { token, guestId, cardUid });
        update((s) => {
          const updatedGuests = s.guests.map((g) => (g.guest_id === guestId ? updatedGuest : g));
          return { ...s, guests: updatedGuests };
        });
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.bindCardToGuest', error);
        update((s) => ({ ...s, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    topUpBalance: async (guestId, topUpData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const updatedGuest = await invoke('top_up_balance', { token, guestId, topUpData });
        update((s) => {
          const updatedGuests = s.guests.map((g) => (g.guest_id === guestId ? updatedGuest : g));
          return { ...s, guests: updatedGuests, loading: false };
        });
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.topUpBalance', error);
        update((s) => ({ ...s, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },
  };
}

export const guestStore = createGuestStore();
