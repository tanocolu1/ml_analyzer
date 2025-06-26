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
    # 1) Obtengo la lista de IDs de mis publicaciones
    data = ml_get(f"/users/{SELLER_ID}/items/search")       # :contentReference[oaicite:4]{index=4}
    item_ids = data.get("results", [])

    items_list = []
    for item_id in item_ids:
        # 2) Detalles básicos del ítem
        item = ml_get(f"/items/{item_id}")                  # :contentReference[oaicite:5]{index=5}

        # 3) Descripción (si existe)
        desc_array = ml_get(f"/items/{item_id}/descriptions")  # :contentReference[oaicite:6]{index=6}
        description = desc_array[0]["text"] if desc_array else None

        # 4) Cálculo de comisión de venta
        price = item["price"]
        listing_type = item["listing_type_id"]
        qty = item["available_quantity"]
        fees = ml_get(f"/sites/{SITE_ID}/listing_prices", params={
            "price": price,
            "listing_type_id": listing_type,
            "quantity": qty
        })                                                # :contentReference[oaicite:7]{index=7}
        fee_info = next((f for f in fees if f["listing_type_id"] == listing_type), fees[0])
        commission_amount = fee_info["sale_fee_amount"]

        # 5) Estimación de costo de envío
        ship = item.get("shipping", {})
        if ship.get("free_shipping"):
            shipping_cost = 0.0
        else:
            # Construir 'dimensions' si existen datos de paquete
            dims_obj = item.get("package_dimensions", {})
            if dims_obj:
                dims = f"{dims_obj['height']}x{dims_obj['width']}x{dims_obj['depth']},{dims_obj['weight']}"
            else:
                dims = ""
            ship_opts = ml_get(f"/users/{SELLER_ID}/shipping_options/free", params={
                "dimensions": dims,
                "verbose": True,
                "item_price": price,
                "listing_type_id": listing_type,
                "mode": ship.get("mode"),
                "condition": item.get("condition"),
                "logistic_type": ship.get("logistic_type")
            })                                            # :contentReference[oaicite:8]{index=8}
            # Extraigo el costo (puede venir en 'cost' o en una lista 'costs')
            shipping_cost = (
                ship_opts.get("cost")
                or next((c.get("cost") for c in ship_opts.get("costs", []) if c.get("cost")), None)
            )

        # 6) Armar objeto de respuesta
        items_list.append(ItemInfo(
            id=item_id,
            title=item["title"],
            description=description,
            price=price,
            available_quantity=item["available_quantity"],
            sold_quantity=item["sold_quantity"],
            listing_type_id=listing_type,
            commission_amount=commission_amount,
            shipping_cost=shipping_cost,
            currency_id=item["currency_id"],
            category_id=item["category_id"]
        ))

    return items_list
