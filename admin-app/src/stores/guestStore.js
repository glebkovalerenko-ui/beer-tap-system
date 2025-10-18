// src/stores/guestStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';

function createGuestStore() {
  const { subscribe, set, update } = writable({
    guests: [],
    loading: false,
    error: null,
  });

  return {
    subscribe,
    // +++ НАЧАЛО ИЗМЕНЕНИЙ: Возвращаем полную и правильную реализацию fetchGuests +++
    fetchGuests: async () => {
      const token = get(sessionStore).token;
      if (!token) {
        // Если токена нет, это не ошибка, просто мы еще не готовы.
        // Устанавливаем пустой массив, чтобы избежать ошибок в UI.
        set({ guests: [], loading: false, error: null });
        console.warn("fetchGuests called without a token. Aborting.");
        return;
      }
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        const guests = await invoke('get_guests', { token });
        set({ guests, loading: false, error: null });
      } catch (error) {
        const errorMessage = error.message || error.toString();
        set({ guests: [], loading: false, error: errorMessage });
      }
    },
    // +++ КОНЕЦ ИЗМЕНЕНИЙ +++
    
    createGuest: async (guestData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        const newGuest = await invoke('create_guest', { token, guestData });
        update(s => ({
          ...s,
          guests: [...s.guests, newGuest].sort((a, b) => a.last_name.localeCompare(b.last_name)),
          loading: false,
        }));
      } catch (error) {
        update(s => ({ ...s, loading: false, error: error.message || error }));
        throw error;
      }
    },

    updateGuest: async (guestId, guestData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");

      update(s => ({ ...s, loading: true, error: null }));
      try {
        const updatedGuest = await invoke('update_guest', { token, guestId, guestData });
        update(s => {
          const updatedGuests = s.guests.map(g => g.guest_id === guestId ? updatedGuest : g);
          return { ...s, guests: updatedGuests, loading: false };
        });
      } catch (error) {
        update(s => ({ ...s, loading: false, error: error.message || error }));
        throw error;
      }
    },
    
    bindCardToGuest: async (guestId, cardUid) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");

      update(s => ({ ...s, error: null }));
      try {
        const updatedGuest = await invoke('bind_card_to_guest', { token, guestId, cardUid });
        update(s => {
          const updatedGuests = s.guests.map(g => g.guest_id === guestId ? updatedGuest : g);
          return { ...s, guests: updatedGuests };
        });
      } catch (error) {
        update(s => ({ ...s, error: error.message || error }));
        throw error;
      }
    },

    topUpBalance: async (guestId, topUpData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");

      update(s => ({ ...s, loading: true, error: null }));
      try {
        const updatedGuest = await invoke('top_up_balance', { token, guestId, topUpData });
        update(s => {
          const updatedGuests = s.guests.map(g => g.guest_id === guestId ? updatedGuest : g);
          return { ...s, guests: updatedGuests, loading: false };
        });
      } catch (error) {
        update(s => ({ ...s, loading: false, error: error.message || error }));
        throw error;
      }
    },
  };
}

export const guestStore = createGuestStore();