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
    fetchGuests: async () => {
      const token = get(sessionStore).token;
      if (!token) {
        set({ guests: [], loading: false, error: 'Not authenticated' });
        return;
      }
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        const guests = await invoke('get_guests', { token });
        set({ guests, loading: false, error: null });
      } catch (error) {
        // Проверяем, есть ли у ошибки поле `message`, и сохраняем его.
        // Если нет, сохраняем ошибку как есть (на всякий случай).
        const errorMessage = error.message || error.toString();
        set({ guests: [], loading: false, error: errorMessage });
      }
    },
    
    // НОВЫЙ МЕТОД для создания гостя
    createGuest: async (guestData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        // Вызываем нашу новую Rust-команду
        const newGuest = await invoke('create_guest', { token, guestData });
        
        // Оптимистичное обновление: добавляем нового гостя в список без refetch
        update(s => ({
          ...s,
          guests: [...s.guests, newGuest].sort((a, b) => a.last_name.localeCompare(b.last_name)),
          loading: false,
        }));

      } catch (error) {
        // В случае ошибки, обновляем состояние
        update(s => ({ ...s, loading: false, error: error.message || error }));
        // Пробрасываем ошибку дальше, чтобы компонент формы мог ее обработать
        throw error;
      }
    },
    // Здесь в будущем будут методы addGuest, updateGuest и т.д.
  };
}

export const guestStore = createGuestStore();