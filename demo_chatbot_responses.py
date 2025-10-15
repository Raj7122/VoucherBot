#!/usr/bin/env python3
"""
Demo script to simulate VoucherBot responses to pertinent and non-pertinent questions.
This demonstrates the chatbot's ability to handle relevant housing queries and redirect off-topic questions.
"""

import json
from typing import Dict, List, Any

# Mock data for demonstration
MOCK_LISTINGS = [
    {
        "address": "123 Main St, Brooklyn, NY",
        "bedrooms": 2,
        "rent": 1800,
        "borough": "Brooklyn",
        "violations": 0,
        "risk_level": "✅ Safe",
        "subway_distance": 0.3,
        "school_distance": 0.5
    },
    {
        "address": "456 Oak Ave, Queens, NY",
        "bedrooms": 3,
        "rent": 2200,
        "borough": "Queens",
        "violations": 2,
        "risk_level": "⚠️ Moderate",
        "subway_distance": 0.8,
        "school_distance": 0.3
    }
]

MOCK_VIOLATIONS = {
    "123 Main St, Brooklyn, NY": {
        "violations": 0,
        "risk_level": "✅ Safe",
        "last_inspection": "2024-01-15",
        "summary": "No violations found. Building is in good condition."
    },
    "456 Oak Ave, Queens, NY": {
        "violations": 2,
        "risk_level": "⚠️ Moderate",
        "last_inspection": "2024-02-20",
        "summary": "Minor violations for maintenance issues. Generally safe for occupancy."
    }
}

def mock_search_housing(query: str) -> List[Dict[str, Any]]:
    """Mock housing search function"""
    # Simple keyword matching for demo
    if "brooklyn" in query.lower() or "2 bedroom" in query.lower():
        return [MOCK_LISTINGS[0]]
    elif "queens" in query.lower() or "3 bedroom" in query.lower():
        return [MOCK_LISTINGS[1]]
    else:
        return MOCK_LISTINGS[:2]  # Return all for general queries

def mock_check_violations(address: str) -> Dict[str, Any]:
    """Mock violation check function"""
    return MOCK_VIOLATIONS.get(address, {
        "violations": 0,
        "risk_level": "✅ Safe",
        "summary": "No violation data available for this address."
    })

def mock_email_draft(landlord_info: str, user_info: str) -> str:
    """Mock email generation"""
    return f"""
Subject: Section 8 Voucher Inquiry for Apartment

Dear Property Manager,

{user_info}

I am writing to inquire about renting an apartment with my Section 8 housing voucher. {landlord_info}

Thank you for your consideration.

Best regards,
[Your Name]
"""

def simulate_chatbot_response(user_input: str) -> str:
    """
    Simulate how the chatbot would respond to different inputs.
    This demonstrates pertinent vs non-pertinent question handling.
    """

    input_lower = user_input.lower()

    # Pertinent questions - housing/voucher related
    if any(keyword in input_lower for keyword in [
        "housing", "apartment", "rent", "voucher", "section 8", "cityfheps",
        "violation", "building safety", "subway", "school", "email", "landlord"
    ]):

        # Housing search queries
        if any(word in input_lower for word in ["search", "find", "looking for", "need"]):
            listings = mock_search_housing(user_input)
            if listings:
                response = "🔍 Here are some voucher-friendly housing options I found:\n\n"
                for listing in listings:
                    response += f"🏠 **{listing['address']}**\n"
                    response += f"   Bedrooms: {listing['bedrooms']} | Rent: ${listing['rent']}\n"
                    response += f"   Safety: {listing['risk_level']} | Subway: {listing['subway_distance']}mi\n"
                    response += f"   Schools: {listing['school_distance']}mi away\n\n"
                return response
            else:
                return "🔍 I couldn't find specific listings matching your criteria. Try adjusting your search terms or location."

        # Violation checking
        elif "violation" in input_lower or "safety" in input_lower:
            # Extract address if mentioned
            if "123 main" in input_lower or "brooklyn" in input_lower:
                violations = mock_check_violations("123 Main St, Brooklyn, NY")
            elif "456 oak" in input_lower or "queens" in input_lower:
                violations = mock_check_violations("456 Oak Ave, Queens, NY")
            else:
                return "🏢 To check building violations, please provide a specific NYC address (e.g., '123 Main St, Brooklyn')."

            response = f"🏢 **Building Safety Report**\n\n"
            response += f"**Risk Level:** {violations['risk_level']}\n"
            response += f"**Violations:** {violations['violations']}\n"
            response += f"**Summary:** {violations['summary']}\n"
            return response

        # Email drafting
        elif "email" in input_lower or "draft" in input_lower:
            return mock_email_draft(
                "I have a Section 8 voucher and am looking for a 2-bedroom apartment.",
                "I am a responsible tenant with a stable income and good rental history."
            )

        # General housing questions
        elif any(word in input_lower for word in ["voucher", "section 8", "cityfheps"]):
            return """🏠 **Housing Voucher Information**

Section 8 is a federal program that helps low-income families afford housing. In NYC, you can apply through NYCHA.

**Key Requirements:**
- Income must be below certain limits
- Must be a US citizen or eligible immigrant
- Background check required

**NYC Resources:**
- NYCHA: nyc.gov/nycha
- HPD: nyc.gov/hpd

Would you like help finding specific apartments or checking building safety?"""

        # Subway/school proximity
        elif "subway" in input_lower or "school" in input_lower:
            return """🚇 **Transit & Education Access**

For subway proximity, I can check distance to nearest stations. For schools, I can find nearby public schools.

Please provide an address, and I'll give you detailed information about:
- Nearest subway stations and walking distance
- Nearby schools and their ratings
- Public transportation options"""

    # Non-pertinent questions - redirect appropriately
    else:
        # Weather questions
        if "weather" in input_lower:
            return """🌤️ **Weather & Housing Connection**

While I focus on housing, NYC weather can affect apartment hunting! Currently, it's typically mild in spring/fall.

**Housing Tip:** Consider building location for weather exposure (wind, flooding) when choosing apartments.

Would you like help finding weather-resilient housing or checking building safety?"""

        # Food/restaurant questions
        elif any(word in input_lower for word in ["food", "restaurant", "eat"]):
            return """🍽️ **Food & Housing Connection**

Great food is important for quality of life! Many NYC neighborhoods offer diverse dining options.

**Housing Tip:** Look for apartments near public transportation to access restaurants easily. Consider kitchen size for cooking at home.

Would you like help finding apartments in foodie neighborhoods or checking nearby amenities?"""

        # Sports/entertainment
        elif any(word in input_lower for word in ["sports", "game", "movie", "entertainment"]):
            return """🎬 **Entertainment & Housing**

NYC has amazing entertainment options! Consider apartment location for easy access to venues.

**Housing Tip:** Apartments near subway lines give you quick access to sports events, theaters, and entertainment districts.

Would you like help finding housing near entertainment areas or checking transit access?"""

        # Completely off-topic
        else:
            return """🤔 **Staying On Topic**

I specialize in helping NYC residents find safe, affordable, voucher-friendly housing. While I'm happy to chat about other topics, my expertise is in:

- Housing searches and listings
- Building safety and violations
- Transit and school proximity
- Voucher program information

What housing-related question can I help you with today?"""

# Demo function to show various responses
def run_demo():
    print("🤖 VoucherBot Response Simulation Demo")
    print("=" * 50)

    # Pertinent questions
    pertinent_questions = [
        "I need help finding housing with Section 8 voucher",
        "Search for 2 bedroom apartments in Brooklyn under $2000",
        "Check building violations for 123 Main St, Brooklyn",
        "Draft an email to a landlord about my Section 8 voucher",
        "How do I apply for CityFHEPS?",
        "Find apartments near subway stations"
    ]

    print("\n📋 PERTINENT QUESTIONS (Housing/Voucher Related):")
    print("-" * 40)

    for i, question in enumerate(pertinent_questions, 1):
        print(f"\n{i}. User: {question}")
        response = simulate_chatbot_response(question)
        print(f"🤖 Bot: {response[:100]}{'...' if len(response) > 100 else ''}")

    # Non-pertinent questions
    non_pertinent_questions = [
        "What's the weather like today?",
        "Where's a good place to eat pizza?",
        "Who won the game last night?",
        "Can you tell me a joke?",
        "What time is it?"
    ]

    print("\n\n🚫 NON-PERTINENT QUESTIONS (Off-Topic):")
    print("-" * 40)

    for i, question in enumerate(non_pertinent_questions, 1):
        print(f"\n{i}. User: {question}")
        response = simulate_chatbot_response(question)
        print(f"🤖 Bot: {response[:100]}{'...' if len(response) > 100 else ''}")

    print("\n" + "=" * 50)
    print("🎉 Demo Complete!")
    print("\nThis simulation shows how VoucherBot:")
    print("✅ Responds helpfully to housing-related questions")
    print("✅ Provides mock data for searches and violations")
    print("✅ Gracefully redirects non-pertinent questions back to housing topics")
    print("✅ Maintains focus on its core mission of helping with NYC housing")

if __name__ == "__main__":
    run_demo()
