# backend/main.py
import uuid
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Импортируем все необходимые компоненты из наших модулей
import models, schemas, crud
from database import engine, get_db
from crud import guest_crud, pour_crud

# Эта команда говорит SQLAlchemy создать все таблицы в БД,
# которые описаны в models.py, если их еще не существует.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Beer Tap System API",
    description="API для управления системой автоматизации пивных кранов",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для разработки разрешаем все источники.
    allow_credentials=True,
    allow_methods=["*"], # Разрешаем все методы (GET, POST, и т.д.)
    allow_headers=["*"], # Разрешаем все заголовки
)

# --- Эндпоинты для Гостей (Guests) ---

@app.post("/api/guests/", 
          response_model=schemas.Guest, 
          status_code=status.HTTP_201_CREATED,
          tags=["Guests"])
def create_guest(guest: schemas.GuestCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового гостя в системе.
    
    Проверяет уникальность номера телефона и документа перед созданием.
    """
    # Используем наши новые CRUD-функции для проверки дубликатов
    db_guest_by_doc = guest_crud.get_guest_by_document(db, id_document=guest.id_document)
    if db_guest_by_doc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                            detail="Guest with this ID document already registered")
        
    db_guest_by_phone = guest_crud.get_guest_by_phone(db, phone_number=guest.phone_number)
    if db_guest_by_phone:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                            detail="Guest with this phone number already registered")
    
    # Если проверки пройдены, создаем гостя
    return guest_crud.create_guest(db=db, guest=guest)

@app.get("/api/guests/", response_model=List[schemas.Guest], tags=["Guests"])
def read_guests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Получение списка всех гостей с возможностью пагинации.
    """
    guests = guest_crud.get_guests(db, skip=skip, limit=limit)
    return guests

@app.get("/api/guests/{guest_id}", response_model=schemas.Guest, tags=["Guests"])
def read_guest(guest_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Получение детальной информации о конкретном госте по его ID.
    """
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if db_guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return db_guest

@app.get("/")
def read_root():
    return {"Status": "Beer Tap System Backend is running!"}
    
@app.post("/api/sync/pours/", response_model=schemas.SyncResponse)
def sync_pours(sync_data: schemas.SyncRequest, db: Session = Depends(get_db)):
    response_results = []
    
    for pour_data in sync_data.pours:
        # 1. Проверка на идемпотентность: не создаем дубликат
        existing_pour = pour_crud.get_pour_by_client_tx_id(db, client_tx_id=pour_data.client_tx_id)
        if existing_pour:
            response_results.append(schemas.SyncResult(
                client_tx_id=pour_data.client_tx_id,
                status="accepted",
                reason="duplicate" # Сообщаем, что это дубликат
            ))
            continue # Переходим к следующей транзакции в пакете

        # 2. Здесь в будущем будет проверка баланса карты, ее статуса и т.д.
        # Например, можно будет раскомментировать и доработать:
        # card = card_crud.get_card(db, uid=pour_data.card_uid)
        # if not card or card.balance < pour_data.price_cents:
        #     response_results.append(...)
        #     continue

        # 3. Создаем запись в сессии БД
        pour_crud.create_pour(db, pour=pour_data)
        response_results.append(schemas.SyncResult(
            client_tx_id=pour_data.client_tx_id,
            status="accepted"
        ))

    # 4. Делаем один коммит в конце, чтобы сохранить всю пачку транзакций
    db.commit()
    
    return schemas.SyncResponse(results=response_results)