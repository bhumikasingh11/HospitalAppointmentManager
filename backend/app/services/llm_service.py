import json
import logging
import httpx
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def _call_groq_api(prompt: str, system_prompt: str) -> str:
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    with httpx.Client(timeout=10.0) as client:
        response = client.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

def _get_specialty_fallback(specialization: str, symptoms: str) -> Dict[str, Any]:
    spec_lower = (specialization or "").lower()
    
    if "neuro" in spec_lower:
        return {
            "urgency": "Medium",
            "chief_complaint": "Patient presents with neurological concerns including headaches, dizziness, or cognitive symptoms." if symptoms else "Routine neurological evaluation.",
            "suggested_questions": [
                "How frequently do these symptoms occur, and what is their typical duration and severity?",
                "Have you noticed any vision changes, sensory numbness, tingling, or limb weakness?",
                "Are there specific triggers or factors that seem to bring on or relieve the symptoms?"
            ]
        }
    elif "cardio" in spec_lower:
        return {
            "urgency": "High" if any(w in (symptoms or "").lower() for w in ["chest", "breath", "pain", "pressure"]) else "Medium",
            "chief_complaint": "Patient presents with cardiovascular symptoms requiring specialist evaluation." if symptoms else "Routine cardiology check-up.",
            "suggested_questions": [
                "Do your symptoms worsen during physical exertion, stress, or when lying flat?",
                "Have you experienced any palpitations, lightheadedness, or swelling in your ankles or legs?",
                "Do you have a personal or family history of high blood pressure, heart disease, or elevated cholesterol?"
            ]
        }
    elif "derm" in spec_lower:
        return {
            "urgency": "Low",
            "chief_complaint": "Patient presents with skin or dermatological symptoms requiring clinical review." if symptoms else "Routine dermatological consultation.",
            "suggested_questions": [
                "When did you first notice the skin changes, and have they spread or changed in appearance?",
                "Are the symptoms accompanied by itching, pain, warmth, scaling, or bleeding?",
                "Have you recently used new soaps, lotions, detergents, or had contact with new environmental materials?"
            ]
        }
    elif "ortho" in spec_lower:
        return {
            "urgency": "Medium",
            "chief_complaint": "Patient presents with musculoskeletal or joint pain affecting mobility." if symptoms else "Routine orthopedic consultation.",
            "suggested_questions": [
                "Did the pain begin after an acute injury or strain, or did it develop gradually over time?",
                "Does the affected joint click, lock, give way, or swell after physical activity?",
                "Is the pain aggravated by weight-bearing movements like walking, climbing stairs, or bending?"
            ]
        }
    else:
        return {
            "urgency": "Medium",
            "chief_complaint": "Patient seeking clinical consultation for reported symptoms." if symptoms else "Routine consultation.",
            "suggested_questions": [
                "How long have you been experiencing these symptoms, and have they progressed over time?",
                "What specific activities or circumstances make the symptoms better or worse?",
                "Are you currently taking any prescribed medications, over-the-counter remedies, or supplements?"
            ]
        }

def generate_pre_visit_summary(symptoms: str, specialization: str = "General Medicine") -> Dict[str, Any]:
    fallback = _get_specialty_fallback(specialization, symptoms)

    if not symptoms or not symptoms.strip():
        fallback["urgency"] = "Low"
        return fallback

    system_prompt = (
        f"You are an expert clinical intake assistant preparing a concise pre-consultation summary for a specialist in {specialization}. "
        "Strict rules:\n"
        "1. Urgency MUST be exactly one of: 'Low', 'Medium', or 'High'.\n"
        "2. Chief Complaint MUST be exactly ONE concise, symptom-based sentence summarizing the patient's primary concern. Never invent symptoms or diagnose.\n"
        f"3. Suggested Questions MUST contain exactly 3 concise, relevant exploration questions tailored specifically to BOTH the patient's symptoms AND the doctor's specialty ({specialization}).\n"
        "4. NEVER generate questions from an unrelated medical specialty (for example, do NOT ask about skin rashes or topical products for a Neurology, Cardiology, or Orthopedics visit).\n"
        "5. NEVER make a medical diagnosis or prescribe treatments.\n"
        "6. Keep output concise to prevent truncation.\n"
        "Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "urgency": "Low" | "Medium" | "High",\n'
        '  "chief_complaint": "one concise sentence summarizing primary concern",\n'
        '  "suggested_questions": ["question 1", "question 2", "question 3"]\n'
        "}"
    )

    user_prompt = (
        f"Doctor Specialty: {specialization}\n"
        f"Patient Reported Symptoms: {symptoms.strip()}"
    )

    try:
        raw_response = _call_groq_api(user_prompt, system_prompt)
        parsed = json.loads(raw_response)

        urgency = parsed.get("urgency", fallback["urgency"])
        if urgency not in ["Low", "Medium", "High"]:
            urgency = fallback["urgency"]

        chief_complaint = str(parsed.get("chief_complaint", "")).strip()
        if not chief_complaint or len(chief_complaint) > 200:
            chief_complaint = fallback["chief_complaint"]

        questions = parsed.get("suggested_questions")
        if not isinstance(questions, list) or len(questions) < 3:
            questions = fallback["suggested_questions"]
        else:
            questions = [str(q).strip() for q in questions[:3] if str(q).strip()]
            if len(questions) < 3:
                questions = fallback["suggested_questions"]

        return {
            "urgency": urgency,
            "chief_complaint": chief_complaint,
            "suggested_questions": questions
        }
    except Exception as e:
        logger.warning(f"LLM pre-visit summary failed, returning specialty fallback: {e}")
        return fallback

def generate_post_visit_summary(notes: str, prescriptions: List[Dict[str, Any]]) -> Dict[str, str]:
    presc_summary = []
    for p in prescriptions:
        p_name = p.get("medicine_name", "Medication")
        p_dose = p.get("dosage", "")
        p_freq = p.get("frequency", "")
        p_dur = p.get("duration", "")
        p_inst = p.get("instructions", "")
        presc_summary.append(f"- {p_name} ({p_dose}): {p_freq} for {p_dur}. Instructions: {p_inst}")

    presc_text = "\n".join(presc_summary) if presc_summary else "None prescribed."

    fallback = {
        "patient_friendly_summary": f"Your doctor noted: {notes}" if notes else "Consultation completed.",
        "medication_schedule": presc_text,
        "follow_up_steps": "Follow up with your doctor if symptoms persist or worsen."
    }

    if not notes and not prescriptions:
        return fallback

    system_prompt = (
        "You are an empathetic medical communicator. Transform clinical notes and prescriptions into "
        "an easy-to-understand summary for the patient. Return ONLY a valid JSON object with the schema:\n"
        "{\n"
        '  "patient_friendly_summary": "plain English explanation of the diagnosis and visit",\n'
        '  "medication_schedule": "clear schedule explaining how and when to take medications",\n'
        '  "follow_up_steps": "practical next steps, warning signs, and return visit timing"\n'
        "}"
    )

    user_prompt = f"Doctor Clinical Notes:\n{notes}\n\nPrescriptions:\n{presc_text}"

    try:
        raw_response = _call_groq_api(user_prompt, system_prompt)
        parsed = json.loads(raw_response)
        return {
            "patient_friendly_summary": str(parsed.get("patient_friendly_summary") or fallback["patient_friendly_summary"]),
            "medication_schedule": str(parsed.get("medication_schedule") or fallback["medication_schedule"]),
            "follow_up_steps": str(parsed.get("follow_up_steps") or fallback["follow_up_steps"])
        }
    except Exception as e:
        logger.warning(f"LLM post-visit summary failed, returning fallback: {e}")
        return fallback
