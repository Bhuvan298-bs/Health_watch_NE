"""
AI Prediction Engine for outbreak detection and risk analysis.
Uses statistical scoring + weather data for predictions.
"""
import math
import random
import os
import pickle
from datetime import datetime, timedelta
from collections import Counter

# Disease symptom mappings
WATERBORNE_DISEASES = {
    "cholera": ["watery diarrhea", "vomiting", "dehydration", "leg cramps", "rapid heart rate"],
    "typhoid": ["sustained fever", "headache", "abdominal pain", "weakness", "rash"],
    "dysentery": ["bloody diarrhea", "abdominal cramps", "fever", "nausea"],
    "hepatitis_a": ["jaundice", "fatigue", "nausea", "abdominal pain", "dark urine", "fever"],
    "leptospirosis": ["high fever", "headache", "muscle pain", "red eyes", "jaundice"],
    "giardiasis": ["diarrhea", "gas", "bloating", "stomach cramps", "nausea"],
    "amoebiasis": ["bloody diarrhea", "abdominal pain", "fever", "fatigue"],
}

SYMPTOM_KEYWORDS = {
    "diarrhea": 3, "vomiting": 3, "fever": 2, "nausea": 2,
    "abdominal pain": 2, "dehydration": 4, "jaundice": 4,
    "bloody stool": 4, "headache": 1, "weakness": 1,
    "cramps": 2, "bloating": 1, "fatigue": 1, "rash": 2,
    "dark urine": 3, "muscle pain": 1, "red eyes": 2
}

HEALTH_TIPS = {
    "green": [
        "Continue to drink clean filtered or boiled water.",
        "Wash hands regularly with soap before meals.",
        "Keep your surroundings clean and dispose of waste properly.",
        "Store water in clean, covered containers.",
    ],
    "yellow": [
        "⚠️ There are mild reports of illness in your area. Stay cautious.",
        "Boil all drinking water for at least 1 minute before consuming.",
        "Avoid eating raw or unwashed fruits and vegetables.",
        "If you experience diarrhea or vomiting, seek medical help immediately.",
        "Use water purification tablets if boiling is not possible.",
    ],
    "red": [
        "🚨 HIGH ALERT: Multiple cases reported in your village!",
        "Do NOT drink untreated water from any source.",
        "Boil water for at least 3 minutes or use certified purification.",
        "Seek immediate medical attention if you have diarrhea, vomiting, or fever.",
        "Avoid public water sources until cleared by health authorities.",
        "Help spread awareness – inform your neighbors about water safety!",
    ]
}

SAFE_WATER_GUIDE = [
    {"title": "Boiling", "description": "Boil water at a rolling boil for at least 1 minute (3 minutes at high altitude). This kills most disease-causing organisms.", "icon": "🔥"},
    {"title": "Chlorination", "description": "Add 2 drops of household bleach per liter of clear water. Wait 30 minutes before drinking.", "icon": "💧"},
    {"title": "Solar Disinfection (SODIS)", "description": "Fill clear plastic bottles with water and place in direct sunlight for 6+ hours. UV rays kill pathogens.", "icon": "☀️"},
    {"title": "Ceramic Filters", "description": "Use locally available ceramic water filters. They remove bacteria and parasites effectively.", "icon": "🏺"},
    {"title": "Sand Filtration", "description": "Build a simple sand filter with layers of gravel and sand. Pour water through slowly to remove impurities.", "icon": "⏳"},
    {"title": "Storage Tips", "description": "Always store treated water in clean, covered containers. Never dip hands into stored water.", "icon": "🫙"},
]


# Model paths (strict mode: required for advanced predictions)
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
WATER_RF_MODEL_PATH = os.path.join(MODEL_DIR, "water_quality_rf.pkl")
WATER_LGBM_MODEL_PATH = os.path.join(MODEL_DIR, "water_quality_lgbm.pkl")
DISEASE_XGB_MODEL_PATH = os.path.join(MODEL_DIR, "disease_probability_xgb.pkl")


def _load_required_pickle(path: str, model_name: str):
    """Load a required pickle model; raise clear error if unavailable."""
    if not os.path.isfile(path):
        raise RuntimeError(
            f"Required model '{model_name}' not found at: {path}. "
            f"Please add the trained model file before running predictions."
        )
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as exc:
        raise RuntimeError(f"Failed to load model '{model_name}': {exc}") from exc


def _normalize_probability(value: float) -> float:
    """Clamp values to 0..1 range."""
    try:
        return max(0.0, min(float(value), 1.0))
    except Exception:
        return 0.0


def _predict_proba_strict(model, features: list, model_name: str) -> float:
    """Predict probability in strict mode; raise explicit error on failure."""
    try:
        # Expected format: [ [f1, f2, ...] ]
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba([features])
            if probs is not None and len(probs) > 0:
                row = probs[0]
                if len(row) >= 2:
                    return _normalize_probability(row[1])
                if len(row) == 1:
                    return _normalize_probability(row[0])
        if hasattr(model, "predict"):
            pred = model.predict([features])
            if pred is not None and len(pred) > 0:
                return _normalize_probability(pred[0])
    except Exception as exc:
        raise RuntimeError(f"Prediction failed for model '{model_name}': {exc}") from exc
    raise RuntimeError(
        f"Model '{model_name}' does not support predict_proba or predict in expected format."
    )


def predict_water_quality_probability(report_count: int, avg_severity: float, rainfall: float, humidity: float, temp: float) -> dict:
    """
    Predict contaminated-water probability.
    Strict mode: LightGBM model if available, else RandomForest model.
    Raises error if neither model file is present.
    Returns probability (0..1), model_used, and quality label.
    """
    features = [report_count, avg_severity, rainfall, humidity, temp]

    # Try LightGBM model first if file is present
    if os.path.isfile(WATER_LGBM_MODEL_PATH):
        lgbm_model = _load_required_pickle(WATER_LGBM_MODEL_PATH, "water_quality_lgbm")
        prob = _predict_proba_strict(lgbm_model, features, "water_quality_lgbm")
        return {
            "probability": round(prob, 4),
            "model_used": "lightgbm",
            "label": "unsafe" if prob >= 0.5 else "safe"
        }

    # Then RandomForest model if file is present
    if os.path.isfile(WATER_RF_MODEL_PATH):
        rf_model = _load_required_pickle(WATER_RF_MODEL_PATH, "water_quality_rf")
        prob = _predict_proba_strict(rf_model, features, "water_quality_rf")
        return {
            "probability": round(prob, 4),
            "model_used": "random_forest",
            "label": "unsafe" if prob >= 0.5 else "safe"
        }

    raise RuntimeError(
        "No water quality model found. Add either 'water_quality_lgbm.pkl' or 'water_quality_rf.pkl' in backend/models/."
    )


def predict_disease_probability_xgboost(symptoms_str: str, duration_days: int = 0, severity: str = "low") -> dict:
    """
    Predict disease probability using required XGBoost model.
    Raises error if model file is missing or invalid.
    """
    severity_map = {"low": 0.2, "medium": 0.45, "high": 0.7, "critical": 0.9}
    symptom_score = calculate_symptom_score(symptoms_str) / 100.0
    duration_norm = _normalize_probability((duration_days or 0) / 14.0)
    sev_norm = _normalize_probability(severity_map.get((severity or "low").lower(), 0.2))
    features = [symptom_score, duration_norm, sev_norm]

    xgb_model = _load_required_pickle(DISEASE_XGB_MODEL_PATH, "disease_probability_xgb")
    prob = _predict_proba_strict(xgb_model, features, "disease_probability_xgb")

    return {
        "probability": round(prob, 4),
        "model_used": "xgboost",
        "risk_band": "high" if prob >= 0.7 else "medium" if prob >= 0.4 else "low"
    }


def early_warning_ensemble(risk_score: float, water_quality_prob: float, disease_prob: float) -> dict:
    """
    Ensemble early-warning score from multiple signals.
    This does not require any external package and is always safe.
    """
    rs = _normalize_probability((risk_score or 0) / 100.0)
    wq = _normalize_probability(water_quality_prob)
    dp = _normalize_probability(disease_prob)

    # Weighted blend for stability in low-data settings
    ensemble_score = (0.5 * rs) + (0.25 * wq) + (0.25 * dp)

    if ensemble_score >= 0.65:
        level = "red"
    elif ensemble_score >= 0.35:
        level = "yellow"
    else:
        level = "green"

    return {
        "ensemble_score": round(ensemble_score * 100.0, 1),
        "early_warning_level": level,
        "components": {
            "risk_score": round(rs * 100.0, 1),
            "water_quality_probability": round(wq, 4),
            "disease_probability": round(dp, 4)
        }
    }


def calculate_symptom_score(symptoms_str: str) -> float:
    """Calculate disease risk score based on reported symptoms."""
    symptoms_lower = symptoms_str.lower()
    score = 0
    matched = 0
    for keyword, weight in SYMPTOM_KEYWORDS.items():
        if keyword in symptoms_lower:
            score += weight
            matched += 1
    # Normalize to 0-100
    max_possible = sum(SYMPTOM_KEYWORDS.values())
    normalized = (score / max_possible) * 100 if max_possible > 0 else 0
    return min(normalized, 100)


def detect_disease(symptoms_str: str) -> list:
    """Match symptoms to likely waterborne diseases."""
    symptoms_lower = symptoms_str.lower()
    matches = []
    for disease, disease_symptoms in WATERBORNE_DISEASES.items():
        match_count = sum(1 for s in disease_symptoms if s in symptoms_lower)
        if match_count > 0:
            confidence = (match_count / len(disease_symptoms)) * 100
            matches.append({
                "disease": disease.replace("_", " ").title(),
                "confidence": round(confidence, 1),
                "matched_symptoms": match_count,
                "total_symptoms": len(disease_symptoms)
            })
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return matches[:3]


def calculate_village_risk(reports: list, weather_data: dict = None) -> dict:
    """
    Calculate outbreak risk for a village based on:
    - Number of recent reports
    - Severity of symptoms
    - Weather conditions (rainfall, temperature, humidity)
    """
    if not reports:
        return {"risk_level": "green", "risk_score": 5.0, "factors": []}

    now = datetime.now()
    week_ago = now - timedelta(days=7)

    # Count recent reports
    recent_reports = []
    for r in reports:
        created = r.get("created_at", "")
        if isinstance(created, str):
            try:
                dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                if dt >= week_ago:
                    recent_reports.append(r)
            except:
                recent_reports.append(r)
        else:
            recent_reports.append(r)

    report_count = len(recent_reports)
    factors = []

    # Base score from report count
    count_score = min(report_count * 8, 40)
    factors.append(f"{report_count} reports in last 7 days")

    # Severity score
    severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 5}
    severity_total = sum(severity_map.get(r.get("severity", "low"), 1) for r in recent_reports)
    severity_score = min((severity_total / max(report_count, 1)) * 10, 30)
    factors.append(f"Average severity score: {severity_total / max(report_count, 1):.1f}")

    # Symptom diversity score
    all_symptoms = " ".join([r.get("symptoms", "") for r in recent_reports])
    symptom_score = calculate_symptom_score(all_symptoms) * 0.2
    factors.append(f"Symptom severity index: {symptom_score:.1f}")

    # Weather factor
    weather_score = 0
    if weather_data:
        temp = weather_data.get("temp", 25)
        humidity = weather_data.get("humidity", 60)
        rainfall = weather_data.get("rainfall", 0)

        if temp > 30:
            weather_score += 5
            factors.append(f"High temperature: {temp}°C")
        if humidity > 80:
            weather_score += 5
            factors.append(f"High humidity: {humidity}%")
        if rainfall > 50:
            weather_score += 10
            factors.append(f"Heavy rainfall: {rainfall}mm (flooding risk)")
        elif rainfall > 20:
            weather_score += 5
            factors.append(f"Moderate rainfall: {rainfall}mm")

    total_score = count_score + severity_score + symptom_score + weather_score
    total_score = min(total_score, 100)

    # Strict model signals (required model files)
    avg_severity = severity_total / max(report_count, 1)
    rainfall = float((weather_data or {}).get("rainfall", 0) or 0)
    humidity = float((weather_data or {}).get("humidity", 0) or 0)
    temp = float((weather_data or {}).get("temp", 25) or 25)

    try:
        water_quality = predict_water_quality_probability(report_count, avg_severity, rainfall, humidity, temp)
    except Exception as exc:
        water_quality = {
            "probability": None,
            "model_used": "unavailable",
            "label": "unknown",
            "error": str(exc)
        }

    try:
        disease_signal = predict_disease_probability_xgboost(all_symptoms, duration_days=0, severity="medium")
    except Exception as exc:
        disease_signal = {
            "probability": None,
            "model_used": "unavailable",
            "risk_band": "unknown",
            "error": str(exc)
        }

    if water_quality.get("probability") is not None and disease_signal.get("probability") is not None:
        ensemble = early_warning_ensemble(total_score, water_quality["probability"], disease_signal["probability"])
    else:
        ensemble = {
            "ensemble_score": None,
            "early_warning_level": None,
            "components": {
                "risk_score": round(total_score, 1),
                "water_quality_probability": water_quality.get("probability"),
                "disease_probability": disease_signal.get("probability")
            },
            "error": "ML ensemble unavailable: one or more required model files are missing"
        }

    if total_score >= 60:
        risk_level = "red"
    elif total_score >= 30:
        risk_level = "yellow"
    else:
        risk_level = "green"

    if ensemble.get("early_warning_level") is None:
        ensemble["early_warning_level"] = risk_level

    return {
        "risk_level": risk_level,
        "risk_score": round(total_score, 1),
        "factors": factors,
        "report_count": report_count,
        "diseases_detected": detect_disease(all_symptoms) if recent_reports else [],
        "water_quality_prediction": water_quality,
        "disease_probability_prediction": disease_signal,
        "early_warning": ensemble
    }


def detect_fake_report(report: dict, worker_reports: list) -> dict:
    """Simple heuristic-based fake report detection."""
    flags = []
    score = 0

    # Check for very short symptom descriptions
    symptoms = report.get("symptoms", "")
    if len(symptoms) < 10:
        flags.append("Very short symptom description")
        score += 20

    # Check for too many reports in short time
    worker_id = report.get("worker_id")
    today_reports = [r for r in worker_reports if r.get("created_at", "")[:10] == datetime.now().strftime("%Y-%m-%d")]
    if len(today_reports) > 20:
        flags.append(f"Worker submitted {len(today_reports)} reports today (unusually high)")
        score += 25

    # Check for duplicate patient names
    patient_name = report.get("patient_name", "").lower()
    duplicates = [r for r in worker_reports if r.get("patient_name", "").lower() == patient_name]
    if len(duplicates) > 3:
        flags.append(f"Patient name '{report.get('patient_name')}' appears {len(duplicates)} times")
        score += 30

    # Check for generic/test data patterns
    test_patterns = ["test", "abc", "xxx", "aaa", "123", "asdf"]
    for pattern in test_patterns:
        if pattern in patient_name or pattern in symptoms.lower():
            flags.append(f"Contains test/generic data pattern: '{pattern}'")
            score += 40

    is_suspicious = score >= 30
    return {
        "is_suspicious": is_suspicious,
        "suspicion_score": min(score, 100),
        "flags": flags
    }


def analyze_water_source(reports_for_source: list) -> dict:
    """Analyze water source contamination based on linked reports."""
    if not reports_for_source:
        return {"status": "safe", "contamination_score": 0, "linked_cases": 0}

    case_count = len(reports_for_source)
    severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 5}
    severity_sum = sum(severity_map.get(r.get("severity", "low"), 1) for r in reports_for_source)
    avg_severity = severity_sum / case_count

    contamination_score = min((case_count * 15) + (avg_severity * 10), 100)

    if contamination_score >= 70:
        status = "contaminated"
    elif contamination_score >= 35:
        status = "warning"
    else:
        status = "safe"

    return {
        "status": status,
        "contamination_score": round(contamination_score, 1),
        "linked_cases": case_count,
        "avg_severity": round(avg_severity, 1)
    }


def generate_trend_data(reports: list, days: int = 30) -> list:
    """Generate daily case count trend data."""
    now = datetime.now()
    trend = []
    for i in range(days, -1, -1):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        count = 0
        for r in reports:
            created = r.get("created_at", "")
            if isinstance(created, str) and created[:10] == date:
                count += 1
        trend.append({"date": date, "cases": count})
    return trend


def get_health_tips(risk_level: str) -> list:
    """Get health tips based on current risk level."""
    return HEALTH_TIPS.get(risk_level, HEALTH_TIPS["green"])


def get_safe_water_guide() -> list:
    """Return safe water guide information."""
    return SAFE_WATER_GUIDE
