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
        const errorMessage = error.message || error.toString();
        set({ guests: [], loading: false, error: errorMessage });
      }
    },
    
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
          const updatedGuests = s.guests.map(g => 
            g.guest_id === guestId ? updatedGuest : g
          );
          return { ...s, guests: updatedGuests, loading: false };
        });

      } catch (error) {
        update(s => ({ ...s, loading: false, error: error.message || error }));
        throw error;
      }
    },
    
    // +++ НАЧАЛО ИЗМЕНЕНИЙ: НОВЫЙ МЕТОД для привязки карты +++
    bindCardToGuest: async (guestId, cardUid) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");

      // КОММЕНТАРИЙ: Мы не устанавливаем loading=true здесь, так как
      // основная "загрузка" - это ожидание карты, что обрабатывается в NFCModal.
      // API-запрос должен быть очень быстрым.
      update(s => ({ ...s, error: null }));
      try {
        // Вызываем новую Tauri-команду, которую мы создадим в Rust.
        const updatedGuest = await invoke('bind_card_to_guest', { 
          token, 
          guestId, 
          cardUid 
        });

        // Используем наш стандартный паттерн "оптимистичного" обновления.
        // Бэкенд возвращает обновленного гостя, и мы заменяем его в сторе.
        update(s => {
          const updatedGuests = s.guests.map(g =>
            g.guest_id === guestId ? updatedGuest : g
          );
          return { ...s, guests: updatedGuests };
        });

      } catch (error) {
        update(s => ({ ...s, error: error.message || error }));
        // Пробрасываем ошибку дальше, чтобы UI мог ее показать.
        throw error;
      }
    },
    // +++ КОНЕЦ ИЗМЕНЕНИЙ +++
  };
}

export const guestStore = createGuestStore();