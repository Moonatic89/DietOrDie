import json
import re
from typing import List, Optional, Dict, Any
import httpx

from app.config import settings
from app.models import BodyCompositionLog, UserProfile
from app.schemas import AIProgressReviewResponse
from app.services.metrics import calculate_age


def clean_json_text(text: str) -> str:
    """Rimuove blocchi markdown ```json ... ``` se presenti"""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    return text


def generate_algorithmic_review(
    logs: List[BodyCompositionLog],
    profile: Optional[UserProfile]
) -> AIProgressReviewResponse:
    """Valutazione deterministica e approfondita della composizione corporea se l'LLM non è raggiungibile"""
    if not logs:
        return AIProgressReviewResponse(
            overall_trend="stabile",
            review_markdown="Non ci sono ancora pesate registrate. Effettua la tua prima pesata sulla bilancia smart per iniziare a tracciare i tuoi progressi!",
            key_metrics_summary={},
            recommendations=[
                "Pesati al mattino a digiuno, dopo essere andato in bagno.",
                "Mantieni una buona idratazione costante durante la giornata.",
                "Esegui la pesata sempre nello stesso giorno della settimana."
            ]
        )

    current = logs[0]
    prev = logs[1] if len(logs) > 1 else None

    # Trend calculation
    key_summary: Dict[str, Any] = {
        "current_weight_kg": current.weight_kg,
        "current_fat_pct": current.body_fat_pct,
        "current_muscle_kg": current.muscle_mass_kg,
        "current_visceral_fat": current.visceral_fat,
        "current_water_pct": current.body_water_pct,
    }

    recs = []
    trend = "positivo"

    lines = []
    lines.append(f"### 📊 Valutazione Composizione Corporea ({current.recorded_at.strftime('%d/%m/%Y')})\n")

    if prev:
        d_weight = round(current.weight_kg - prev.weight_kg, 2)
        d_fat = round((current.body_fat_pct or 0) - (prev.body_fat_pct or 0), 1) if current.body_fat_pct and prev.body_fat_pct else None
        d_muscle = round((current.muscle_mass_kg or 0) - (prev.muscle_mass_kg or 0), 2) if current.muscle_mass_kg and prev.muscle_mass_kg else None
        d_visc = round((current.visceral_fat or 0) - (prev.visceral_fat or 0), 1) if current.visceral_fat and prev.visceral_fat else None

        key_summary["delta_weight_kg"] = d_weight
        key_summary["delta_fat_pct"] = d_fat
        key_summary["delta_muscle_kg"] = d_muscle
        key_summary["delta_visceral_fat"] = d_visc

        days_between = (current.recorded_at - prev.recorded_at).days

        lines.append(f"Rispetto all'ultima pesata ({days_between} giorni fa):\n")

        # Weight & Fat analysis
        if d_weight < 0:
            if d_fat is not None and d_fat <= 0:
                lines.append(f"- **Perdita di peso di qualità**: Sei sceso di **{abs(d_weight)} kg** con una riduzione della massa grassa di **{abs(d_fat)}%**.")
                if d_muscle is not None and d_muscle >= -0.3:
                    lines.append(f"- **Massa muscolare protetta**: La massa magra si è mantenuta stabile ({d_muscle:+.2f} kg), segno eccellente che stai bruciando adipe e non muscolo!")
                    trend = "eccellente"
                elif d_muscle is not None and d_muscle < -0.3:
                    lines.append(f"- **Attenzione al catabolismo**: Hai perso {abs(d_muscle)} kg di muscolo. Aumenta l'apporto proteico e mantieni resistenza sui pedali.")
                    trend = "positivo"
            else:
                lines.append(f"- **Calo di peso complessivo**: Hai perso **{abs(d_weight)} kg**. Continua a monitorare la percentuale di grasso.")
        elif d_weight > 0:
            if d_muscle is not None and d_muscle > 0 and (d_fat is None or d_fat <= 0):
                lines.append(f"- **Aumento muscolare pulito**: Il peso è salito di +{d_weight} kg, ma è aumentata la massa muscolare (+{d_muscle} kg) senza incremento di grasso!")
                trend = "eccellente"
            else:
                lines.append(f"- **Variazione di peso**: +{d_weight} kg rispetto all'ultima rilevazione.")
                trend = "stabile"
        else:
            lines.append("- **Peso stabile**: Bilancio calorico in pareggio.")
            trend = "stabile"

        # Visceral fat
        if current.visceral_fat is not None:
            if current.visceral_fat >= 15:
                lines.append(f"- ⚠️ **Grasso viscerale elevato ({current.visceral_fat})**: È il grasso addominale più sensibile all'attività cardio. Continuare con le sessioni costanti in cyclette aiuterà a ridurlo rapidamente.")
                recs.append("Mantieni 3-4 sessioni settimanali di cyclette a ritmo costante (zona aerobica Z2).")
            elif current.visceral_fat >= 10:
                lines.append(f"- **Grasso viscerale ({current.visceral_fat})**: Livello medio-alto. Target ideale sotto quota 9.")
            else:
                lines.append(f"- **Grasso viscerale ottimale ({current.visceral_fat})**: Livello di sicurezza metabolica eccellente.")

            if d_visc is not None and d_visc < 0:
                lines.append(f"  *Ottima notizia*: il grasso viscerale è diminuito di **{abs(d_visc)} punti**!")
    else:
        lines.append(f"Prima rilevazione registrata: **{current.weight_kg} kg**, massa grassa **{current.body_fat_pct or '--'}%**, massa muscolare **{current.muscle_mass_kg or '--'} kg**.")
        lines.append("Questa misurazione farà da baseline fondamentale per confrontare tutti i tuoi progressi futuri.")

    # Hydration note
    if current.body_water_pct is not None:
        if current.body_water_pct < 48:
            lines.append(f"- 💧 **Idratazione ({current.body_water_pct}%)**: Livello leggermente basso. Una lieve disidratazione può far sovrastimare la percentuale di grasso corporeo nella bilancia BIA.")
            recs.append("Aumenta l'introito d'acqua a 2.5 - 3 litri al giorno per misurazioni più accurate e migliore recupero.")
        else:
            lines.append(f"- 💧 **Idratazione ({current.body_water_pct}%)**: Buon livello di idratazione corporea.")

    if not recs:
        recs.append("Mantieni costanza con le uscite in cyclette (almeno 30 minuti a pedalata).")
        recs.append("Garantisci 1.6-2.0g di proteine per kg di massa magra per preservare il muscolo.")
        recs.append("Pesati sempre nelle stesse condizioni orarie (mattina a digiuno).")

    lines.append("\n#### 🎯 Prossimi Obiettivi:")
    for r in recs:
        lines.append(f"- {r}")

    return AIProgressReviewResponse(
        overall_trend=trend,
        review_markdown="\n".join(lines),
        key_metrics_summary=key_summary,
        recommendations=recs
    )


async def analyze_body_composition_progress(
    logs: List[BodyCompositionLog],
    profile: Optional[UserProfile]
) -> AIProgressReviewResponse:
    """Analisi dello storico composizione corporea con OpenRouter LLM, con fallback algoritmico"""
    if not logs:
        return generate_algorithmic_review(logs, profile)

    if not settings.OPENROUTER_API_KEY:
        return generate_algorithmic_review(logs, profile)

    # Prepara il contesto per il modello
    recent_logs = logs[:8]  # Ultime 8 rilevazioni
    logs_data = []
    for l in recent_logs:
        logs_data.append({
            "data": l.recorded_at.isoformat(),
            "peso_kg": l.weight_kg,
            "bmi": l.bmi,
            "grasso_corporeo_pct": l.body_fat_pct,
            "grasso_sottocutaneo_pct": l.subcutaneous_fat_pct,
            "grasso_viscerale": l.visceral_fat,
            "massa_muscolare_kg": l.muscle_mass_kg,
            "massa_magra_kg": l.fat_free_mass_kg,
            "muscolo_scheletrico_pct": l.skeletal_muscle_pct,
            "massa_ossea_kg": l.bone_mass_kg,
            "eta_metabolica": l.metabolic_age,
            "bmr_kcal": l.bmr_kcal,
            "acqua_corporea_pct": l.body_water_pct,
            "proteine_pct": l.protein_pct,
            "note": l.notes
        })

    profile_info = {}
    if profile:
        profile_info = {
            "eta": calculate_age(profile.birth_date) if profile.birth_date else None,
            "altezza_cm": profile.height_cm,
            "genere": profile.gender,
            "peso_target_kg": profile.target_weight_kg,
            "calorie_target": profile.daily_calorie_target
        }

    system_prompt = (
        "Sei un biologo nutrizionista e preparatore atletico esperto di bioimpedenziometria (BIA) e dimagrimento sostenibile. "
        "Il tuo compito è analizzare i dati storici delle pesate su bilancia impedenziometrica dell'utente e generare un feedback chiaro, motivante, professionale e scientificamente accurato in lingua ITALIANA.\n\n"
        "LINEE GUIDA DELL'ANALISI:\n"
        "1. Analisi differenziale: Non guardare solo il peso sulla bilancia! Confronta la perdita di massa grassa (%) rispetto alla preservazione della massa muscolare (kg) e della massa magra.\n"
        "2. Grasso viscerale: Evidenzia sempre lo stato del grasso viscerale (indice di rischio cardiovascolare e metabolico: <10 normale, 10-14 attenzione, >=15 alto rischio).\n"
        "3. Idratazione: La bioimpedenza dipende dall'acqua corporea. Spiega se l'idratazione è ottimale (>50% per gli uomini) o se ha influenzato le stime.\n"
        "4. Tone: Professionale, incoraggiante, empatico ma rigoroso.\n\n"
        "RISPONDI ESCLUSIVAMENTE con un oggetto JSON valido con la seguente struttura:\n"
        "{\n"
        '  "overall_trend": "positivo" | "eccellente" | "stabile" | "attenzione",\n'
        '  "review_markdown": "Testo dettagliato formattato in Markdown con titoli h3/h4, elenchi puntati, grassetto sui numeri chiave e spiegazione del trend",\n'
        '  "key_metrics_summary": {"peso_attuale": 122.4, "delta_peso": -1.2, "delta_grasso_pct": -0.5, "delta_muscolo_kg": 0.1, "grasso_viscerale": 20},\n'
        '  "recommendations": ["Consiglio pratico 1", "Consiglio pratico 2", "Consiglio pratico 3"]\n'
        "}"
    )

    user_prompt = (
        f"DATI UTENTE:\n{json.dumps(profile_info, ensure_ascii=False, indent=2)}\n\n"
        f"STORICO RILEVAZIONI BILANCIA (dalla più recente alla più vecchia):\n"
        f"{json.dumps(logs_data, ensure_ascii=False, indent=2)}\n\n"
        "Fornisci la tua valutazione dettagliata in JSON."
    )

    candidate_models = [
        getattr(settings, "OPENROUTER_TEXT_MODEL", "nvidia/nemotron-3.5-lightning:free"),
        "nvidia/nemotron-3.5-lightning:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free"
    ]

    for model_name in candidate_models:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": f"https://{settings.DOMAIN}",
                "X-Title": "DietOrDie",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 1500
            }
            async with httpx.AsyncClient(timeout=35.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    cleaned = clean_json_text(content)
                    parsed = json.loads(cleaned)
                    return AIProgressReviewResponse(
                        overall_trend=parsed.get("overall_trend", "positivo"),
                        review_markdown=parsed.get("review_markdown", cleaned),
                        key_metrics_summary=parsed.get("key_metrics_summary", {}),
                        recommendations=parsed.get("recommendations", [])
                    )
                else:
                    print(f"[OpenRouter Progress AI Error {model_name} {res.status_code}]: {res.text}")
        except Exception as e:
            print(f"[OpenRouter Progress AI Exception with {model_name}]: {e}")

    # Fallback deterministico
    return generate_algorithmic_review(logs, profile)
