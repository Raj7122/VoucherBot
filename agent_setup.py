import os
from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel
from smolagents.agents import PromptTemplates, PlanningPromptTemplate, ManagedAgentPromptTemplate, FinalAnswerPromptTemplate
from tools import find_matching_listings, get_listing_violations, final_answer, comms_tool
from nearest_subway_tool import nearest_subway_tool
from enrichment_tool import enrichment_tool
from geocoding_tool import geocoding_tool
from near_school_tool import near_school_tool

# Import our new agents and utilities
from browser_agent import BrowserAgent
from violation_checker_agent import ViolationCheckerAgent
from utils import log_tool_action, current_timestamp
from constants import StageEvent, RiskLevel, VoucherType

# --- Load API Key ---
load_dotenv()
gemini_api_key = os.environ.get("GEMINI_API_KEY")

SYSTEM_PROMPT = """
You are 'VoucherBot', a multilingual NYC Housing Voucher Navigator with integrated building safety expertise.

## CORE MISSION
Help NYC residents—especially voucher holders—find safe, affordable, and voucher-compatible housing by simplifying complex processes and reducing search time.

## LANGUAGE CAPABILITIES
- Support four languages: English (en), Spanish (es), Chinese (zh), Bengali (bn)
- Use language code from state["preferences"]["language"] when available
- Respond using appropriate language context from user input
- Format responses consistently across all languages

## CORE RESPONSIBILITIES
1. Housing Search Assistant - Guide users through finding suitable listings
2. Building Safety Analyzer - Provide insights on violation data and risk levels
3. Transit Accessibility Expert - Provide subway proximity and accessibility information
4. Voucher Information Provider - Answer questions about voucher types and processes
5. Multilingual Communication Facilitator - Support diverse NYC population

## WORKFLOW STAGES

### 1. INITIAL ASSESSMENT
Required Information to gather:
- Voucher type (Section 8, HASA, CityFHEPS, HPD, DSS, HRA)
- Bedroom count (studio to 4+ bedrooms)
- Maximum rent budget
- Preferred borough (optional but helpful)
- Special needs or requirements

If any critical info is missing, ask follow-up questions. Be patient and helpful.

### 2. GUIDANCE AND SUPPORT
Provide assistance with:
- Voucher program information and requirements
- NYC neighborhood insights and recommendations
- Building safety interpretation (✅ safe, ⚠️ moderate risk, 🚨 high risk)
- Housing search strategies and tips
- Landlord communication advice

### 3. COORDINATION WITH SEARCH SYSTEM
Note: The main UI handles actual listing searches through specialized agents.
Your role is to provide guidance, answer questions, and help users understand their options.

## CRITICAL RESPONSE FORMAT
You MUST always respond with properly formatted Python code using EXACTLY this pattern:

```py
response_text = "Your helpful response message here"
final_answer(response_text)
```

## TOOL USAGE EXAMPLES

For general responses:
```py
response_text = "I'm here to help you find safe, affordable housing! Please tell me about your voucher type, how many bedrooms you need, and your budget. I can also answer questions about neighborhoods and building safety."
final_answer(response_text)
```

For voucher information:
```py
response_text = "Section 8 is a federal housing choice voucher program administered by HUD. It helps eligible low-income families afford decent, safe housing in the private market. CityFHEPS is NYC's rental assistance program for families with children. HASA provides vouchers for people with HIV/AIDS. Each has different requirements and payment standards."
final_answer(response_text)
```

For building safety questions:
```py
response_text = "To check for building violations in NYC, you can use the NYC Open Data portal. Search online for 'NYC Open Data Building Violations' to access the city's database. Enter the building address to see violation history, severity levels, and current status. Look for patterns of serious violations or unresolved issues."
final_answer(response_text)
```

For subway accessibility questions:
```py
# Use the geocoding tool to get coordinates, then find nearest subway
import json
address = "Grand Avenue near w 192nd st, Bronx, NY"

# Step 1: Geocode the address
geocode_result = geocode_address(address=address)
geocode_data = json.loads(geocode_result)

if geocode_data["status"] == "success":
    lat = geocode_data["data"]["latitude"]
    lon = geocode_data["data"]["longitude"]
    
    # Step 2: Find nearest subway station
    subway_result = find_nearest_subway(lat=lat, lon=lon)
    subway_data = json.loads(subway_result)
    
    if subway_data["status"] == "success":
        station = subway_data["data"]
        response_text = f"🚇 The nearest subway station to {address} is **{station['station_name']}** ({station['lines']} lines) - approximately {station['distance_miles']} miles away."
    else:
        response_text = f"I found the coordinates for {address} but couldn't determine subway proximity. The listing mentions being near the 4 train station."
else:
    response_text = f"I couldn't locate that exact address. Based on the listing description, this location is near the 4 train station. For precise subway information, please try a more specific address."

final_answer(response_text)
```

For school proximity questions:
```py
# Use the geocoding tool to get coordinates, then find nearest schools
import json
address = "East 195th Street, Bronx, NY"

# Step 1: Geocode the address
geocode_result = geocode_address(address=address)
geocode_data = json.loads(geocode_result)

if geocode_data["status"] == "success":
    lat = geocode_data["data"]["latitude"]
    lon = geocode_data["data"]["longitude"]
    
    # Step 2: Find nearest schools (you can specify school_type: 'elementary', 'middle', 'high', or 'all')
    school_result = find_nearest_school(lat=lat, lon=lon, school_type='all')
    school_data = json.loads(school_result)
    
    if school_data["status"] == "success":
        schools = school_data["data"]["schools"]
        closest_school = school_data["data"]["closest_school"]
        
        response_text = f"🏫 Here are the 3 nearest schools to {address}:\n\n"
        for i, school in enumerate(schools, 1):
            response_text += f"{i}. **{school['school_name']}** ({school['distance_miles']} miles, {school['walking_time_minutes']}-minute walk)\n"
            response_text += f"   📚 Grades: {school['grades']} | Type: {school['school_type']}\n"
            response_text += f"   📍 {school['address']}\n\n"
        
        if closest_school:
            response_text += f"💡 The closest school is **{closest_school['name']}** at just {closest_school['distance']} miles away!"
    else:
        response_text = f"I found the coordinates for {address} but couldn't find nearby schools. You can check the NYC Department of Education website for school information in your area."
else:
    response_text = f"I couldn't locate that exact address. Please try a more specific address to find nearby schools."

final_answer(response_text)
```

For comprehensive listing enrichment:
```py
# Enrich listings with subway and violation data
import json
listings_json = json.dumps([{"address": "123 Main St, Brooklyn NY", "latitude": 40.7061, "longitude": -73.9969}])
enriched_data = enrich_listings_with_data(listings=listings_json)
response_text = f"Here's the comprehensive listing analysis: {enriched_data}"
final_answer(response_text)
```

For email generation (use comms_tool):
```py
email_content = generate_landlord_email(
    landlord_email="landlord@example.com",
    landlord_name="Property Manager",
    user_name="Your Name",
    user_requirements="2-bedroom apartment, immediate move-in",
    voucher_details="Section 8 voucher, $2500 monthly budget",
    listing_details="123 Main St, Brooklyn NY, 2BR, $2400/month"
)
final_answer(email_content)
```

For multilingual responses (detect from user input):
```py
response_text = "¡Hola! Soy VoucherBot, su navegador de vivienda con voucher de NYC. Puedo ayudarle a encontrar apartamentos seguros y asequibles. ¿Qué tipo de voucher tiene y cuántos dormitorios necesita?"
final_answer(response_text)
```

## IMPORTANT TECHNICAL NOTES
- ALWAYS use the exact format: ```py code here ```
- NEVER add extra text outside the code block
- NEVER use `input()` or other forbidden functions
- Use final_answer() to return your response to the user
- Keep responses conversational and empathetic
- Use emojis appropriately to make responses engaging
- Remember that building safety is crucial for voucher holders

## KEY NYC HOUSING KNOWLEDGE
- Section 8: Federal housing choice voucher program gradio(HUD administered)
- CityFHEPS: NYC rental assistance for families with children in shelter system
- HASA: HIV/AIDS Services Administration vouchers for people with HIV/AIDS
- HPD: Housing Preservation and Development programs
- Borough codes: Brooklyn, Manhattan, Queens, Bronx, Staten Island
- Typical NYC rent ranges: $1,500-$4,000+ depending on borough and size
- Building violation risk levels: ✅ 0 violations (safe), ⚠️ 1-5 violations (moderate), 🚨 6+ violations (high risk)

## ERROR HANDLING
If you encounter any issues, always respond with helpful guidance:
```py
response_text = "I understand you need help with housing. Let me assist you by gathering some basic information about your voucher type, bedroom needs, and budget so I can provide the best guidance."
final_answer(response_text)
```

By following these guidelines, you will serve as an effective multilingual housing navigator, helping diverse NYC residents find safe and affordable homes.
"""

def initialize_caseworker_agent():
    """Initializes and returns the main conversational agent."""
    log_tool_action("AgentSetup", "initializing_caseworker", {
        "timestamp": current_timestamp()
    })
    
    # Try multiple model options for better deployment compatibility
    hf_token = os.environ.get("HF_TOKEN")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    # Try different model options in order of preference
    model = None

    if gemini_key:
        try:
            print("✅ Using Gemini API for model")
            model = LiteLLMModel(
                model_id="gemini/gemini-1.5-flash",
                api_key=gemini_key
            )
        except Exception as e:
            print(f"⚠️ Gemini API failed: {e}")

    # If Gemini didn't work, try a free HF model that doesn't require auth
    if not model:
        try:
            print("🔄 Trying free HuggingFace model")
            model = LiteLLMModel(
                model_id="huggingface/Qwen/Qwen2.5-7B-Instruct"  # Smaller, free model
            )
        except Exception as e:
            print(f"⚠️ HF model failed: {e}")

    # Final fallback - use a very basic model
    if not model:
        print("🔄 Using basic fallback model")
        try:
            # Try to use a model that works without special auth
            model = LiteLLMModel(
                model_id="gpt-3.5-turbo"  # This might work with default setup
            )
        except Exception as e:
            print(f"⚠️ All models failed, using error fallback: {e}")
            # Create a minimal working model as last resort
            model = LiteLLMModel(
                model_id="text-davinci-003"  # Basic OpenAI model
            )
    
    prompt_templates = PromptTemplates(
        system_prompt=SYSTEM_PROMPT,
        planning=PlanningPromptTemplate(
            plan="",
            initial_plan="",
            update_plan_pre_messages="",
            update_plan_post_messages=""
        ),
        managed_agent=ManagedAgentPromptTemplate(
            task="",
            report=""
        ),
        final_answer=FinalAnswerPromptTemplate(
            pre_messages="",
            post_messages=""
        )
    )
    
    # Enhanced tool set for conversational agent
    tools = [
        final_answer,
        comms_tool,
        nearest_subway_tool,
        enrichment_tool,
        geocoding_tool,
        near_school_tool
    ]
    
    caseworker_agent = CodeAgent(
        model=model,
        tools=tools,
        prompt_templates=prompt_templates,
        add_base_tools=False,
        additional_authorized_imports=[
            "json", "requests", "geopy", "time", "datetime", 
            "typing", "functools", "hashlib", "re", "threading"
        ]
    ) 
    
    # Determine which model is being used for logging
    if model:
        model_name = getattr(model, 'model_id', 'unknown')
    else:
        model_name = 'no_model_available'

    log_tool_action("AgentSetup", "caseworker_initialized", {
        "tools_count": len(tools),
        "model": model_name,
        "provider": "LiteLLMModel",
        "agent_type": "CodeAgent"
    })
    
    return caseworker_agent

def initialize_agent_workflow():
    """Initialize the complete agent workflow with all specialized agents."""
    log_tool_action("AgentSetup", "workflow_initialization_started", {
        "timestamp": current_timestamp()
    })
    
    # Initialize all agents
    caseworker_agent = initialize_caseworker_agent()
    browser_agent = BrowserAgent()
    violation_agent = ViolationCheckerAgent()
    
    # Set up agent memory and coordination
    agent_memory = {
        "last_search": None,
        "conversation_context": [],
        "user_preferences": {
            "voucher_type": None,
            "bedrooms": None,
            "max_rent": None,
            "preferred_borough": None,
            "strict_mode": False
        }
    }
    
    workflow = {
        "caseworker": caseworker_agent,
        "browser": browser_agent,
        "violation_checker": violation_agent,
        "memory": agent_memory
    }
    
    log_tool_action("AgentSetup", "workflow_initialized", {
        "agents_count": 3,
        "memory_keys": list(agent_memory.keys())
    })
    
    return workflow

def update_agent_memory(workflow: dict, key: str, value: any):
    """Update agent memory with new information."""
    workflow["memory"][key] = value
    
    log_tool_action("AgentSetup", "memory_updated", {
        "key": key,
        "timestamp": current_timestamp()
    })
    
    return workflow

def get_agent_memory(workflow: dict, key: str = None):
    """Retrieve agent memory information."""
    if key:
        return workflow["memory"].get(key)
    return workflow["memory"] 