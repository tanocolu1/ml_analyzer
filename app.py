import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Configuración desde variables de entorno
ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")
SELLER_ID    = os.getenv("ML_SELLER_ID")
SITE_ID      = os.getenv("ML_SITE_ID", "MLA")
API_BASE_URL = "https://api.mercadolibre.com"

# Inicialización de FastAPI
app = FastAPI(title="ML Listings Analyzer")

# Modelo de datos para la respuesta
class ItemInfo(BaseModel):
    id: str
    title: str
    description: Optional[str]
    price: float
    available_quantity: int
    sold_quantity: int
    listing_type_id: str
    commission_amount: float
    shipping_cost: Optional[float]
    currency_id: str
    category_id: str

def ml_get(endpoint: str, params: dict = None):
    """Helper para llamadas a la API de MercadoLibre."""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    resp = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@app.get("/items", response_model=List[ItemInfo])
def read_items():
    # 1) obtengo mis publicaciones activas
    data = ml_get("/sites/{SITE_ID}/search", params={"seller_id": SELLER_ID})
    items_data = data.get("results", [])

    items_list = []
    for item in items_data:
        item_id = item["id"]
        # ya viene title, price, stock, sold, etc.
        # si necesitás más detalles: haces ml_get("/items/{item_id}") u otros endpoints
        # ...
        items_list.append(ItemInfo(
          id=item_id,
          title=item["title"],
          description=None,  # o llamar a /items/{item_id}/descriptions
          price=item["price"],
          available_quantity=item["available_quantity"],
          sold_quantity=item["sold_quantity"],
          listing_type_id=item["listing_type_id"],
          commission_amount=0.0,   # o tu cálculo con listing_prices
          shipping_cost=None,      # o tu cálculo de envío
          currency_id=item["currency_id"],
          category_id=item["category_id"]
        ))
    return items_list

