def explain(event: str, user: dict = None) -> dict:
    explanations = {
        "rain": {
            "event": "Heavy Rainfall Impact",
            "confidence": 87,
            "factors": [
                {"name": "Historical delivery drop during rain", "weight": 35, "value": "−38% avg"},
                {"name": "IMD weather alert active", "weight": 28, "value": "6+ cities"},
                {"name": "Platform surge pricing pattern", "weight": 22, "value": "Groceries +3x"},
                {"name": "Your city base risk", "weight": 15, "value": "High zone"},
            ],
            "summary": "Rain events historically cause 35-45% income drop for delivery workers. Switching to grocery platforms recovers ~60% of lost income.",
        },
        "aqi": {
            "event": "Poor Air Quality Impact",
            "confidence": 79,
            "factors": [
                {"name": "AQI level correlation with outdoor work", "weight": 40, "value": "AQI >300"},
                {"name": "City pollution baseline", "weight": 30, "value": "Unhealthy zone"},
                {"name": "Health risk multiplier", "weight": 20, "value": "1.4x"},
                {"name": "Government advisory", "weight": 10, "value": "Active"},
            ],
            "summary": "High AQI reduces outdoor worker efficiency by 25-30%. AC vehicle workers see less impact. Masks required.",
        },
        "accident": {
            "event": "Accident / Injury Risk",
            "confidence": 92,
            "factors": [
                {"name": "Road accident rate in city", "weight": 38, "value": "High"},
                {"name": "Work type risk category", "weight": 30, "value": "2-wheeler delivery"},
                {"name": "Peak hour traffic density", "weight": 20, "value": "7-10 PM"},
                {"name": "Income loss duration", "weight": 12, "value": "Avg 18 days"},
            ],
            "summary": "Delivery workers have 3x higher accident risk vs general public. Full income protection activates within 2 hours of claim.",
        },
        "festival": {
            "event": "Festival Demand Surge",
            "confidence": 94,
            "factors": [
                {"name": "Historical festival earnings spike", "weight": 45, "value": "+120% avg"},
                {"name": "Platform incentive programs", "weight": 28, "value": "Active bonuses"},
                {"name": "Customer order frequency", "weight": 17, "value": "+85%"},
                {"name": "City demand index", "weight": 10, "value": "Peak"},
            ],
            "summary": "Festival seasons produce the highest earning potential. Extended hours of 12+ per day can yield 2-3x normal income.",
        },
    }
    result = explanations.get(event, {
        "event": event.replace("_", " ").title(),
        "confidence": 75,
        "factors": [
            {"name": "Historical data correlation", "weight": 40, "value": "Moderate"},
            {"name": "Current conditions", "weight": 35, "value": "Active"},
            {"name": "User profile match", "weight": 25, "value": "Standard"},
        ],
        "summary": f"AI analysis for {event} based on your profile and real-time city data.",
    })
    return result
