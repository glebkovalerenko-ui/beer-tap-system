const shift = {
  key: 'shift',
  label: 'Смена',
  href: '#/shift',
  navDescription: 'Живая смена: что требует действия, где идёт налив и куда перейти прямо сейчас.',
  title: 'Смена',
  description: 'Короткая сводка смены: приоритеты, события, KPI и быстрые переходы.',
};

const visits = {
  key: 'visits',
  label: 'Визиты',
  href: '#/visits',
  navDescription: 'Гости и визиты в работе: открыть, продолжить, проверить детали.',
  title: 'Визиты',
  description: 'Открывайте новые и текущие визиты, находите гостя и переходите к деталям, наливам и проблемам.',
};

const guests = {
  key: 'guests',
  label: 'Гости',
  href: '#/guests',
  navDescription: 'Карточка гостя: карта, баланс, визит и быстрые действия.',
  title: 'Гости',
  description: 'Работа с постоянной карточкой гостя: поиск, регистрация, карта, баланс, активный визит и история.',
};

const taps = {
  key: 'taps',
  label: 'Краны',
  href: '#/taps',
  navDescription: 'Состояние кранов, активные гости и ближайшее действие по точке.',
  title: 'Краны',
  description: 'Операторская рабочая зона по кранам: статус, текущий налив, гость, кега и быстрые действия.',
};

const lostCards = {
  key: 'lostCards',
  label: 'Потерянные карты',
  href: '#/lost-cards',
  navDescription: 'Очередь по потерянным картам и переход к гостю или визиту.',
  title: 'Потерянные карты',
  description: 'Очередь по потерянным картам: кого касается, когда отмечено и что делать дальше.',
};

const pours = {
  key: 'pours',
  label: 'Наливы',
  href: '#/pours',
  navDescription: 'Журнал конкретных эпизодов розлива, включая проблемные и непродажные наливы.',
  title: 'Наливы',
  description: 'Журнал налива: фильтры по гостю, крану и статусу, плюс понятные детали по каждому эпизоду.',
};

const kegsBeverages = {
  key: 'kegsBeverages',
  label: 'Кеги и напитки',
  href: '#/kegs-beverages',
  navDescription: 'Каталог напитков, рабочие кеги и экраны кранов.',
  title: 'Кеги и напитки',
  description: 'Напитки как каталог, кеги как физический запас, экраны как отдельный служебный слой.',
};

const incidents = {
  key: 'incidents',
  label: 'Инциденты',
  href: '#/incidents',
  navDescription: 'Очередь проблем, требующих реакции, а не просто технический лог.',
  title: 'Инциденты',
  description: 'Рабочая очередь инцидентов со связями на кран, визит, налив и гостя.',
};

const system = {
  key: 'system',
  label: 'Система',
  href: '#/system',
  navDescription: 'Состояние системы, устройств и очереди обмена без лишней инженерной тревожности.',
  title: 'Система',
  description: 'Операционная сводка по системе: что мешает работе точки, что проверить первым и где нужна эскалация.',
};

const settings = {
  key: 'settings',
  label: 'Настройки',
  href: '#/settings',
  navDescription: 'Редкие административные изменения и конфигурация рабочего места.',
  title: 'Настройки',
  description: 'Сервисные и административные параметры, не относящиеся к ежедневному operator flow.',
};

const help = {
  key: 'help',
  label: 'Справка',
  href: '#/help',
  navDescription: 'Короткие регламенты, роли и рабочие сценарии для смены.',
  title: 'Справка',
  description: 'Подсказки по ролям, регламентам и частым операторским сценариям.',
};

const tapScreens = {
  key: 'tapScreens',
  label: 'Экраны кранов',
  href: '#/kegs-beverages?tab=screens',
  navDescription: 'Тихий сервисный слой экранов кранов из контекста кеги и напитка.',
  title: 'Экраны кранов',
  description: 'Настройка экранов кранов как отдельного служебного слоя.',
};

export const ROUTE_COPY = Object.freeze({
  shift,
  today: shift,
  visits,
  sessions: visits,
  guests,
  cardsGuests: guests,
  taps,
  lostCards,
  pours,
  kegsBeverages,
  incidents,
  tapScreens,
  system,
  settings,
  help,
});

export const SHELL_NAV_COPY = Object.freeze({
  primaryTitle: 'Основные разделы',
  primaryIntroTitle: 'Рабочий контур',
  primaryIntro: 'Сначала гость, визит, кран и наливы. Ниже тихие служебные разделы.',
  supportTitle: 'Настройки и справка',
  supportIntro: 'Редкие настройки, регламенты и вспомогательная информация.',
});
