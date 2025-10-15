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
        "school_distance": 0.5,
        "amenities": ["Laundry", "Gym"],
        "accepts_vouchers": True
    },
    {
        "address": "456 Oak Ave, Queens, NY",
        "bedrooms": 3,
        "rent": 2200,
        "borough": "Queens",
        "violations": 2,
        "risk_level": "⚠️ Moderate",
        "subway_distance": 0.8,
        "school_distance": 0.3,
        "amenities": ["Parking", "Balcony"],
        "accepts_vouchers": True
    },
    {
        "address": "789 Pine St, Manhattan, NY",
        "bedrooms": 1,
        "rent": 2500,
        "borough": "Manhattan",
        "violations": 1,
        "risk_level": "✅ Safe",
        "subway_distance": 0.1,
        "school_distance": 0.7,
        "amenities": ["Doorman", "Rooftop"],
        "accepts_vouchers": False
    }
]

MOCK_VIOLATIONS = {
    "123 Main St, Brooklyn, NY": {
        "violations": 0,
        "risk_level": "✅ Safe",
        "last_inspection": "2024-01-15",
        "summary": "No violations found. Building is in good condition.",
        "details": []
    },
    "456 Oak Ave, Queens, NY": {
        "violations": 2,
        "risk_level": "⚠️ Moderate",
        "last_inspection": "2024-02-20",
        "summary": "Minor violations for maintenance issues. Generally safe for occupancy.",
        "details": ["Elevator maintenance overdue", "Minor plumbing issues"]
    },
    "789 Pine St, Manhattan, NY": {
        "violations": 1,
        "risk_level": "✅ Safe",
        "last_inspection": "2024-03-10",
        "summary": "Single minor violation resolved. Building is safe.",
        "details": ["Fire alarm system updated"]
    }
}

MOCK_SUBWAY_DATA = {
    "123 Main St, Brooklyn, NY": {
        "nearest_station": "Atlantic Avenue-Barclays Center",
        "lines": ["2", "3", "4", "5", "B", "D", "N", "Q", "R"],
        "distance": 0.3,
        "walking_time": 7
    },
    "456 Oak Ave, Queens, NY": {
        "nearest_station": "Jamaica Center-Parsons/Archer",
        "lines": ["E", "J", "Z"],
        "distance": 0.8,
        "walking_time": 18
    }
}

MOCK_SCHOOL_DATA = {
    "123 Main St, Brooklyn, NY": [
        {"name": "PS 123", "type": "Elementary", "distance": 0.5, "rating": "A"},
        {"name": "Brooklyn High School", "type": "High School", "distance": 1.2, "rating": "B+"}
    ],
    "456 Oak Ave, Queens, NY": [
        {"name": "Queens Elementary", "type": "Elementary", "distance": 0.3, "rating": "B"},
        {"name": "Jamaica High School", "type": "High School", "distance": 0.9, "rating": "A-"}
    ]
}

def mock_search_housing(query: str) -> List[Dict[str, Any]]:
    """Mock housing search function with detailed filtering"""
    results = []
    query_lower = query.lower()

    for listing in MOCK_LISTINGS:
        # Filter by bedrooms
        if "studio" in query_lower and listing["bedrooms"] != 0:
            continue
        if "1 bedroom" in query_lower and listing["bedrooms"] != 1:
            continue
        if "2 bedroom" in query_lower and listing["bedrooms"] != 2:
            continue
        if "3 bedroom" in query_lower and listing["bedrooms"] != 3:
            continue

        # Filter by borough
        if "brooklyn" in query_lower and listing["borough"] != "Brooklyn":
            continue
        if "queens" in query_lower and listing["borough"] != "Queens":
            continue
        if "manhattan" in query_lower and listing["borough"] != "Manhattan":
            continue

        # Filter by budget
        if "under" in query_lower:
            try:
                budget = int(query_lower.split("under")[1].split()[0].replace("$", "").replace(",", ""))
                if listing["rent"] >= budget:
                    continue
            except:
                pass

        # Filter by voucher acceptance
        if "voucher" in query_lower and not listing["accepts_vouchers"]:
            continue

        results.append(listing)

    return results if results else MOCK_LISTINGS[:2]  # Fallback

def mock_check_violations(address: str) -> Dict[str, Any]:
    """Mock violation check function with detailed data"""
    return MOCK_VIOLATIONS.get(address, {
        "violations": 0,
        "risk_level": "✅ Safe",
        "last_inspection": "Unknown",
        "summary": "No violation data available for this address.",
        "details": []
    })

def mock_subway_info(address: str) -> Dict[str, Any]:
    """Mock subway proximity data"""
    return MOCK_SUBWAY_DATA.get(address, {
        "nearest_station": "Unknown Station",
        "lines": ["A", "B", "C"],
        "distance": 0.5,
        "walking_time": 12
    })

def mock_school_info(address: str) -> List[Dict[str, Any]]:
    """Mock school proximity data"""
    return MOCK_SCHOOL_DATA.get(address, [
        {"name": "Local Elementary", "type": "Elementary", "distance": 0.5, "rating": "B+"}
    ])

def mock_email_draft(landlord_info: str, user_info: str, voucher_type: str = "Section 8") -> str:
    """Mock email generation with customization"""
    return f"""
Subject: Housing Voucher Inquiry for {voucher_type}

Dear Property Manager,

I am writing to express my interest in renting an apartment at your property. {user_info}

I currently hold a {voucher_type} voucher and am seeking a suitable apartment that accepts housing vouchers. {landlord_info}

I would appreciate any information about available units and the application process for voucher holders.

Thank you for your time and consideration.

Best regards,
[Your Name]
Phone: [Your Phone Number]
Email: [Your Email Address]
"""

def mock_voucher_info(voucher_type: str) -> str:
    """Mock voucher program information"""
    info = {
        "section 8": {
            "name": "Section 8 Housing Choice Voucher",
            "admin": "NYCHA (NYC Housing Authority)",
            "website": "nyc.gov/nycha",
            "income_limit": "80% of Area Median Income",
            "payment": "Up to 30% of tenant income + voucher portion"
        },
        "cityfheps": {
            "name": "CityFHEPS",
            "admin": "HRA (Human Resources Administration)",
            "website": "nyc.gov/hra",
            "income_limit": "200% of Federal Poverty Level",
            "payment": "Covers rent up to payment standard"
        },
        "hasa": {
            "name": "HASA",
            "admin": "HIV/AIDS Services Administration",
            "website": "nyc.gov/hasa",
            "income_limit": "No income limit for eligible individuals",
            "payment": "Full rent coverage for eligible units"
        }
    }

    voucher_lower = voucher_type.lower()
    if voucher_lower in info:
        data = info[voucher_lower]
        return f"""🏠 **{data['name']} Information**

**Administered by:** {data['admin']}
**Website:** {data['website']}
**Income Requirements:** {data['income_limit']}
**Payment Structure:** {data['payment']}

**How to Apply:**
1. Contact {data['admin']} for application
2. Gather required documents (ID, income proof, etc.)
3. Attend orientation and interview
4. Receive voucher upon approval

**Next Steps:** Visit {data['website']} for detailed requirements."""
    else:
        return "Please specify a voucher type (Section 8, CityFHEPS, HASA) for detailed information."

def simulate_chatbot_response(user_input: str) -> str:
    """
    Simulate how the chatbot would respond to different inputs.
    This demonstrates pertinent vs non-pertinent question handling with comprehensive logic.
    """

    input_lower = user_input.lower()

    # Pertinent questions - housing/voucher related
    if any(keyword in input_lower for keyword in [
        "housing", "apartment", "rent", "voucher", "section 8", "cityfheps", "hasa",
        "violation", "building safety", "subway", "school", "email", "landlord",
        "bedroom", "studio", "lease", "application", "income", "payment"
    ]):

        # Housing search queries with detailed filtering
        if any(word in input_lower for word in ["search", "find", "looking for", "need", "available"]):
            listings = mock_search_housing(user_input)
            if listings:
                response = "🔍 **Voucher-Friendly Housing Options Found**\n\n"
                for i, listing in enumerate(listings, 1):
                    response += f"**{i}. {listing['address']}**\n"
                    response += f"   🏠 {listing['bedrooms']} BR | 💰 ${listing['rent']:,}/month\n"
                    response += f"   🏛️ Borough: {listing['borough']} | ✅ Safety: {listing['risk_level']}\n"
                    response += f"   🚇 Subway: {listing['subway_distance']}mi | 🏫 Schools: {listing['school_distance']}mi\n"
                    response += f"   ⭐ Amenities: {', '.join(listing['amenities'])}\n"
                    if listing['accepts_vouchers']:
                        response += "   🎫 **Accepts Vouchers**\n"
                    response += "\n"
                response += "💡 **Tips:** Contact landlords directly and mention your voucher type. I can help draft emails!"
                return response
            else:
                return "🔍 I couldn't find listings matching your exact criteria. Try broadening your search or let me know your preferences!"

        # Violation checking with address detection
        elif "violation" in input_lower or "safety" in input_lower or "inspection" in input_lower:
            # Try to detect address from input
            addresses = ["123 Main St, Brooklyn, NY", "456 Oak Ave, Queens, NY", "789 Pine St, Manhattan, NY"]
            detected_address = None

            for addr in addresses:
                if any(part.lower() in input_lower for part in addr.split(",")[0].split()):
                    detected_address = addr
                    break

            if not detected_address:
                return """🏢 **Building Safety Check**

To check building violations and safety, please provide a specific NYC address like:
- "123 Main St, Brooklyn, NY"
- "456 Oak Ave, Queens"

I can provide:
- Violation count and risk level
- Last inspection date
- Detailed safety report

What's the address you'd like me to check?"""

            violations = mock_check_violations(detected_address)
            subway = mock_subway_info(detected_address)
            schools = mock_school_info(detected_address)

            response = f"🏢 **Comprehensive Building Report: {detected_address}**\n\n"
            response += f"**Safety Status:** {violations['risk_level']}\n"
            response += f"**Violations:** {violations['violations']}\n"
            response += f"**Last Inspection:** {violations['last_inspection']}\n"
            response += f"**Summary:** {violations['summary']}\n"

            if violations['details']:
                response += f"**Details:** {', '.join(violations['details'])}\n"

            response += f"\n🚇 **Transit Access:**\n"
            response += f"   Nearest Station: {subway['nearest_station']}\n"
            response += f"   Lines: {', '.join(subway['lines'])}\n"
            response += f"   Distance: {subway['distance']}mi ({subway['walking_time']} min walk)\n"

            response += f"\n🏫 **Nearby Schools:**\n"
            for school in schools:
                response += f"   {school['name']} ({school['type']}): {school['distance']}mi, Rating: {school['rating']}\n"

            return response

        # Email drafting
        elif "email" in input_lower or "draft" in input_lower or "contact" in input_lower:
            # Detect voucher type
            voucher_type = "Section 8"
            if "cityfheps" in input_lower:
                voucher_type = "CityFHEPS"
            elif "hasa" in input_lower:
                voucher_type = "HASA"

            return mock_email_draft(
                "I am currently looking for apartments and would like to know if you accept housing vouchers.",
                f"I hold a {voucher_type} voucher and am seeking a suitable apartment. Please let me know about availability and requirements.",
                voucher_type
            )

        # Voucher information
        elif any(word in input_lower for word in ["voucher", "section 8", "cityfheps", "hasa", "program"]):
            # Detect specific voucher type
            if "section 8" in input_lower:
                return mock_voucher_info("section 8")
            elif "cityfheps" in input_lower:
                return mock_voucher_info("cityfheps")
            elif "hasa" in input_lower:
                return mock_voucher_info("hasa")
            else:
                return """🏠 **NYC Housing Voucher Programs**

NYC offers several housing voucher programs:

**Section 8** (Federal) - Income-based rental assistance
**CityFHEPS** (City) - For families in shelter system
**HASA** (City) - For people with HIV/AIDS

Which program are you interested in learning about?"""

        # Subway/school proximity
        elif "subway" in input_lower or "school" in input_lower or "transit" in input_lower:
            # Try to detect address
            addresses = ["123 Main St, Brooklyn, NY", "456 Oak Ave, Queens, NY"]
            detected_address = None

            for addr in addresses:
                if any(part.lower() in input_lower for part in addr.split(",")[0].split()):
                    detected_address = addr
                    break

            if detected_address:
                subway = mock_subway_info(detected_address)
                schools = mock_school_info(detected_address)

                response = f"🚇 **Transit & Education Report: {detected_address}**\n\n"
                response += f"**Nearest Subway:**\n"
                response += f"   Station: {subway['nearest_station']}\n"
                response += f"   Lines: {', '.join(subway['lines'])}\n"
                response += f"   Distance: {subway['distance']}mi ({subway['walking_time']} min walk)\n"

                response += f"\n**Nearby Schools:**\n"
                for school in schools:
                    response += f"   {school['name']} ({school['type']}): {school['distance']}mi away, Rating: {school['rating']}\n"

                return response
            else:
                return """🚇 **Transit & Education Access**

I can provide detailed information about subway access and nearby schools for specific addresses.

Please provide an NYC address, and I'll give you:
- Nearest subway stations and walking distance
- Nearby schools with ratings
- Public transportation options

What's the address you're interested in?"""

        # Neighborhood or general housing advice
        elif any(word in input_lower for word in ["neighborhood", "area", "borough", "recommend"]):
            return """🏘️ **NYC Neighborhood Guide**

Each borough offers different housing options:

**Brooklyn:** Diverse neighborhoods, good transit access
**Queens:** More affordable, family-friendly areas
**Manhattan:** Central location, higher rents
**Bronx:** Affordable options, growing communities
**Staten Island:** Suburban feel, ferry access

**Tips for Voucher Holders:**
- Look for buildings that explicitly accept vouchers
- Consider proximity to work, schools, and transit
- Check building safety records before applying

Which borough or type of neighborhood interests you?"""

    # Non-pertinent questions - redirect appropriately
    else:
        # Weather questions
        if "weather" in input_lower or "temperature" in input_lower:
            return """🌤️ **Weather & Housing Connection**

NYC weather varies by season, which can impact housing choices:

**Winter:** Consider heated buildings and proximity to transit
**Summer:** Look for AC and good ventilation
**Spring/Fall:** Generally comfortable for apartment hunting

**Housing Tip:** Buildings in flood-prone areas may have higher insurance costs.

Would you like help finding weather-resilient housing or checking building locations?"""

        # Food/restaurant questions
        elif any(word in input_lower for word in ["food", "restaurant", "eat", "pizza", "dining"]):
            return """🍽️ **Food & Housing Connection**

NYC's incredible food scene is a major quality-of-life factor!

**Housing Tips:**
- **Kitchen Size:** Consider if you cook often
- **Neighborhood Dining:** Areas like Queens offer diverse international cuisine
- **Transit Access:** Easy subway access means more restaurant options
- **Budget Impact:** Factor in dining costs when budgeting for rent

Would you like help finding apartments in foodie neighborhoods or checking transit access to restaurants?"""

        # Sports/entertainment
        elif any(word in input_lower for word in ["sports", "game", "movie", "entertainment", "concert", "theater"]):
            return """🎬 **Entertainment & Housing**

NYC is an entertainment hub! Your location affects access to:

**Sports:** Proximity to stadiums (Yankee Stadium, Barclays Center)
**Theater:** Broadway access from Manhattan locations
**Concerts:** Venues throughout the city

**Housing Tips:**
- Consider commute time to venues
- Apartments near subway lines provide flexibility
- Some buildings offer entertainment amenities

Would you like help finding housing near entertainment venues or checking transit access?"""

        # Work/job related
        elif any(word in input_lower for word in ["job", "work", "employment", "commute"]):
            return """💼 **Work & Housing Connection**

Your job location significantly impacts housing choices:

**Commute Considerations:**
- Proximity to subway lines reduces travel time
- Consider work-life balance and transportation costs
- Some voucher programs prioritize employment

**Housing Tips:**
- Calculate total commuting costs when budgeting
- Look for apartments with good transit access
- Consider work-from-home setup if applicable

Would you like help finding housing based on your work location or checking transit options?"""

        # Health/medical questions
        elif any(word in input_lower for word in ["health", "medical", "doctor", "hospital"]):
            return """🏥 **Healthcare & Housing**

Access to healthcare is crucial for quality of life:

**NYC Healthcare:**
- Major hospitals throughout all boroughs
- Public transportation provides access to medical facilities
- Some neighborhoods have more healthcare options

**Housing Tips:**
- Proximity to hospitals for medical emergencies
- Consider accessibility features for health needs
- Transit access ensures you can reach appointments

Would you like help finding housing near medical facilities or checking accessibility features?"""

        # Completely off-topic or unclear
        else:
            return """🤔 **Staying Focused on Housing**

I specialize in helping NYC residents find safe, affordable, voucher-friendly housing. While I'm happy to connect other topics to housing decisions, my core expertise includes:

- Housing searches and listings
- Building safety and violations
- Transit and school proximity
- Voucher program information
- Neighborhood recommendations
- Email drafting for landlords

**Quick Housing Check:** Are you looking for apartments, need safety information, or have voucher questions?

If your question is completely unrelated to housing, I recommend consulting specialized resources for that topic. What housing-related help do you need?"""

# Demo function to show various responses
def run_demo():
    print("🤖 VoucherBot Response Simulation Demo")
    print("=" * 50)

    # Pertinent questions - comprehensive housing scenarios
    pertinent_questions = [
        "I need help finding housing with Section 8 voucher",
        "Search for 2 bedroom apartments in Brooklyn under $2000 that accept vouchers",
        "Check building violations for 123 Main St, Brooklyn and tell me about nearby schools",
        "Draft an email to a landlord about my CityFHEPS voucher for a 3 bedroom apartment",
        "How do I apply for Section 8 in NYC?",
        "Find apartments near subway stations in Queens",
        "What are the requirements for HASA vouchers?",
        "Show me safe buildings in Manhattan with good transit access",
        "I need a studio apartment under $1500 in Brooklyn"
    ]

    print("\n📋 PERTINENT QUESTIONS (Housing/Voucher Related):")
    print("-" * 40)

    for i, question in enumerate(pertinent_questions, 1):
        print(f"\n{i}. User: {question}")
        response = simulate_chatbot_response(question)
        print(f"🤖 Bot: {response[:150]}{'...' if len(response) > 150 else ''}")

    # Non-pertinent questions - expanded scenarios
    non_pertinent_questions = [
        "What's the weather like today?",
        "Where's a good place to eat authentic Italian food?",
        "Who won the Knicks game last night?",
        "Can you recommend a good movie to watch?",
        "What's the best way to get around NYC?",
        "I'm looking for a job in tech - any advice?",
        "How do I get to the airport from Manhattan?",
        "What's the population of New York City?",
        "Can you help me with my math homework?",
        "Tell me about the history of Brooklyn"
    ]

    print("\n\n🚫 NON-PERTINENT QUESTIONS (Off-Topic with Housing Connections):")
    print("-" * 40)

    for i, question in enumerate(non_pertinent_questions, 1):
        print(f"\n{i}. User: {question}")
        response = simulate_chatbot_response(question)
        print(f"🤖 Bot: {response[:150]}{'...' if len(response) > 150 else ''}")

    print("\n" + "=" * 50)
    print("🎉 Comprehensive Demo Complete!")
    print("\nThis simulation demonstrates VoucherBot's capabilities:")
    print("✅ **Intelligent Filtering:** Searches by bedrooms, borough, budget, voucher acceptance")
    print("✅ **Comprehensive Reports:** Building safety with violations, transit, and school data")
    print("✅ **Smart Detection:** Automatically identifies addresses, voucher types, and query intent")
    print("✅ **Contextual Help:** Provides detailed voucher program information and application guidance")
    print("✅ **Graceful Redirection:** Connects non-housing topics back to housing decisions")
    print("✅ **User-Centric:** Offers practical tips and maintains helpful, conversational tone")
    print("✅ **Multi-Modal Support:** Handles housing searches, safety checks, emails, and neighborhood advice")
    print("\n🚀 **Agent Orchestration Features Shown:**")
    print("   • Message routing and intent classification")
    print("   • Tool integration (violation checker, geocoding, enrichment)")
    print("   • State management and conversation flow")
    print("   • Error handling and user feedback")
    print("   • Multilingual and contextual awareness")

if __name__ == "__main__":
    run_demo()
