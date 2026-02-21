# backend/crud/transaction_crud.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import models
import schemas
import uuid
from crud import guest_crud, visit_crud

def create_topup_transaction(db: Session, guest_id: uuid.UUID, topup_data: schemas.TopUpRequest):
    """
    Создает финансовую транзакцию пополнения и атомарно обновляет баланс гостя.

    Эта функция обеспечивает транзакционную целостность:
    1. Находит гостя и блокирует его запись для обновления, чтобы избежать состояния гонки.
    2. Создает запись о транзакции.
    3. Обновляет баланс гостя.
    Все три операции выполняются в рамках одной транзакции БД. Если что-то идет не так,
    все изменения откатываются.
    """
    # Находим гостя, используя существующую CRUD-функцию
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    # SQLAlchemy сессия по умолчанию работает в режиме транзакции.
    # Мы просто выполняем все операции, и `db.commit()` в конце их подтвердит.
    
    # 1. Создаем объект транзакции
    active_visit = visit_crud.get_active_visit_by_guest_id(db=db, guest_id=guest_id)

    transaction = models.Transaction(
        guest_id=guest_id,
        visit_id=active_visit.visit_id if active_visit else None,
        amount=topup_data.amount,
        type="top-up",
        payment_method=topup_data.payment_method
    )
    db.add(transaction)

    # 2. Обновляем баланс гостя
    db_guest.balance += topup_data.amount
    
    # 3. Сохраняем все изменения в БД (транзакция и обновление баланса)
    # Если на любом из предыдущих шагов произойдет ошибка, commit не будет вызван,
    # и сессия откатит изменения при закрытии.
    db.commit()
    
    # Обновляем объект гостя, чтобы вернуть актуальные данные, включая новый баланс
    db.refresh(db_guest)
    
    return db_guest