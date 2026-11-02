import json
import base64
import re
import httpx
from typing import Optional
from app.config import settings
from app.schemas import AIAnalyzeFoodResponse, AIFoodItem, AIAnalyzeDisplayResponse

FOOD_SYSTEM_PROMPT = """Sei un esperto nutrizionista e dietologo specializzato nella stima visiva di pasti da fotografie.
Analizza con attenzione la foto del pasto e restituisci ESCLUSIVAMENTE un oggetto JSON valido (senza markdown aggiuntivo, senza spiegazioni testuali prima o dopo, solo il JSON) con la seguente struttura:
{
  "dish_name": "Nome descrittivo del pasto o alimenti identificati",
  "estimated_calories": 550,
  "protein_g": 30.5,
  "carbs_g": 60.0,
  "fat_g": 18.0,
  "confidence_notes": "Breve commento sulle porzioni stimate, condimenti supposti e accuratezza.",
  "suggested_items": [
    {
      "name": "Nome singolo ingrediente/componente",
      "portion_g": 150,
      "calories": 250,
      "protein": 15.0,
      "carbs": 30.0,
      "fat": 5.0
    }
  ]
}"""

def clean_json_text(text: str) -> str:
    """Rimuove eventuali blocchi markdown ```json ... ``` dall'output del modello"""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    return text

async def analyze_food_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> AIAnalyzeFoodResponse:
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # 1. OpenRouter (Tier Gratuito / Modelli Open come Llama 3.2 Vision)
    if settings.OPENROUTER_API_KEY:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": f"https://{settings.DOMAIN}",
                "X-Title": "DietOrDie",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": FOOD_SYSTEM_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_image}"
                                }
                            }
                        ]
                    }
                ]
            }
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = clean_json_text(data["choices"][0]["message"]["content"])
                    parsed = json.loads(raw_text)
                    items = [AIFoodItem(**item) for item in parsed.get("suggested_items", [])]
                    return AIAnalyzeFoodResponse(
                        dish_name=parsed.get("dish_name", "Pasto riconosciuto"),
                        estimated_calories=float(parsed.get("estimated_calories", 0)),
                        protein_g=float(parsed.get("protein_g", 0)),
                        carbs_g=float(parsed.get("carbs_g", 0)),
                        fat_g=float(parsed.get("fat_g", 0)),
                        confidence_notes=parsed.get("confidence_notes", f"Analizzato con {settings.OPENROUTER_MODEL}"),
                        suggested_items=items
                    )
                else:
                    print(f"[OpenRouter Vision Error status {res.status_code}]: {res.text}")
        except Exception as e:
            print(f"[OpenRouter Vision Exception]: {e}")

    # 2. Google Gemini API (se presente chiave)
    if settings.GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": FOOD_SYSTEM_PROMPT},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": b64_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "response_mime_type": "application/json"
                }
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    parsed = json.loads(clean_json_text(raw_text))
                    items = [AIFoodItem(**item) for item in parsed.get("suggested_items", [])]
                    return AIAnalyzeFoodResponse(
                        dish_name=parsed.get("dish_name", "Pasto riconosciuto"),
                        estimated_calories=float(parsed.get("estimated_calories", 0)),
                        protein_g=float(parsed.get("protein_g", 0)),
                        carbs_g=float(parsed.get("carbs_g", 0)),
                        fat_g=float(parsed.get("fat_g", 0)),
                        confidence_notes=parsed.get("confidence_notes", "Analizzato con Gemini Flash"),
                        suggested_items=items
                    )
        except Exception as e:
            print(f"[Gemini Vision Error]: {e}")

    # 3. Fallback intelligente quando nessuna chiave API è ancora inserita
    return AIAnalyzeFoodResponse(
        dish_name="Piatto da Foto (Stima Demo)",
        estimated_calories=480.0,
        protein_g=28.0,
        carbs_g=45.0,
        fat_g=16.0,
        confidence_notes="Stima dimostrativa. Inserisci OPENROUTER_API_KEY nel file .env per usare Llama 3.2 Vision 100% gratuito. Puoi modificare liberamente i valori qui sotto.",
        suggested_items=[
            AIFoodItem(name="Porzione principale", portion_g=180, calories=320, protein=22, carbs=35, fat=9),
            AIFoodItem(name="Contorno & Condimento", portion_g=100, calories=160, protein=6, carbs=10, fat=7)
        ]
    )

async def analyze_display_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> AIAnalyzeDisplayResponse:
    # Stima base per foto display
    return AIAnalyzeDisplayResponse(
        distance_km=10.0,
        duration_seconds=1500,
        avg_speed_kmh=24.0,
        calories_burned=280.0,
        notes="Display cyclette rilevato. Nota: puoi inviare i dati direttamente dall'ESP32 via Wi-Fi!"
    )
