import pytest
from unittest.mock import patch
from app.services.llm_service import generate_pre_visit_summary

def test_neurology_pre_visit_summary():
    symptoms = "recurring headaches, dizziness, difficulty concentrating"
    summary = generate_pre_visit_summary(symptoms, specialization="Neurology")

    assert summary["urgency"] in ["Low", "Medium", "High"]
    assert len(summary["suggested_questions"]) == 3
    # Check that questions are relevant to neurological symptoms and do not contain skin/topical keywords
    for q in summary["suggested_questions"]:
        assert "itching" not in q.lower()
        assert "topical" not in q.lower()
        assert "rash" not in q.lower()

def test_dermatology_pre_visit_summary():
    symptoms = "itchy rash on forearms"
    summary = generate_pre_visit_summary(symptoms, specialization="Dermatology")

    assert summary["urgency"] in ["Low", "Medium", "High"]
    assert len(summary["suggested_questions"]) == 3
    # Check that questions are relevant to skin
    assert any("skin" in q.lower() or "rash" in q.lower() or "itching" in q.lower() for q in summary["suggested_questions"])

def test_cardiology_pre_visit_summary():
    symptoms = "chest discomfort and shortness of breath"
    summary = generate_pre_visit_summary(symptoms, specialization="Cardiology")

    assert summary["urgency"] in ["Medium", "High"]
    assert len(summary["suggested_questions"]) == 3
    # Check cardiology relevant questions
    assert any("exertion" in q.lower() or "palpitations" in q.lower() or "blood pressure" in q.lower() or "heart" in q.lower() for q in summary["suggested_questions"])

def test_orthopedics_pre_visit_summary():
    symptoms = "knee pain when walking down stairs"
    summary = generate_pre_visit_summary(symptoms, specialization="Orthopedics")

    assert summary["urgency"] in ["Low", "Medium", "High"]
    assert len(summary["suggested_questions"]) == 3
    # Check orthopedics relevant questions
    assert any("joint" in q.lower() or "injury" in q.lower() or "walking" in q.lower() or "weight-bearing" in q.lower() or "swelling" in q.lower() for q in summary["suggested_questions"])

def test_mocked_groq_with_specialization():
    mock_json = """{
        "urgency": "Medium",
        "chief_complaint": "Patient presents with recurring headaches accompanied by dizziness and concentration difficulties.",
        "suggested_questions": [
            "How long do the headache episodes last and what is their pain quality?",
            "Do you experience light or sound sensitivity during the dizziness?",
            "Have you noticed any preceding aura, visual disturbances, or neurological deficits?"
        ]
    }"""
    with patch("app.services.llm_service._call_groq_api", return_value=mock_json):
        summary = generate_pre_visit_summary("recurring headaches, dizziness, difficulty concentrating", specialization="Neurology")
        assert summary["urgency"] == "Medium"
        assert "headaches" in summary["chief_complaint"]
        assert len(summary["suggested_questions"]) == 3
        assert "aura" in summary["suggested_questions"][2]
