// src/stores/guestStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeError } from '../lib/errorUtils';
import { notifyForbiddenIfNeeded } from '../lib/forbidden.js';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createGuestStore() {
  const { subscribe, set, update } = writable({
    guests: [],
    loading: false,
    isLoading: false,
    lastFetchedAt: null,
    staleTtlMs: 30000,
    error: null,
  });
  let guestsInFlight = null;

  return {
    subscribe,

    fetchGuests: async ({ force = false, staleTtlMs = null } = {}) => {
      const token = get(sessionStore).token;
      if (!token) {
        set({ guests: [], loading: false, isLoading: false, lastFetchedAt: null, staleTtlMs: 30000, error: null });
        console.warn('Загрузка гостей отменена: отсутствует токен авторизации.');
        return [];
      }

      const state = get({ subscribe });
      const ttlMs = Number.isFinite(staleTtlMs) ? Number(staleTtlMs) : state.staleTtlMs;
      const hasFreshData = state.lastFetchedAt && (Date.now() - state.lastFetchedAt) < ttlMs;
      if (!force && hasFreshData && state.guests.length > 0) {
        return state.guests;
      }
      if (guestsInFlight) {
        return guestsInFlight;
      }

      update((s) => ({ ...s, loading: true, isLoading: true, error: null }));
      try {
        guestsInFlight = invoke('get_guests', { token });
        const guests = await guestsInFlight;
        set({ ...state, guests, loading: false, isLoading: false, lastFetchedAt: Date.now(), error: null });
        return guests;
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.fetchGuests', error);
        set({ ...state, guests: [], loading: false, isLoading: false, error: errorMessage });
        throw new Error(errorMessage);
      } finally {
        guestsInFlight = null;
      }
    },

    createGuest: async (guestData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Требуется повторный вход в систему');

      update((s) => ({ ...s, loading: true, isLoading: true, error: null }));
      try {
        const newGuest = await invoke('create_guest', { token, guestData });
        update((s) => ({
          ...s,
          guests: [...s.guests, newGuest].sort((a, b) => a.last_name.localeCompare(b.last_name)),
          loading: false,
          isLoading: false,
        }));
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.createGuest', error);
        update((s) => ({ ...s, loading: false, isLoading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    updateGuest: async (guestId, guestData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Требуется повторный вход в систему');

      update((s) => ({ ...s, loading: true, isLoading: true, error: null }));
      try {
        const updatedGuest = await invoke('update_guest', { token, guestId, guestData });
        update((s) => {
          const updatedGuests = s.guests.map((g) => (g.guest_id === guestId ? updatedGuest : g));
          return { ...s, guests: updatedGuests, loading: false, isLoading: false };
        });
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.updateGuest', error);
        update((s) => ({ ...s, loading: false, isLoading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    bindCardToGuest: async (guestId, cardUid) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Требуется повторный вход в систему');

      update((s) => ({ ...s, error: null }));
      try {
        const updatedGuest = await invoke('bind_card_to_guest', { token, guestId, cardUid });
        update((s) => {
          const updatedGuests = s.guests.map((g) => (g.guest_id === guestId ? updatedGuest : g));
          return { ...s, guests: updatedGuests };
        });
      } catch (error) {
        notifyForbiddenIfNeeded(error);
        const errorMessage = toErrorMessage('guestStore.bindCardToGuest', error);
        update((s) => ({ ...s, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    topUpBalance: async (guestId, topUpData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Требуется повторный вход в систему');

      update((s) => ({ ...s, loading: true, isLoading: true, error: null }));
      try {
        const updatedGuest = await invoke('top_up_balance', { token, guestId, topUpData });
        update((s) => {
          const updatedGuests = s.guests.map((g) => (g.guest_id === guestId ? updatedGuest : g));
          return { ...s, guests: updatedGuests, loading: false, isLoading: false };
        });
      } catch (error) {
        const errorMessage = toErrorMessage('guestStore.topUpBalance', error);
        update((s) => ({ ...s, loading: false, isLoading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },
  };
}

export const guestStore = createGuestStore();
