import os
import time
import json
import random
import threading
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from smolagents import Tool
# import helium
# from selenium.common.exceptions import NoSuchElementException
# from selenium.webdriver.chrome.options import Options
# Browser automation dependencies commented out for mock demo
# from selenium import webdriver
# from webdriver_manager.chrome import ChromeDriverManager
from functools import lru_cache

# Import our new utilities and mixins
from utils import log_tool_action, current_timestamp
from mixins import TimedObservationMixin
from constants import Borough, VoucherType
from browser_agent_fix import validate_listing_url_for_nyc

# --- 1. Global Browser Management with Optimization ---
driver = None
successful_selectors = {}  # Cache successful selectors

# NYC Borough mapping for Craigslist with optimized listing limits
NYC_BOROUGHS = {
    'bronx': {
        'code': 'brx',
        'limit': 80,  # High density of voucher listings, important area
        'priority': 1
    },
    'brooklyn': {
        'code': 'brk',
        'limit': 80,  # Large, diverse market with many voucher-accepting landlords
        'priority': 2
    },
    'manhattan': {
        'code': 'mnh',
        'limit': 50,  # Expensive but worth checking for HASA/Section 8
        'priority': 4
    },
    'queens': {
        'code': 'que',
        'limit': 70,  # Broad area with frequent FHEPS activity
        'priority': 3
    },
    'staten_island': {
        'code': 'stn',
        'limit': 30,  # Fewer listings, low density
        'priority': 5
    }
}

# # def start_browser(headless=True):
#     """Initializes the Helium browser driver as a global variable."""
#     global driver
#     if driver is None:
#         print("Initializing address-enhanced browser instance...")
#
#         # Setup Chrome options for better performance
#         chrome_options = Options()
#         if headless:
#             chrome_options.add_argument('--headless')
#         chrome_options.add_argument('--no-sandbox')
#         chrome_options.add_argument('--disable-dev-shm-usage')
#         chrome_options.add_argument('--disable-gpu')
#         chrome_options.add_argument('--disable-web-security')
#         chrome_options.add_argument('--disable-features=VizDisplayCompositor')
#
#         # Set up ChromeDriver using webdriver-manager
#         driver_path = ChromeDriverManager().install()
#         driver = webdriver.Chrome(service=webdriver.chrome.service.Service(driver_path), options=chrome_options)
#
#         # Initialize Helium with the driver
#         helium.set_driver(driver)
#
#         # Apply anti-detection measures
#         driver.execute_script("""
#             Object.defineProperty(navigator, 'webdriver', {
#                 get: () => undefined
#             });
#             if (window.chrome) {
#                 window.chrome.runtime = undefined;
#             }
#             const getParameter = WebGLRenderingContext.getParameter;
#             WebGLRenderingContext.prototype.getParameter = function(parameter) {
#                 if (parameter === 37445) return 'Intel Open Source Technology Center';
#                 if (parameter === 37446) return 'Mesa DRI Intel(R) Iris(R) Plus Graphics (ICL GT2)';
#                 return getParameter(parameter);
#             };
#         """)
#
#         print("Browser initialized with enhanced address extraction capabilities.")
#     return driver

# def quit_browser():
#     """Safely quits the global browser instance."""
#     global driver
#     if driver is not None:
#         print("Cleaning up browser resources...")
#         try:
#             helium.kill_browser()
#         except:
#             pass
#         driver = None
#         print("Browser closed.")

def _smart_delay(base_delay=0.5, max_delay=1.5):
    """Intelligent delay with randomization."""
    delay = random.uniform(base_delay, max_delay)
    time.sleep(delay)

# --- 2. Enhanced Address Validation and Normalization ---

def _validate_address(address: str) -> bool:
    """Validate extracted address format with flexible criteria."""
    if not address or address == 'N/A':
        return False
        
    # Should be reasonable length
    is_reasonable_length = 5 <= len(address) <= 100
    
    # Should contain street-like patterns
    street_patterns = [
        r'(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|place|pl|lane|ln)',
        r'(?:east|west|north|south)\s+\d+',  # East 184th, West 42nd, etc.
        r'\d+\w*\s+(?:street|st|avenue|ave)',  # 123rd Street, 42nd Ave
        r'(?:broadway|park\s+ave|grand\s+concourse)',  # Famous NYC streets
        r'near\s+(?:east|west|north|south)',  # "near East 181st"
    ]
    
    has_street_pattern = any(re.search(pattern, address, re.IGNORECASE) for pattern in street_patterns)
    
    # Contains NYC-related terms
    nyc_indicators = ['bronx', 'brooklyn', 'manhattan', 'queens', 'staten island', 'ny', 'new york', 'harlem', 'parkchester', 'wakefield', 'riverdale']
    has_nyc_indicator = any(indicator.lower() in address.lower() for indicator in nyc_indicators)
    
    # Reject clearly bad extractions
    bad_patterns = [
        r'^\$\d+',  # Starts with price
        r'br\s*-\s*\d+ft',  # bedroom/footage info
        r'🏙️.*housing',  # emoji + housing descriptions
    ]
    
    has_bad_pattern = any(re.search(pattern, address, re.IGNORECASE) for pattern in bad_patterns)
    
    return is_reasonable_length and (has_street_pattern or has_nyc_indicator) and not has_bad_pattern

def _normalize_address(address: str, borough_context: str = None) -> str:
    """Standardize address format with optional borough context."""
    if not address or address == 'N/A':
        return address
        
    # Remove extra whitespace
    address = ' '.join(address.split())
    
    # Standardize abbreviations
    replacements = {
        'St.': 'Street',
        'Ave.': 'Avenue', 
        'Blvd.': 'Boulevard',
        'Dr.': 'Drive',
        'Rd.': 'Road',
        'Pl.': 'Place',
        'Ln.': 'Lane',
        'Apt.': 'Apartment',
        ' E ': ' East ',
        ' W ': ' West ',
        ' N ': ' North ',
        ' S ': ' South '
    }
    
    for old, new in replacements.items():
        address = address.replace(old, new)
    
    # Add borough context if missing and we have context
    if borough_context and not any(borough.lower() in address.lower() for borough in ['bronx', 'brooklyn', 'manhattan', 'queens', 'staten']):
        address = f"{address}, {borough_context.title()}"
        
    # Ensure NY state is included if not present
    if 'NY' not in address.upper() and any(borough in address.lower() for borough in ['bronx', 'brooklyn', 'manhattan', 'queens', 'staten']):
        if address.endswith(','):
            address += ' NY'
        else:
            address += ', NY'
        
    return address.strip()

# Address extraction cache for performance
@lru_cache(maxsize=1000)
def _get_cached_address_data(url: str) -> dict:
    """Cache addresses to avoid re-extraction."""
    return _get_detailed_data_with_enhanced_address(url)

# --- 3. Optimized Helper Functions ---

def _go_to_borough_search_page_fast(borough_name):
    """Navigate to borough search page with minimal delays."""
    borough_info = NYC_BOROUGHS.get(borough_name.lower())
    if not borough_info:
        raise ValueError(f"Unknown borough: {borough_name}")
    
    print(f"Fast navigation to {borough_name.title()}...")
    
    # Direct URL with optimized parameters - FORCE LIST MODE
    search_url = f"https://newyork.craigslist.org/search/{borough_info['code']}/apa?format=list"
    print(f"🌐 Navigating to URL: {search_url}")
    log_tool_action("BrowserAgent", "url_navigation", {
        "borough": borough_name,
        "url": search_url,
        "borough_code": borough_info['code']
    })
    helium.go_to(search_url)
    _smart_delay(1, 2)  # Reduced delay
    
    # ENSURE LIST MODE: Force list mode if not already active
    try:
        force_list_script = """
        function forceListMode() {
            // Check if we're in gallery mode and switch to list mode
            let listButton = document.querySelector('.view-list') || 
                           document.querySelector('a[href*="format=list"]') ||
                           document.querySelector('.display-list');
            if (listButton && listButton.style.display !== 'none') {
                listButton.click();
                return 'Switched to list mode';
            }
            
            // Check current URL and force list mode if needed
            if (!window.location.href.includes('format=list')) {
                let newUrl = window.location.href;
                if (newUrl.includes('format=')) {
                    newUrl = newUrl.replace(/format=[^&]*/, 'format=list');
                } else {
                    newUrl += (newUrl.includes('?') ? '&' : '?') + 'format=list';
                }
                window.location.href = newUrl;
                return 'Forced list mode via URL';
            }
            
            return 'Already in list mode';
        }
        return forceListMode();
        """
        result = helium.get_driver().execute_script(force_list_script)
        print(f"📋 List mode: {result}")
        if "Switched" in result or "Forced" in result:
            _smart_delay(2, 3)  # Wait for page reload
    except Exception as e:
        print(f"List mode check failed: {str(e)}")
    
    # Quick price and date filters via JavaScript
    try:
        filter_script = """
        function quickFilters() {
            // Set price range
            let minPrice = document.querySelector('#min_price');
            let maxPrice = document.querySelector('#max_price');
            if (minPrice) { minPrice.value = '1500'; minPrice.dispatchEvent(new Event('change')); }
            if (maxPrice) { maxPrice.value = '4000'; maxPrice.dispatchEvent(new Event('change')); }
            return true;
        }
        return quickFilters();
        """
        helium.get_driver().execute_script(filter_script)
    except Exception as e:
        print(f"Quick filters failed: {str(e)}")
    
    return _find_search_interface_cached()

def _find_search_interface_cached():
    """Find search interface using cached successful selectors first."""
    global successful_selectors
    
    # Try cached selector first
    if 'search_box' in successful_selectors:
        try:
            cached_selector = successful_selectors['search_box']
            element = helium.get_driver().find_element("css selector", cached_selector)
            if element.is_displayed():
                return cached_selector
        except:
            pass  # Cache miss, continue with full search
    
    # Full search with caching - Updated selectors for current Craigslist
    search_selectors = [
        'input[placeholder*="search apartments"]',  # Current Craigslist main search
        'input[placeholder*="search"]',             # Fallback for search inputs
        "#query",                                   # Legacy selector (keep as fallback)
        "input#query", 
        "input[name='query']", 
        "input[type='text']"
    ]
    
    for selector in search_selectors:
        try:
            element = helium.get_driver().find_element("css selector", selector)
            if element.is_displayed():
                successful_selectors['search_box'] = selector  # Cache it
                return selector
        except:
            continue
    
    raise Exception("Could not find search interface")

def _extract_bulk_listing_data_from_search_page(limit=20):
    """Extract listing data directly from search results page with enhanced location detection."""
    print(f"Fast-extracting up to {limit} listings from search results...")
    _smart_delay(1, 1.5)
    
    # Updated JavaScript to handle both gallery mode AND grid mode with posting-title links
    extraction_script = f"""
    function extractListingsData() {{
        let listings = [];
        
        // Try gallery mode first (like our working test)
        let galleryCards = document.querySelectorAll('.gallery-card');
        if (galleryCards.length > 0) {{
            // GALLERY MODE
            Array.from(galleryCards).slice(0, {limit}).forEach(function(element, index) {{
                let data = {{}};
                
                let link = element.querySelector('a.main') ||
                          element.querySelector('a[href*="/apa/d/"]') || 
                          element.querySelector('.gallery-inner a') ||
                          element.querySelector('a');
                
                if (link && link.href && link.href.includes('/apa/d/')) {{
                    data.url = link.href;
                    
                    let titleLink = element.querySelector('a.posting-title') || 
                                   element.querySelector('a[class*="posting-title"]');
                    data.title = titleLink ? titleLink.textContent.trim() : 'No title';
                    
                    let priceEl = element.querySelector('.result-price') || 
                                 element.querySelector('.price') ||
                                 element.querySelector('[class*="price"]');
                    data.price = priceEl ? priceEl.textContent.trim() : 'N/A';
                    
                    let housingEl = element.querySelector('.housing');
                    data.housing_info = housingEl ? housingEl.textContent.trim() : 'N/A';
                    
                    let locationEl = element.querySelector('.result-hood') ||
                                   element.querySelector('.nearby') ||
                                   element.querySelector('[class*="location"]');
                    data.location_hint = locationEl ? locationEl.textContent.trim() : null;
                    
                    listings.push(data);
                }}
            }});
        }} else {{
            // GRID MODE - work with posting-title links directly
            let postingTitles = document.querySelectorAll('a.posting-title');
            Array.from(postingTitles).slice(0, {limit}).forEach(function(titleLink, index) {{
                if (titleLink.href && titleLink.href.includes('/apa/d/')) {{
                    let data = {{}};
                    data.url = titleLink.href;
                    data.title = titleLink.textContent.trim();
                    
                    // Try to find price and other info in the parent container
                    let container = titleLink.closest('.cl-search-result') || 
                                   titleLink.closest('.result') ||
                                   titleLink.closest('[class*="result"]') ||
                                   titleLink.parentElement;
                    
                    if (container) {{
                        let priceEl = container.querySelector('.result-price') || 
                                     container.querySelector('.price') ||
                                     container.querySelector('[class*="price"]');
                        data.price = priceEl ? priceEl.textContent.trim() : 'N/A';
                        
                        let housingEl = container.querySelector('.housing');
                        data.housing_info = housingEl ? housingEl.textContent.trim() : 'N/A';
                        
                        let locationEl = container.querySelector('.result-hood') ||
                                       container.querySelector('.nearby') ||
                                       container.querySelector('[class*="location"]');
                        data.location_hint = locationEl ? locationEl.textContent.trim() : null;
                    }} else {{
                        data.price = 'N/A';
                        data.housing_info = 'N/A';
                        data.location_hint = null;
                    }}
                    
                    listings.push(data);
                }}
            }});
        }}
        
        return listings;
    }}
    return extractListingsData();
    """
    
    try:
        listings_data = helium.get_driver().execute_script(extraction_script)
        print(f"Fast-extracted {len(listings_data)} listings from search page")
        return listings_data
    except Exception as e:
        print(f"Bulk extraction failed: {e}")
        return []

def _get_detailed_data_with_enhanced_address(url):
    """Get description, price, and PROPER ADDRESS from individual listing page with comprehensive extraction."""
    try:
        helium.go_to(url)
        _smart_delay(0.5, 1)
        
        # Comprehensive JavaScript extraction including multiple address strategies
        extraction_script = """
        function extractDetailedData() {
            let result = {};
            let debug = {};
            
            // Get description
            let desc = document.querySelector('#postingbody') || 
                      document.querySelector('.posting-body') || 
                      document.querySelector('.body');
            result.description = desc ? desc.textContent.trim() : 'N/A';
            
            // Get price if not found on search page
            let priceEl = document.querySelector('.price') ||
                         document.querySelector('.postingtitle .price') ||
                         document.querySelector('span.price') ||
                         document.querySelector('[class*="price"]');
            result.price = priceEl ? priceEl.textContent.trim() : 'N/A';
            
            // ENHANCED ADDRESS EXTRACTION - Multiple strategies with debugging
            let address = null;
            debug.attempts = [];
            
            // Strategy 1: Look for map address (most reliable)
            let mapAddress = document.querySelector('.mapaddress') ||
                            document.querySelector('[class*="map-address"]') ||
                            document.querySelector('.postingtitle .mapaddress');
            if (mapAddress && mapAddress.textContent.trim()) {
                address = mapAddress.textContent.trim();
                debug.attempts.push({strategy: 1, found: address, element: 'mapaddress'});
            } else {
                debug.attempts.push({strategy: 1, found: null, searched: '.mapaddress, [class*="map-address"], .postingtitle .mapaddress'});
            }
            
            // Strategy 2: Look in posting title for address in parentheses or after price
            if (!address) {
                let titleEl = document.querySelector('.postingtitle') ||
                             document.querySelector('#titletextonly');
                if (titleEl) {
                    let titleText = titleEl.textContent;
                    debug.titleText = titleText;
                    // Look for patterns like "(East 184, Bronx, NY 10458)" or "- East 184, Bronx"
                    let addressMatch = titleText.match(/[\\(\\$\\-]\\s*([^\\(\\$]+(?:Bronx|Brooklyn|Manhattan|Queens|Staten Island)[^\\)]*)/i);
                    if (addressMatch) {
                        address = addressMatch[1].trim();
                        debug.attempts.push({strategy: 2, found: address, pattern: 'title_parentheses'});
                    } else {
                        debug.attempts.push({strategy: 2, found: null, titleText: titleText});
                    }
                } else {
                    debug.attempts.push({strategy: 2, found: null, element_missing: 'postingtitle'});
                }
            }
            
            // Strategy 3: Look for address in attributes section
            if (!address) {
                let attrGroups = document.querySelectorAll('.attrgroup');
                debug.attrGroups = attrGroups.length;
                for (let group of attrGroups) {
                    let text = group.textContent;
                    if (text.includes('NY') && (text.includes('Bronx') || text.includes('Brooklyn') || 
                        text.includes('Manhattan') || text.includes('Queens') || text.includes('Staten'))) {
                        // Extract address-like text
                        let lines = text.split('\\n').map(line => line.trim()).filter(line => line);
                        for (let line of lines) {
                            if (line.includes('NY') && line.length > 10 && line.length < 100) {
                                address = line;
                                debug.attempts.push({strategy: 3, found: address, source: 'attrgroup'});
                                break;
                            }
                        }
                        if (address) break;
                    }
                }
                if (!address) {
                    debug.attempts.push({strategy: 3, found: null, attrGroups: attrGroups.length});
                }
            }
            
            // Strategy 4: Look in the posting body for address patterns
            if (!address && result.description !== 'N/A') {
                let addressPatterns = [
                    /([0-9]+\\s+[A-Za-z\\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Place|Pl|Lane|Ln)\\s*,?\\s*(?:Bronx|Brooklyn|Manhattan|Queens|Staten Island)\\s*,?\\s*NY\\s*[0-9]{5}?)/gi,
                    /((?:East|West|North|South)?\\s*[0-9]+[A-Za-z]*\\s*(?:Street|St|Avenue|Ave|Road|Rd)\\s*,?\\s*(?:Bronx|Brooklyn|Manhattan|Queens))/gi
                ];
                
                for (let pattern of addressPatterns) {
                    let matches = result.description.match(pattern);
                    if (matches && matches[0]) {
                        address = matches[0].trim();
                        debug.attempts.push({strategy: 4, found: address, pattern: 'description_regex'});
                        break;
                    }
                }
                if (!address) {
                    debug.attempts.push({strategy: 4, found: null, patterns_tried: 2});
                }
            }
            
            result.address = address || 'N/A';
            result.debug = debug;
            
            // Get additional location info
            let locationInfo = document.querySelector('.postingtitle small') ||
                              document.querySelector('.location');
            result.location_info = locationInfo ? locationInfo.textContent.trim() : null;
            
            return result;
        }
        return extractDetailedData();
        """
        
        result = helium.get_driver().execute_script(extraction_script)
        
        # Log debug information
        if result.get('debug'):
            print(f"🔍 DEBUG for {url}:")
            print(f"   Title text: {result['debug'].get('titleText', 'N/A')}")
            print(f"   AttrGroups found: {result['debug'].get('attrGroups', 0)}")
            for attempt in result['debug'].get('attempts', []):
                print(f"   Strategy {attempt['strategy']}: {attempt}")
        
        # Post-process and validate the address
        if result.get('address') and result['address'] != 'N/A':
            # Normalize the address (we'll pass borough context from the processing function)
            result['address'] = _normalize_address(result['address'])
            
            # Validate the address
            if not _validate_address(result['address']):
                print(f"❌ Address validation failed: {result['address']}")
                result['address'] = 'N/A'
            else:
                print(f"✅ Address validated: {result['address']}")
                
        return result
    except Exception as e:
        print(f"Enhanced extraction failed for {url}: {e}")
        return {"description": "N/A", "price": "N/A", "address": "N/A", "location_info": None}

# --- Enhanced Voucher Validation System ---

class VoucherListingValidator:
    """Advanced validator for determining if listings are truly voucher-friendly."""
    
    def __init__(self):
        # Strong positive patterns that indicate voucher acceptance
        self.positive_patterns = [
            r"(?i)(section[- ]?8|vouchers?|programs?|cityfheps|fheps|hasa|hpd|dss).{0,30}(welcome|accepted|ok|approval?)",
            r"(?i)(accept(s|ing)|taking).{0,30}(section[- ]?8|vouchers?|programs?|cityfheps|fheps|hasa|hpd|dss)",
            r"(?i)all.{0,10}(programs|vouchers).{0,10}(welcome|accepted)",
            r"(?i)(section[- ]?8|vouchers?|programs?|cityfheps|fheps|hasa|hpd|dss).{0,15}(tenant|client)s?.{0,15}(welcome|accepted)",
            r"(?i)(hasa|section[- ]?8|cityfheps|fheps|hpd|dss).{0,20}(are|is).{0,20}(welcome|accepted)",
            r"(?i)(section[- ]?8|vouchers?|hasa|cityfheps|fheps|hpd|dss).{0,15}(ok|okay)",
            # Inclusive patterns for all voucher types - "apartment for [voucher]" style
            r"(?i)apartment.{0,10}(for|with).{0,10}(hasa|section[- ]?8|cityfheps|fheps|hpd|dss)",
            r"(?i)(hasa|section[- ]?8|cityfheps|fheps|hpd|dss).{0,20}(apartment|listing|unit|studio|bedroom)",
            r"(?i)(landlord|owner).{0,30}(works?|deals?).{0,30}(with\s+)?(hasa|section[- ]?8|cityfheps|fheps|hpd|dss)",
            r"(?i)for\s+(hasa|section[- ]?8|cityfheps|fheps|hpd|dss)\s+(clients?|tenants?|vouchers?)",
            r"(?i)(takes?|accepting).{0,10}(hasa|section[- ]?8|cityfheps|fheps|hpd|dss)",
        ]
        
        # Negative patterns that indicate voucher rejection
        self.negative_patterns = [
            r"(?i)no.{0,10}(section[- ]?8|vouchers?|programs?)",
            r"(?i)(cash|private pay).{0,10}only",
            r"(?i)not.{0,10}(accepting|taking).{0,10}(section[- ]?8|vouchers?|programs?)",
            r"(?i)(section[- ]?8|vouchers?|programs?).{0,15}not.{0,15}(accepted|welcome)",
            r"(?i)owner.{0,15}(pay|cash).{0,10}only",
        ]
        
        # Context-dependent terms that need additional validation
        self.context_terms = {
            "income restricted": ["voucher", "section 8", "program", "subsidy", "assistance"],
            "low income": ["voucher", "section 8", "program", "subsidy", "assistance"],
            "affordable": ["voucher", "section 8", "program", "subsidy", "assistance"]
        }
        
        # Keywords that strongly indicate voucher acceptance
        self.strong_indicators = [
            "all section 8 welcome",
            "all section-8 welcome",
            "all vouchers accepted",
            "all other vouchers accepted", 
            "all programs welcome",
            "cityfheps ok",
            "cityfheps accepted",
            "hasa approved",
            "hasa welcome",
            "hasa accepted",
            "section 8 tenants welcome",
            "section-8 welcome",
            "voucher programs accepted",
            "all programs accepted",
            "section 8 welcome",
            "section 8 accepted",
            "vouchers are accepted",
            "vouchers are welcome",
            "vouchers welcome",
            "housing vouchers welcome",
            # Inclusive strong indicators for all voucher types
            "apartment for hasa",
            "apartment for section 8",
            "apartment for section-8",
            "apartment for cityfheps",
            "apartment for fheps",
            "apartment for hpd",
            "apartment for dss",
            "for hasa",
            "for section 8",
            "for section-8",
            "for cityfheps",
            "for fheps",
            "for hpd",
            "for dss",
            "hasa apartment",
            "section 8 apartment",
            "section-8 apartment",
            "cityfheps apartment",
            "fheps apartment",
            "hpd apartment",
            "dss apartment",
            "hasa voucher",
            "section 8 voucher",
            "cityfheps voucher",
            "fheps voucher",
            "hpd voucher",
            "dss voucher",
            "works with hasa",
            "works with section 8",
            "works with cityfheps",
            "works with fheps",
            "works with hpd",
            "works with dss",
            "takes hasa",
            "takes section 8",
            "takes cityfheps",
            "takes fheps",
            "takes hpd",
            "takes dss",
            "studio for hasa",
            "studio for section 8",
            "studio for cityfheps",
            "studio for fheps",
            "studio for hpd",
            "studio for dss",
            "bedroom for hasa",
            "bedroom for section 8",
            "bedroom for cityfheps",
            "bedroom for fheps",
            "bedroom for hpd",
            "bedroom for dss",
            "hasa clients",
            "section 8 clients",
            "cityfheps clients",
            "fheps clients",
            "hpd clients",
            "dss clients",
            "hasa tenants",
            "section 8 tenants",
            "cityfheps tenants",
            "fheps tenants",
            "hpd tenants",
            "dss tenants"
        ]

    def _check_patterns(self, text, patterns):
        """Check if any pattern matches in the text"""
        return any(re.search(pattern, text) for pattern in patterns)

    def _calculate_confidence(self, text):
        """Calculate confidence score based on various factors"""
        score = 0.0
        
        # Check for strong positive indicators (highest weight)
        strong_found = [indicator for indicator in self.strong_indicators if indicator in text.lower()]
        if strong_found:
            score += 0.7
            
        # Check for positive patterns - increased weight
        if self._check_patterns(text, self.positive_patterns):
            score += 0.4
            
        # Voucher-specific boost: if any voucher type is mentioned in title/description, give additional confidence
        voucher_keywords = ["hasa", "section 8", "section-8", "cityfheps", "fheps", "hpd", "dss"]
        if any(keyword in text.lower() for keyword in voucher_keywords):
            score += 0.2  # Additional boost for voucher type mentions
            
        # Check for negative patterns (can override positive scores)
        if self._check_patterns(text, self.negative_patterns):
            score -= 0.9
            
        # Context validation for ambiguous terms
        for term, required_context in self.context_terms.items():
            if term in text.lower():
                if not any(context in text.lower() for context in required_context):
                    score -= 0.3
                    
        return max(0.0, min(1.0, score))  # Clamp between 0 and 1

    def validate_listing(self, title, description):
        """
        Validate if a listing is truly voucher-friendly
        Returns: (is_voucher_friendly, found_keywords, validation_details)
        """
        text = f"{title} {description}".lower()
        confidence_score = self._calculate_confidence(text)
        
        # Extract found keywords for reference
        found_keywords = []
        
        # Extract positive pattern matches
        for pattern in self.positive_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            found_keywords.extend(match.group(0) for match in matches)
            
        # Add strong indicators found
        found_keywords.extend(
            indicator for indicator in self.strong_indicators 
            if indicator in text.lower()
        )
        
        # Check for negative patterns
        negative_found = []
        for pattern in self.negative_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            negative_found.extend(match.group(0) for match in matches)
        
        validation_details = {
            "confidence_score": confidence_score,
            "has_negative_patterns": bool(negative_found),
            "negative_patterns_found": negative_found,
            "has_positive_patterns": self._check_patterns(text, self.positive_patterns),
            "found_keywords": list(set(found_keywords)),  # Deduplicate
            "validation_reason": self._get_validation_reason(confidence_score, negative_found, found_keywords)
        }
        
        # Consider listing voucher-friendly if confidence score exceeds threshold
        # Use lower threshold for any voucher type listings to be more inclusive
        voucher_keywords = ["hasa", "section 8", "section-8", "cityfheps", "fheps", "hpd", "dss"]
        has_voucher_mention = any(keyword in text.lower() for keyword in voucher_keywords)
        threshold = 0.4 if has_voucher_mention else 0.5
        return confidence_score >= threshold, found_keywords, validation_details
    
    def _get_validation_reason(self, score, negative_patterns, positive_keywords):
        """Provide human-readable reason for validation decision"""
        if score >= 0.5:
            if positive_keywords:
                return f"Strong voucher indicators found: {', '.join(positive_keywords[:2])}"
            else:
                return "Voucher-friendly patterns detected"
        else:
            if negative_patterns:
                return f"Rejected due to negative patterns: {', '.join(negative_patterns[:2])}"
            else:
                return "Insufficient voucher-friendly indicators"

def _process_listings_batch_with_addresses(listings_batch, borough, voucher_keywords):
    """Process a batch of listings with enhanced address extraction and validation."""
    voucher_listings = []
    validator = VoucherListingValidator()
    
    # FIRST: Filter out non-NYC listings by URL validation
    print(f"🔍 Validating {len(listings_batch)} URLs for {borough}...")
    valid_listings = []
    skipped_count = 0
    
    for listing in listings_batch:
        url_validation = validate_listing_url_for_nyc(listing['url'], borough)
        
        if url_validation['should_skip']:
            skipped_count += 1
            print(f"⚠️ SKIPPED: {url_validation['reason']} - {listing['url']}")
            continue
        
        if not url_validation['is_valid']:
            skipped_count += 1
            print(f"❌ INVALID: {url_validation['reason']} - {listing['url']}")
            continue
            
        valid_listings.append(listing)
    
    print(f"✅ {len(valid_listings)} valid URLs, {skipped_count} filtered out")
    
    if not valid_listings:
        print(f"No valid listings found for {borough} after URL validation")
        return voucher_listings
    
    with ThreadPoolExecutor(max_workers=3) as executor:  # Limit concurrent requests
        # Submit enhanced extraction tasks for VALID listings only
        future_to_listing = {
            executor.submit(_get_detailed_data_with_enhanced_address, listing['url']): listing 
            for listing in valid_listings  # Use filtered list
        }
        
        for future in as_completed(future_to_listing):
            listing = future_to_listing[future]
            try:
                result = future.result(timeout=15)  # Increased timeout for address extraction
                
                # Update listing with detailed data
                listing['description'] = result['description']
                listing['borough'] = borough
                
                # Update price if better one found
                if listing.get('price') == 'N/A' and result['price'] != 'N/A':
                    listing['price'] = result['price']
                
                # Add the properly extracted address with borough context
                if result['address'] != 'N/A':
                    listing['address'] = _normalize_address(result['address'], borough)
                else:
                    listing['address'] = result['address']
                
                # Add location info if available
                if result.get('location_info'):
                    listing['location_info'] = result['location_info']
                
                # Enhance address with location hint from search results if needed
                if listing['address'] == 'N/A' and listing.get('location_hint'):
                    potential_address = f"{listing['location_hint']}, {borough.title()}, NY"
                    if _validate_address(potential_address):
                        listing['address'] = _normalize_address(potential_address, borough)
                
                # Use the enhanced validator for voucher detection
                is_voucher_friendly, found_keywords, validation_details = validator.validate_listing(
                    listing.get('title', ''),
                    result['description']
                )
                
                if is_voucher_friendly:
                    listing['voucher_keywords_found'] = found_keywords
                    listing['validation_details'] = validation_details
                    voucher_listings.append(listing)
                    print(f"✓ VOUCHER-FRIENDLY ({validation_details['confidence_score']:.2f}): {listing.get('title', 'N/A')[:50]}...")
                    print(f"  📍 Address: {listing.get('address', 'N/A')}")
                else:
                    print(f"✗ REJECTED ({validation_details['confidence_score']:.2f}): {listing.get('title', 'N/A')[:50]} - {validation_details['validation_reason']}")
                
            except Exception as e:
                print(f"Error processing listing: {e}")
                continue
    
    return voucher_listings

def _search_borough_for_vouchers_fast(borough_name, query):
    """Optimized borough search with bulk extraction and parallel processing."""
    print(f"\n🚀 FAST SEARCH: {borough_name.upper()}")
    
    borough_listings = []
    borough_info = NYC_BOROUGHS[borough_name.lower()]
    limit_per_borough = borough_info['limit']
    
    try:
        # Navigate to borough search
        search_selector = _go_to_borough_search_page_fast(borough_name)
        
        # Quick search
        print(f"Executing search for {borough_name}...")
        search_input = helium.S(search_selector)
        helium.click(search_input)
        _smart_delay(0.3, 0.7)
        helium.write(query, into=search_input)
        _smart_delay(0.3, 0.7)
        helium.press(helium.ENTER)
        
        _smart_delay(1.5, 2.5)  # Wait for results
        
        # FAST: Extract all listing data from search page at once
        listings_data = _extract_bulk_listing_data_from_search_page(limit_per_borough)
        
        if not listings_data:
            print(f"No listings found in {borough_name}")
            return borough_listings
        
        print(f"Processing {len(listings_data)} listings from {borough_name} (limit: {limit_per_borough})...")
        
        # Voucher keywords (same comprehensive list)
        voucher_keywords = [
            "SECTION 8", "SECTION-8", "Section 8", "Section-8",
            "ALL SECTION 8", "ALL SECTION-8", "SECTION 8 WELCOME", "SECTION-8 WELCOME",
            "sec 8", "sec-8", "s8", "section8", "OFF THE BOOK JOBS WELCOME",
            "BAD/FAIR CREDIT WILL BE CONSIDERED", "NEW RENTALS/TRANSFERS/PORTABILITY",
            "HASA", "hasa", "HASA OK", "hasa ok", "HASA ACCEPTED", "hasa accepted", "ALL HASA",
            "HPD", "hpd", "HPD VOUCHER", "hpd voucher", "HPD SECTION 8", "hpd section 8", "ALL HPD",
            "CMI", "cmi", "COMMUNITY MENTAL ILLNESS", "community mental illness", "CMI PROGRAM",
            "NYCHA", "nycha", "NYC HOUSING", "nyc housing", "ALL NYCHA",
            "DSS", "dss", "DSS ACCEPTED", "dss accepted", "DSS WELCOME", "dss welcome", "ALL DSS",
            "VOUCHER ACCEPTED", "voucher accepted", "VOUCHERS OK", "vouchers ok",
            "VOUCHERS WELCOME", "vouchers welcome", "ACCEPTS VOUCHERS", "accepts vouchers",
            "VOUCHER PROGRAMS ACCEPTED", "ALL VOUCHERS", "ALL PROGRAMS",
            "PROGRAM OK", "program ok", "PROGRAM ACCEPTED", "program accepted",
            "PROGRAMS WELCOME", "programs welcome", "ACCEPTS PROGRAMS", "accepts programs",
            "RENTAL ASSISTANCE ACCEPTED", "ALL PROGRAMS WELCOME",
            "SUPPORTIVE HOUSING", "supportive housing", "INCOME-BASED", "income-based",
            "LOW-INCOME HOUSING", "low-income housing", "AFFORDABLE HOUSING", "affordable housing",
            "AFFORDABLE APARTMENT", "affordable apartment", "LOW INCOME", "low income",
            "INCOME RESTRICTED", "income restricted",
            "CITYFHEPS", "CityFHEPS", "FHEPS", "fheps"  # Added FHEPS variations
        ]
        
        # Process listings in smaller batches with address extraction
        batch_size = 4  # Slightly smaller batches due to address extraction overhead
        for i in range(0, len(listings_data), batch_size):
            batch = listings_data[i:i + batch_size]
            batch_results = _process_listings_batch_with_addresses(batch, borough_name, voucher_keywords)
            borough_listings.extend(batch_results)
            
            # Small delay between batches
            if i + batch_size < len(listings_data):
                _smart_delay(0.5, 1)
        
        print(f"✅ {borough_name.upper()}: {len(borough_listings)} voucher listings found")
        
    except Exception as e:
        print(f"❌ Error in {borough_name}: {str(e)}")
    
    return borough_listings

# --- 3. Ultra-Fast Browser Agent Tool ---

class BrowserAgent(TimedObservationMixin, Tool):
    """
    smolagents Tool for ultra-fast voucher listing collection across NYC boroughs.
    Uses bulk extraction and parallel processing for maximum speed.
    """
    
    name = "browser_agent"
    description = (
        "Search for voucher-friendly apartment listings across NYC boroughs. "
        "Returns structured listing data with addresses, prices, and voucher acceptance indicators."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "Search keywords for voucher-friendly listings (e.g., 'Section 8', 'CityFHEPS')",
            "nullable": True
        },
        "boroughs": {
            "type": "string", 
            "description": "Comma-separated list of NYC boroughs to search (bronx,brooklyn,manhattan,queens,staten_island). Default: all boroughs",
            "nullable": True
        }
    }
    output_type = "string"  # JSON-formatted string
    
    def __init__(self):
        super().__init__()
        print("🚀 BrowserAgent initialized with ultra-fast search capabilities")
    
    def forward(self, query: str = "Section 8", 
                boroughs: str = "") -> str:
        """
        Main tool function: Search for voucher listings.
        Returns JSON-formatted string with listing data.
        """
        with self.timed_observation() as timer:
            log_tool_action("BrowserAgent", "mock_search_started", {
                "query": query,
                "boroughs_requested": boroughs,
                "timestamp": current_timestamp()
            })

            try:
                # Mock listings for demonstration
                mock_listings = [
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
                        "accepts_vouchers": True,
                        "description": "Spacious 2BR apartment in safe building, accepts Section 8 vouchers",
                        "contact": "landlord@example.com"
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
                        "accepts_vouchers": True,
                        "description": "3BR apartment with parking, moderate risk building",
                        "contact": "queenslandlord@example.com"
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
                        "accepts_vouchers": False,
                        "description": "Luxury 1BR in Manhattan, does not accept vouchers",
                        "contact": "manhattanlandlord@example.com"
                    }
                ]

                # Filter based on query and boroughs for realism
                filtered_listings = []
                query_lower = query.lower()

                for listing in mock_listings:
                    # Filter by bedrooms if specified
                    if "studio" in query_lower and listing["bedrooms"] != 0:
                        continue
                    if "1 bedroom" in query_lower and listing["bedrooms"] != 1:
                        continue
                    if "2 bedroom" in query_lower and listing["bedrooms"] != 2:
                        continue
                    if "3 bedroom" in query_lower and listing["bedrooms"] != 3:
                        continue

                    # Filter by borough if specified
                    if boroughs:
                        borough_list = [b.strip().lower() for b in boroughs.split(",")]
                        if listing["borough"].lower() not in borough_list:
                            continue

                    # Filter by voucher acceptance if mentioned
                    if "voucher" in query_lower and not listing["accepts_vouchers"]:
                        continue

                    filtered_listings.append(listing)

                # If no specific filters, return first 2 listings
                if not filtered_listings:
                    filtered_listings = mock_listings[:2]

                log_tool_action("BrowserAgent", "mock_search_complete", {
                    "listings_found": len(filtered_listings),
                    "query": query
                })

                return json.dumps(timer.success({
                    "message": f"Mock search complete: Found {len(filtered_listings)} voucher-friendly listings",
                    "listings": filtered_listings
                }))

            except Exception as e:
                return json.dumps(timer.error(
                    f"Mock search failed: {str(e)}",
                    {"error_type": type(e).__name__}
                ))

# --- 4. Convenience Functions and Testing ---

def collect_voucher_listings_ultra_fast(
    query: str = "Section 8",
    boroughs: list = None
) -> list:
    """
    Backward compatibility function that uses the new BrowserAgent with mock data.
    Returns list of listings (unwrapped from observation format).
    """
    agent = BrowserAgent()
    boroughs_str = ",".join(boroughs) if boroughs else ""

    result_json = agent.forward(query=query, boroughs=boroughs_str)
    result = json.loads(result_json)

    if result.get("status") == "success":
        return result["data"]["listings"]
    else:
        print(f"Mock search failed: {result.get('error', 'Unknown error')}")
        return []

def save_to_json_fast(data, filename="ultra_fast_voucher_listings.json"):
    """Save with performance metrics."""
    organized_data = {
        "performance_metrics": {
            "total_listings": len(data),
            "search_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "boroughs_found": list(set([listing.get('borough', 'unknown') for listing in data])),
            "extraction_method": "ultra_fast_bulk_extraction"
        },
        "listings_by_borough": {},
        "all_listings": data
    }
    
    for listing in data:
        borough = listing.get('borough', 'unknown')
        if borough not in organized_data["listings_by_borough"]:
            organized_data["listings_by_borough"][borough] = []
        organized_data["listings_by_borough"][borough].append(listing)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(organized_data, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved {len(data)} listings to {filename}")

def save_to_json_with_address_metrics(data, filename="address_enhanced_voucher_listings.json"):
    """Save listings data with comprehensive address extraction metrics."""
    addresses_found = sum(1 for listing in data if listing.get('address') and listing['address'] != 'N/A')
    addresses_validated = sum(1 for listing in data if listing.get('address') and listing['address'] != 'N/A' and _validate_address(listing['address']))
    
    organized_data = {
        "extraction_metrics": {
            "total_listings": len(data),
            "addresses_extracted": addresses_found,
            "addresses_validated": addresses_validated,
            "address_success_rate": f"{addresses_found/len(data)*100:.1f}%" if data else "0%",
            "address_validation_rate": f"{addresses_validated/addresses_found*100:.1f}%" if addresses_found else "0%",
            "search_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "extraction_method": "enhanced_address_extraction_v2"
        },
        "listings_by_borough": {},
        "all_listings": data
    }
    
    # Group by borough with address stats
    for listing in data:
        borough = listing.get('borough', 'unknown')
        if borough not in organized_data["listings_by_borough"]:
            organized_data["listings_by_borough"][borough] = []
        organized_data["listings_by_borough"][borough].append(listing)
    
    # Add per-borough address stats
    borough_stats = {}
    for borough, listings in organized_data["listings_by_borough"].items():
        borough_addresses = sum(1 for listing in listings if listing.get('address') and listing['address'] != 'N/A')
        borough_stats[borough] = {
            "total_listings": len(listings),
            "addresses_found": borough_addresses,
            "address_rate": f"{borough_addresses/len(listings)*100:.1f}%" if listings else "0%"
        }
    organized_data["extraction_metrics"]["borough_breakdown"] = borough_stats
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(organized_data, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved {len(data)} listings with {addresses_found} addresses to {filename}")
    print(f"📊 Address extraction rate: {addresses_found/len(data)*100:.1f}%")

def collect_voucher_listings_with_addresses(
    query: str = "Section 8", 
    limit_per_borough: int = 12,
    boroughs: list = None
) -> list:
    """
    Enhanced voucher listing collection with proper address extraction.
    Extracts real addresses from Craigslist listings instead of using titles.
    
    Args:
        query (str): Search keywords
        limit_per_borough (int): Max listings per borough (default: 12)
        boroughs (list): Boroughs to search (default: all 5)
    """
    if boroughs is None:
        boroughs = list(NYC_BOROUGHS.keys())
    
    all_listings = []
    start_time = time.time()
    
    try:
        print("\n🏠 ADDRESS-ENHANCED NYC VOUCHER SEARCH")
        print("=" * 55)
        print(f"Target boroughs: {', '.join([b.title() for b in boroughs])}")
        print(f"Limit per borough: {limit_per_borough}")
        print(f"Search query: {query}")
        print("🔍 Enhanced with proper address extraction")
        print("=" * 55)
        
        start_browser()
        
        for borough in boroughs:
            if borough.lower() not in NYC_BOROUGHS:
                continue
                
            borough_start = time.time()
            # Override the limit temporarily for this test
            original_limit = NYC_BOROUGHS[borough.lower()]['limit']
            NYC_BOROUGHS[borough.lower()]['limit'] = limit_per_borough
            
            borough_listings = _search_borough_for_vouchers_fast(borough, query)
            borough_time = time.time() - borough_start
            
            # Restore original limit
            NYC_BOROUGHS[borough.lower()]['limit'] = original_limit
            
            all_listings.extend(borough_listings)
            print(f"⏱️  {borough.title()} completed in {borough_time:.1f}s")
            
            if borough != boroughs[-1]:
                _smart_delay(1, 2)
        
        total_time = time.time() - start_time
        
        # Enhanced summary with address statistics
        print("\n🎯 ADDRESS-ENHANCED SEARCH COMPLETE!")
        print("=" * 55)
        borough_counts = {}
        addresses_found = 0
        
        for listing in all_listings:
            borough = listing.get('borough', 'unknown')
            borough_counts[borough] = borough_counts.get(borough, 0) + 1
            if listing.get('address') and listing['address'] != 'N/A':
                addresses_found += 1
        
        for borough, count in borough_counts.items():
            print(f"{borough.title()}: {count} voucher listings")
        
        print(f"\n📊 TOTAL: {len(all_listings)} voucher listings")
        print(f"📍 ADDRESSES FOUND: {addresses_found}/{len(all_listings)} ({addresses_found/len(all_listings)*100:.1f}%)")
        print(f"⚡ TOTAL TIME: {total_time:.1f} seconds")
        print("=" * 55)
        
        return all_listings

    except Exception as e:
        print(f"❌ Address-enhanced search error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        quit_browser()

def test_address_enhanced_browser_agent():
    """Test the enhanced address extraction functionality."""
    print("🧪 TESTING ADDRESS-ENHANCED BROWSER AGENT")
    print("=" * 50)
    
    start_time = time.time()
    # Test with multiple boroughs and more listings
    listings = collect_voucher_listings_with_addresses(
        limit_per_borough=15, 
        boroughs=['bronx', 'brooklyn']
    )
    total_time = time.time() - start_time
    
    if listings:
        save_to_json_with_address_metrics(listings)
        addresses_found = sum(1 for listing in listings if listing.get('address') and listing['address'] != 'N/A')
        
        print(f"\n🎯 COMPREHENSIVE TEST RESULTS:")
        print(f"Found {len(listings)} listings with {addresses_found} proper addresses!")
        print(f"Address extraction rate: {addresses_found/len(listings)*100:.1f}%")
        print(f"⚡ Completed in {total_time:.1f} seconds")
        print(f"⚡ Rate: {len(listings)/total_time:.1f} listings/second")
        
        # Display some sample addresses from different boroughs
        print(f"\n📍 SAMPLE ADDRESSES BY BOROUGH:")
        borough_samples = {}
        for listing in listings:
            borough = listing.get('borough', 'unknown')
            if borough not in borough_samples:
                borough_samples[borough] = []
            if listing.get('address') and listing['address'] != 'N/A':
                borough_samples[borough].append(listing)
        
        for borough, borough_listings in borough_samples.items():
            print(f"\n  🏠 {borough.upper()}:")
            for i, listing in enumerate(borough_listings[:2]):  # Show 2 per borough
                print(f"     {i+1}. {listing['title'][:40]}...")
                print(f"        📍 {listing['address']}")
                print(f"        💰 {listing['price']}")
                
        # Performance summary
        print(f"\n📊 PERFORMANCE BREAKDOWN:")
        borough_counts = {}
        borough_addresses = {}
        for listing in listings:
            borough = listing.get('borough', 'unknown')
            borough_counts[borough] = borough_counts.get(borough, 0) + 1
            if listing.get('address') and listing['address'] != 'N/A':
                borough_addresses[borough] = borough_addresses.get(borough, 0) + 1
        
        for borough in borough_counts:
            addr_count = borough_addresses.get(borough, 0)
            total_count = borough_counts[borough]
            print(f"   {borough.title()}: {addr_count}/{total_count} addresses ({addr_count/total_count*100:.1f}%)")
            
    else:
        print("❌ No listings found.")

if __name__ == '__main__':
    print("🏠 ADDRESS-ENHANCED VOUCHER SCRAPER TEST")
    
    # Run the enhanced address extraction test
    test_address_enhanced_browser_agent() 