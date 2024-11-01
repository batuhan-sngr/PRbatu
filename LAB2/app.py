from fastapi import FastAPI, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, List
import json

# Database setup
DATABASE_URL = "sqlite:///D:/Documents/Codes/Python/PR/LAB2/products.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define Product table
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    link = Column(String, unique=True, nullable=False)
    sizes = Column(String, nullable=True)  # Sizes as comma-separated string

Base.metadata.create_all(bind=engine)

# Pydantic models for API validation
class ProductModel(BaseModel):
    name: str
    price: float
    link: str
    sizes: Optional[str] = None

class ProductInDB(ProductModel):
    id: int

    class Config:
        from_attributes = True

# FastAPI app
app = FastAPI()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CRUD Endpoints for Products (Tasks 1-4)
@app.post("/products/", response_model=ProductInDB)
def create_product(product: ProductModel, db: Session = Depends(get_db)):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[ProductInDB])
def read_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    
    return db.query(Product).offset(skip).limit(limit).all()

@app.get("/products/{product_id}", response_model=ProductInDB)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=ProductInDB)
def update_product(product_id: int, product: ProductModel, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in product.model_dump().items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"ok": True}

# File Upload Endpoint (Task 5)
@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    print(contents.decode('utf-8'))  # Print the file contents for demonstration
    return {"filename": file.filename, "message": "File received"}

# WebSocket Chat Room (Task 6)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Simulate commands
            if data.startswith("join_room"):
                await websocket.send_text("Welcome to the chat room!")
            elif data.startswith("send_msg"):
                _, msg = data.split(" ", 1)
                await manager.broadcast(f"User says: {msg}")
            elif data.startswith("leave_room"):
                await websocket.send_text("You have left the chat room.")
                break
            else:
                await websocket.send_text("Unknown command.")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")


