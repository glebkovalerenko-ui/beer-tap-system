const shift = {
  key: 'shift',
  label: 'Смена',
  href: '#/shift',
  navDescription: 'Живой обзор смены: что требует внимания, что происходит на кранах и какое действие нужно прямо сейчас.',
  title: 'Смена',
  description: 'Главный overview смены для оператора: внимание, живые события, KPI и быстрые переходы в действие.',
};

const visits = {
  key: 'visits',
  label: 'Визиты',
  href: '#/visits',
  navDescription: 'Главный рабочий экран по гостям в текущем и недавнем контексте визита.',
  title: 'Визиты',
  description: 'Находите активные и недавние визиты, открывайте детали, переходите к наливам, проблемам и действиям по гостю.',
};

const guests = {
  key: 'guests',
  label: 'Гости',
  href: '#/guests',
  navDescription: 'Карточка человека, карта, баланс, история и быстрые действия без лишнего поиска по системным сущностям.',
  title: 'Гости',
  description: 'Работа с постоянной карточкой гостя: поиск, регистрация, карта, баланс, активный визит и история.',
};

const taps = {
  key: 'taps',
  label: 'Краны',
  href: '#/taps',
  navDescription: 'Текущее состояние точек розлива, активные визиты и быстрые действия по крану.',
  title: 'Краны',
  description: 'Операторская рабочая зона по кранам: статус, текущий налив, гость, кега и быстрые действия.',
};

const lostCards = {
  key: 'lostCards',
  label: 'Потерянные карты',
  href: '#/lost-cards',
  navDescription: 'Быстрый фронтовой сценарий по потерянной карте, перевыпуску и снижению риска.',
  title: 'Потерянные карты',
  description: 'Очередь и lookup по потерянным картам: кого касается, когда помечено и что нужно сделать дальше.',
};

const pours = {
  key: 'pours',
  label: 'Наливы',
  href: '#/pours',
  navDescription: 'Журнал конкретных эпизодов розлива, включая проблемные и непродажные наливы.',
  title: 'Наливы',
  description: 'Операционный журнал налива: фильтры по гостю, крану, статусу, проблемам и детализация жизненного цикла.',
};

const kegsBeverages = {
  key: 'kegsBeverages',
  label: 'Кеги и напитки',
  href: '#/kegs-beverages',
  navDescription: 'Отдельно каталог напитков, отдельно физические кеги и тихий сервисный слой экранов.',
  title: 'Кеги и напитки',
  description: 'Два слоя работы: напиток как каталог и контент, кега как физический запас и назначение на кран.',
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
  navDescription: 'Инженерный и сменный обзор backend, контроллеров, считывателей, экранов и очереди синхронизации.',
  title: 'Система',
  description: 'Технический operational health для старшего смены и инженера: устройства, stale-состояния и очереди.',
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
  description: 'Контекстная настройка guest-facing экранов кранов как secondary operational layer.',
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
  primaryIntroTitle: 'Operator flow',
  primaryIntro: 'Навигация построена вокруг реальных рабочих ситуаций: гость, визит, кран, налив и требующие реакции проблемы.',
  supportTitle: 'Настройки и справка',
  supportIntro: 'Тихий блок для редких настроек, регламентов и вспомогательной информации.',
});
