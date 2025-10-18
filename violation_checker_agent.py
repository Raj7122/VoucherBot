import json
import time
import requests
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from smolagents import Tool
import logging

# Import our new utilities and mixins
from utils import log_tool_action, current_timestamp
from mixins import TimedObservationMixin
from constants import RiskLevel, VIOLATION_RISK_THRESHOLDS

# Set up logging for detailed error tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ViolationCheckerAgent(TimedObservationMixin, Tool):
    """
    smolagents Tool for checking NYC building safety violations using NYC Open Data.
    Provides structured violation data with retry logic and caching.
    """
    
    name = "violation_checker"
    description = (
        "Check NYC building safety violations for a given address. "
        "Returns violation count, inspection dates, risk level, and summary."
    )
    inputs = {
        "address": {
            "type": "string", 
            "description": "NYC address to check for building violations (e.g., '123 Main St, Brooklyn NY')",
            "nullable": True
        }
    }
    output_type = "string"  # JSON-formatted string
    
    def __init__(self):
        super().__init__()
        # Caching setup
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        # Optional GeoClient tool for real BBL conversion (set via set_geoclient_tool)
        self.geoclient_tool = None
        
        # NYC Open Data API endpoints
        self.violations_api_url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
        self.geoclient_api_url = "https://api.cityofnewyork.us/geoclient/v1/address.json"
        
        # API configuration
        self.max_retries = 3
        self.base_delay = 1  # seconds for exponential backoff
        self.timeout = 30
        
        # Add this attribute that smolagents might expect
        self.is_initialized = True
        
        print("🏢 ViolationCheckerAgent initialized with caching and retry logic")
    
    def set_geoclient_tool(self, geoclient_tool):
        """Set the GeoClient tool for real BBL conversion."""
        self.geoclient_tool = geoclient_tool
        if geoclient_tool:
            print("✅ Real GeoClient BBL conversion enabled")
        else:
            print("🧪 Using mock BBL generation")
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid based on TTL."""
        if key not in self._cache:
            return False
        
        data, timestamp = self._cache[key]
        return (time.time() - timestamp) < self._cache_ttl
    
    def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve valid cached data."""
        if self._is_cache_valid(key):
            data, _ = self._cache[key]
            print(f"📋 Using cached violation data for: {key}")
            return data
        return None
    
    def _cache_data(self, key: str, data: Dict[str, Any]) -> None:
        """Store data in cache with timestamp."""
        self._cache[key] = (data, time.time())
        print(f"💾 Cached violation data for: {key}")
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address format for consistent caching."""
        # Convert to uppercase and remove extra spaces
        normalized = re.sub(r'\s+', ' ', address.upper().strip())
        # Remove common suffixes that might vary
        normalized = re.sub(r',?\s*(NY|NEW YORK)\s*\d*$', '', normalized)
        return normalized
    
    def _extract_address_components(self, address: str) -> Dict[str, str]:
        """Extract house number, street name, and borough from address."""
        # Simple regex pattern for NYC addresses
        pattern = r'^(\d+[A-Z]?)\s+(.+?)(?:,\s*(.+?))?(?:\s+NY)?$'
        match = re.match(pattern, address.upper().strip())
        
        if match:
            house_number = match.group(1)
            street_name = match.group(2)
            borough = match.group(3) if match.group(3) else "MANHATTAN"  # Default
            
            return {
                "house_number": house_number,
                "street_name": street_name,
                "borough": borough
            }
        else:
            # Fallback parsing
            parts = address.split(',')
            street_part = parts[0].strip()
            borough_part = parts[1].strip() if len(parts) > 1 else "MANHATTAN"
            
            # Extract house number
            street_match = re.match(r'^(\d+[A-Z]?)\s+(.+)$', street_part)
            if street_match:
                house_number = street_match.group(1)
                street_name = street_match.group(2)
            else:
                house_number = ""
                street_name = street_part
            
            return {
                "house_number": house_number,
                "street_name": street_name,
                "borough": borough_part
            }
    
    def _get_bbl_from_address_real(self, address: str) -> Optional[str]:
        """Convert address to BBL using real GeoClient API."""
        if not self.geoclient_tool:
            return None
            
        print(f"🌍 Converting address to BBL using REAL GeoClient API: {address}")
        
        try:
            components = self._extract_address_components(address)
            
            # Call the real GeoClient tool
            bbl_result = self.geoclient_tool.forward(
                houseNumber=components["house_number"],
                street=components["street_name"],
                borough=components["borough"]
            )
            
            # Check if we got a valid BBL (10 digits)
            if bbl_result and len(bbl_result) == 10 and bbl_result.isdigit():
                print(f"✅ Real BBL obtained: {bbl_result} for {address}")
                return bbl_result
            else:
                print(f"⚠️ GeoClient error or invalid BBL: {bbl_result}")
                return None
                
        except Exception as e:
            print(f"❌ Real GeoClient BBL conversion failed: {str(e)}")
            return None
    
    def _get_bbl_from_address_mock(self, address: str) -> Optional[str]:
        """Generate mock BBL for testing when real GeoClient is not available."""
        print(f"🧪 Generating mock BBL for testing: {address}")
        
        try:
            components = self._extract_address_components(address)
            
            # Borough codes for mock BBL
            borough_codes = {
                "MANHATTAN": "1",
                "BRONX": "2", 
                "BROOKLYN": "3",
                "QUEENS": "4",
                "STATEN ISLAND": "5"
            }
            
            borough = components.get("borough", "MANHATTAN")
            for key in borough_codes:
                if key in borough.upper():
                    borough_code = borough_codes[key]
                    break
            else:
                borough_code = "1"  # Default to Manhattan
            
            # Generate deterministic mock block and lot
            house_num = components.get("house_number", "1")
            street_name = components.get("street_name", "")
            
            # Use hash for consistent mock BBL generation
            block_hash = abs(hash(street_name)) % 9999 + 1
            lot_hash = abs(hash(house_num + street_name)) % 999 + 1
            
            block = str(block_hash).zfill(4)
            lot = str(lot_hash).zfill(3)
            
            bbl = f"{borough_code}{block}{lot}"
            print(f"🧪 Mock BBL generated: {bbl} for {address}")
            return bbl
            
        except Exception as e:
            print(f"❌ Mock BBL generation failed: {str(e)}")
            return None
    
    def _get_bbl_from_address(self, address: str) -> Optional[str]:
        """Convert address to BBL using real GeoClient API if available, otherwise use mock."""
        # Try real GeoClient first
        if self.geoclient_tool:
            bbl = self._get_bbl_from_address_real(address)
            if bbl:
                return bbl
            else:
                print("⚠️ Real GeoClient failed, falling back to mock BBL")
        
        # Fallback to mock BBL
        return self._get_bbl_from_address_mock(address)
    
    def _retry_request(self, url: str, params: Dict[str, Any]) -> Optional[requests.Response]:
        """Make HTTP request with exponential backoff retry logic."""
        for attempt in range(self.max_retries):
            try:
                print(f"🔄 API request attempt {attempt + 1}/{self.max_retries}")
                response = requests.get(
                    url, 
                    params=params, 
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'ViolationChecker/1.0',
                        'Accept': 'application/json'
                    }
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                delay = self.base_delay * (2 ** attempt)
                print(f"❌ Request failed (attempt {attempt + 1}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    print(f"⏳ Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"💥 All {self.max_retries} attempts failed")
                    return None
    
    def _query_violations_data(self, bbl: str) -> List[Dict[str, Any]]:
        """Query NYC Open Data for violation records using BBL."""
        print(f"🔍 Querying violations for BBL: {bbl}")
        
        params = {
            "$where": f"bbl='{bbl}'",
            "$limit": 1000,  # Get up to 1000 violations
            "$order": "inspectiondate DESC"
        }
        
        response = self._retry_request(self.violations_api_url, params)
        
        if response is None:
            print("❌ Failed to retrieve violation data after retries")
            return []
        
        try:
            violations = response.json()
            print(f"📊 Found {len(violations)} violation records")
            return violations
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse violations JSON: {str(e)}")
            return []
    
    def _analyze_violations(self, violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze violation data and generate structured insights."""
        if not violations:
            return {
                "violations": 0,
                "last_inspection": "N/A",
                "risk_level": RiskLevel.SAFE.value,
                "summary": "No violation records found"
            }
        
        # Count open violations (not resolved)
        open_violations = [
            v for v in violations 
            if v.get("currentstatusdate") is None or v.get("currentstatus") in ["Open", "OPEN"]
        ]
        
        violation_count = len(open_violations)
        
        # Determine risk level using constants
        if violation_count <= VIOLATION_RISK_THRESHOLDS["safe"]:
            risk_level = RiskLevel.SAFE.value
        elif violation_count <= VIOLATION_RISK_THRESHOLDS["moderate"]:
            risk_level = RiskLevel.MODERATE.value
        else:
            risk_level = RiskLevel.HIGH_RISK.value
        
        # Get last inspection date
        last_inspection = "N/A"
        if violations:
            latest = violations[0]  # Already ordered by date DESC
            inspection_date = latest.get("inspectiondate")
            if inspection_date:
                # Parse date (format: 2024-10-05T00:00:00.000)
                try:
                    last_inspection = inspection_date.split('T')[0]
                except:
                    last_inspection = inspection_date
        
        # Generate summary of top violations
        violation_descriptions = []
        for violation in open_violations[:3]:  # Top 3
            desc = violation.get("violationdescription") or violation.get("class")
            if desc and desc not in violation_descriptions:
                violation_descriptions.append(desc)
        
        summary = ", ".join(violation_descriptions) if violation_descriptions else "No specific violations listed"
        
        result = {
            "violations": violation_count,
            "last_inspection": last_inspection,
            "risk_level": risk_level,
            "summary": summary
        }
        
        print(f"📋 Analysis complete: {violation_count} violations, risk level {risk_level}")
        return result
    
    def forward(self, address: str = None) -> str:
        """
        Main tool function: Check violations for given address.
        Returns JSON-formatted string with violation data.
        """
        with self.timed_observation() as timer:
            # Validate address input
            if not address:
                return json.dumps(timer.error(
                    "Address is required",
                    data={"error": "No address provided"}
                ))
            
            log_tool_action("ViolationCheckerAgent", "check_started", {
                "address": address,
                "timestamp": current_timestamp()
            })
            
            # Normalize address for caching
            cache_key = self._normalize_address(address)
            
            # Check cache first
            cached_result = self._get_cached_data(cache_key)
            if cached_result:
                log_tool_action("ViolationCheckerAgent", "cache_hit", {
                    "address": address,
                    "cache_key": cache_key
                })
                return json.dumps(cached_result)
            
            try:
                # Convert address to BBL
                log_tool_action("ViolationCheckerAgent", "bbl_conversion_started", {
                    "address": address
                })
                
                bbl = self._get_bbl_from_address(address)
                if not bbl:
                    error_result = {
                        "violations": 0,
                        "last_inspection": "N/A",
                        "risk_level": RiskLevel.SAFE.value,
                        "summary": "Could not convert address to BBL"
                    }
                    
                    log_tool_action("ViolationCheckerAgent", "bbl_conversion_failed", {
                        "address": address,
                        "error": "BBL conversion failed"
                    })
                    
                    return json.dumps(timer.error(
                        "BBL conversion failed", 
                        data=error_result
                    ))
                
                log_tool_action("ViolationCheckerAgent", "bbl_conversion_success", {
                    "address": address,
                    "bbl": bbl
                })
                
                # Query violation data
                log_tool_action("ViolationCheckerAgent", "violations_query_started", {
                    "bbl": bbl
                })
                
                violations = self._query_violations_data(bbl)
                
                log_tool_action("ViolationCheckerAgent", "violations_query_complete", {
                    "bbl": bbl,
                    "violations_found": len(violations)
                })
                
                # Analyze and structure the data
                result = self._analyze_violations(violations)
                
                # Cache the result
                self._cache_data(cache_key, result)
                
                log_tool_action("ViolationCheckerAgent", "check_complete", {
                    "address": address,
                    "violations": result["violations"],
                    "risk_level": result["risk_level"]
                })
                
                return json.dumps(timer.success({
                    "address": address,
                    "bbl": bbl,
                    **result
                }))
                
            except Exception as e:
                error_msg = f"Unexpected error checking violations: {str(e)}"
                logger.exception("Violation check failed")
                
                log_tool_action("ViolationCheckerAgent", "check_failed", {
                    "address": address,
                    "error": str(e)
                })
                
                error_result = {
                    "violations": 0,
                    "last_inspection": "N/A",
                    "risk_level": RiskLevel.UNKNOWN.value,
                    "summary": "Could not retrieve violation data"
                }
                
                return json.dumps(timer.error(error_msg, data=error_result))


def enrich_listings_with_violations(listings: List[Dict[str, Any]], checker: ViolationCheckerAgent) -> List[Dict[str, Any]]:
    """
    Enrich apartment listings with building violation data.
    
    Args:
        listings: List of listing dictionaries with 'address' field
        checker: ViolationCheckerAgent instance
    
    Returns:
        List of listings enriched with violation data
    """
    print(f"\n🔧 Enriching {len(listings)} listings with violation data...")
    
    enriched_listings = []
    
    for i, listing in enumerate(listings, 1):
        print(f"\n📍 Processing listing {i}/{len(listings)}")
        
        # Get address from listing
        address = listing.get("address") or listing.get("title", "")
        
        if not address:
            print("⚠️ No address found in listing, skipping violation check")
            enriched_listings.append(listing)
            continue
        
        try:
            # Call the violation checker
            violation_json = checker.forward(address)
            violation_data = json.loads(violation_json)
            
            # Merge violation data into listing
            enriched_listing = listing.copy()
            enriched_listing.update({
                "building_violations": violation_data["violations"],
                "last_inspection": violation_data["last_inspection"],
                "safety_risk_level": violation_data["risk_level"],
                "violation_summary": violation_data["summary"]
            })
            
            enriched_listings.append(enriched_listing)
            
            print(f"✅ Added violation data: {violation_data['violations']} violations, {violation_data['risk_level']}")
            
        except Exception as e:
            print(f"❌ Failed to enrich listing with violations: {str(e)}")
            enriched_listings.append(listing)
    
    print(f"\n🎯 Enrichment complete: {len(enriched_listings)} listings processed")
    return enriched_listings


# Test function for standalone usage
def test_violation_checker():
    """Test the violation checker with sample addresses."""
    print("🧪 Testing ViolationCheckerAgent...")
    
    checker = ViolationCheckerAgent()
    
    test_addresses = [
        "456 Hicks Street, Brooklyn Heights, NY",
        "234 East 7th Street, East Village, NY",
        "1234 Grand Concourse, Bronx, NY"
    ]
    
    for address in test_addresses:
        print(f"\n🏠 Testing address: {address}")
        result = checker.forward(address)
        print(f"📊 Result: {result}")
        
        # Parse and display nicely
        data = json.loads(result)
        print(f"   Violations: {data['violations']}")
        print(f"   Risk Level: {data['risk_level']}")
        print(f"   Last Inspection: {data['last_inspection']}")
        print(f"   Summary: {data['summary']}")


if __name__ == "__main__":
    # Run test when script is executed directly
    test_violation_checker() 