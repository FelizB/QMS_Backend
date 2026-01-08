from typing import List
from fastapi import APIRouter, Depends, HTTPException, FastAPI
from sqlalchemy.orm import Session
from backend_app.db import session
from backend_app.db.models.user import User
from backend_app.db.schema.userSchema import UserCreate, UserOut, UserSummary, UserUpdate

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = session.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE
@router.post("/", response_model=UserOut)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check for empty fields
    for field, value in user_in.dict().items():
        if isinstance(value, str) and not value.strip():
            raise HTTPException(status_code=400, detail=f"{field} cannot be empty")

    db_user = User(**user_in.dict())

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        # Handle unique constraint or other DB errors
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")

    return db_user

# READ (all users)
@router.get("/", response_model=List[UserSummary])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    if not users:
        raise HTTPException(status_code=404, detail="No record available")
    return users

# READ (single user)
@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# UPDATE
@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Apply updates only for provided fields
    for field, value in user_in.dict(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user

# DELETE
@router.delete("/{user_id}", response_model=dict)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"The user with id {user_id} was deleted successfully"}