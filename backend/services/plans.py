"""
ReportPilot plan configuration.
All plan limits, features, and pricing defined here.
"""

PLANS = {
    "trial": {
        "display_name": "Free Trial",
        "client_limit": 10,  # Generous trial to show value
        "features": {
            "pptx_export": True,
            "pdf_export": True,
            "white_label": True,  # Let them experience it
            "scheduling": True,
            "ai_tones": ["professional", "conversational", "executive", "data_heavy"],
            "templates": ["full", "summary", "brief"],
            "visual_templates": ["modern_clean", "dark_executive", "colorful_agency"],
            "powered_by_badge": True,  # Shows "Powered by ReportPilot"
        },
        "trial_days": 14,
    },
    "starter": {
        "display_name": "Starter",
        "monthly_price_inr": 999,
        "annual_price_inr": 9599,
        "monthly_price_usd": 19,
        "annual_price_usd": 182,
        "client_limit": 5,
        "features": {
            "pptx_export": False,  # PDF only
            "pdf_export": True,
            "white_label": False,
            "scheduling": False,  # Pro+ only
            "ai_tones": ["professional"],
            "templates": ["full"],
            "visual_templates": ["modern_clean"],
            "powered_by_badge": True,
        },
    },
    "pro": {
        "display_name": "Pro",
        "monthly_price_inr": 1999,
        "annual_price_inr": 19199,
        "monthly_price_usd": 39,
        "annual_price_usd": 374,
        "client_limit": 15,
        "features": {
            "pptx_export": True,
            "pdf_export": True,
            "white_label": True,
            "scheduling": True,
            "scheduling_frequencies": ["weekly", "biweekly", "monthly"],
            "ai_tones": ["professional", "conversational", "executive", "data_heavy"],
            "templates": ["full", "summary", "brief"],
            "visual_templates": ["modern_clean", "dark_executive", "colorful_agency"],
            "powered_by_badge": False,
        },
    },
    "agency": {
        "display_name": "Agency",
        "monthly_price_inr": 3499,
        "annual_price_inr": 33599,
        "monthly_price_usd": 69,
        "annual_price_usd": 662,
        "client_limit": 999,  # effectively unlimited
        "features": {
            "pptx_export": True,
            "pdf_export": True,
            "white_label": True,
            "scheduling": True,
            "scheduling_frequencies": ["weekly", "biweekly", "monthly"],
            "ai_tones": ["professional", "conversational", "executive", "data_heavy"],
            "templates": ["full", "summary", "brief"],
            "visual_templates": ["modern_clean", "dark_executive", "colorful_agency"],
            "powered_by_badge": False,
        },
    },
}


def get_plan(plan_name: str) -> dict:
    return PLANS.get(plan_name, PLANS["trial"])


def get_client_limit(plan_name: str) -> int:
    return get_plan(plan_name).get("client_limit", 3)


def check_feature(plan_name: str, feature: str) -> bool:
    plan = get_plan(plan_name)
    return plan.get("features", {}).get(feature, False)
