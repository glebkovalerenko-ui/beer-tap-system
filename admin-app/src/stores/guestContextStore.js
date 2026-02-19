import { writable } from 'svelte/store';

function createGuestContextStore() {
  const { subscribe, set } = writable({
    guestId: null,
    guestName: 'Гость не выбран',
    cardUid: null,
    isActive: null,
  });

  return {
    subscribe,
    setGuest: (guest) => {
      if (!guest) {
        set({ guestId: null, guestName: 'Гость не выбран', cardUid: null, isActive: null });
        return;
      }
      const primaryCard = Array.isArray(guest.cards) && guest.cards.length > 0 ? guest.cards[0] : null;
      set({
        guestId: guest.guest_id,
        guestName: `${guest.last_name} ${guest.first_name}`.trim(),
        cardUid: primaryCard?.card_uid || null,
        isActive: guest.is_active,
      });
    },
    clear: () => set({ guestId: null, guestName: 'Гость не выбран', cardUid: null, isActive: null }),
  };
}

export const guestContextStore = createGuestContextStore();
