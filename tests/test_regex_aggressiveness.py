#!/usr/bin/env python3
"""
Comprehensive tests for regex aggressiveness in VoucherBot

This test suite is designed to challenge the regex patterns used throughout
the VoucherBot application to identify overly aggressive matching behavior
that could lead to false positives and incorrect intent classification.
"""

import unittest
import sys
import os

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_semantic_router_v2 import EnhancedSemanticRouterV2, Intent
from semantic_router import EnhancedSemanticRouter, classify_intent
from email_handler import enhanced_classify_message
from what_if_handler import WhatIfScenarioAnalyzer


class TestRegexAggressiveness(unittest.TestCase):
    """Test suite to identify overly aggressive regex patterns"""
    
    def setUp(self):
        """Set up test components"""
        self.router_v2 = EnhancedSemanticRouterV2()
        self.router_v1 = EnhancedSemanticRouter()
        self.what_if_analyzer = WhatIfScenarioAnalyzer()
        
        # Test state with listings for context
        self.state_with_listings = {
            "listings": [
                {
                    "address": "1234 Grand Concourse, Bronx, NY 10457",
                    "price": "$2,000",
                    "url": "https://test.com/listing1",
                    "risk_level": "✅",
                    "building_violations": 0,
                    "title": "Nice Bronx Apartment"
                }
            ]
        }
        
        self.empty_state = {}

    def test_informational_vs_search_intent(self):
        """Test that informational questions don't trigger search intent"""
        
        # These should NOT be classified as SEARCH_LISTINGS
        informational_queries = [
            "What is a housing listing?",
            "How do apartment listings work?",
            "Tell me about finding apartments",
            "What does it mean to search for housing?",
            "Explain the apartment search process",
            "What are the benefits of looking for apartments?",
            "Why would someone browse listings?",
            "What is the definition of housing search?",
            "How does apartment hunting work in NYC?",
            "What should I know about finding places to live?",
            "Can you explain what apartment browsing means?",
            "What are the steps in looking for housing?",
            "Tell me about the apartment finding process",
            "What does housing search involve?",
            "How do people typically find apartments?"
        ]
        
        print("\n🔍 Testing Informational vs Search Intent Classification")
        print("=" * 60)
        
        for query in informational_queries:
            with self.subTest(query=query):
                intent_v2 = self.router_v2.classify_intent(query)
                intent_v1 = classify_intent(query)
                
                print(f"Query: '{query}'")
                print(f"  V2 Intent: {intent_v2}")
                print(f"  V1 Intent: {intent_v1}")
                
                # These should be classified as VOUCHER_INFO, SHOW_HELP, or UNCLASSIFIED
                # NOT as SEARCH_LISTINGS
                self.assertNotEqual(intent_v2, Intent.SEARCH_LISTINGS, 
                                  f"V2 incorrectly classified informational query as SEARCH_LISTINGS: '{query}'")
                self.assertNotEqual(intent_v1.value if hasattr(intent_v1, 'value') else str(intent_v1), 
                                  "search_listings",
                                  f"V1 incorrectly classified informational query as search_listings: '{query}'")
                print("  ✅ Correctly NOT classified as search intent")
                print()

    def test_borough_mention_vs_what_if_intent(self):
        """Test that casual borough mentions don't trigger what-if intent"""
        
        # These should NOT be classified as WHAT_IF intent
        casual_borough_mentions = [
            "I live in Brooklyn",
            "Brooklyn is a nice place",
            "My friend is from Queens",
            "Manhattan has tall buildings",
            "The Bronx is part of NYC",
            "Staten Island is an island",
            "I work in Manhattan",
            "Brooklyn pizza is the best",
            "Queens has many neighborhoods",
            "The Bronx Zoo is famous",
            "I grew up in Staten Island",
            "Brooklyn Bridge is iconic",
            "Manhattan is expensive",
            "Queens is diverse",
            "The Bronx has good food",
            "Staten Island ferry is free",
            "I visited Brooklyn yesterday",
            "Manhattan traffic is bad",
            "Queens has two airports",
            "The Bronx is north of Manhattan"
        ]
        
        print("\n🏙️ Testing Borough Mention vs What-If Intent Classification")
        print("=" * 60)
        
        for query in casual_borough_mentions:
            with self.subTest(query=query):
                intent_v2 = self.router_v2.classify_intent(query)
                what_if_detected, _ = self.what_if_analyzer.detect_what_if_scenario(query, {})
                
                print(f"Query: '{query}'")
                print(f"  V2 Intent: {intent_v2}")
                print(f"  What-If Detected: {what_if_detected}")
                
                # These should NOT be classified as WHAT_IF
                self.assertNotEqual(intent_v2, Intent.WHAT_IF,
                                  f"V2 incorrectly classified casual borough mention as WHAT_IF: '{query}'")
                self.assertFalse(what_if_detected,
                               f"What-if analyzer incorrectly detected scenario in: '{query}'")
                print("  ✅ Correctly NOT classified as what-if intent")
                print()

    def test_voucher_mention_vs_voucher_info_intent(self):
        """Test that casual voucher mentions don't always trigger voucher info intent"""
        
        # These should NOT necessarily be classified as VOUCHER_INFO
        casual_voucher_mentions = [
            "I have a Section 8 voucher",
            "My voucher expires next month",
            "The landlord accepted my CityFHEPS",
            "I'm using HASA assistance",
            "My Section 8 is approved",
            "The voucher amount is $1500",
            "I received my housing voucher",
            "My CityFHEPS application was approved",
            "The HASA voucher covers rent",
            "I qualified for Section 8",
            "My housing assistance starts Monday",
            "The voucher payment is processed",
            "I'm a voucher holder",
            "My Section 8 caseworker called",
            "The CityFHEPS office is closed"
        ]
        
        # These SHOULD be classified as VOUCHER_INFO
        voucher_info_requests = [
            "What is Section 8?",
            "How does CityFHEPS work?",
            "Tell me about HASA vouchers",
            "Explain housing vouchers",
            "What are the requirements for Section 8?",
            "How do I apply for CityFHEPS?",
            "What is the difference between Section 8 and HASA?",
            "Can you explain voucher programs?",
            "What voucher types are available?",
            "How do housing vouchers work?"
        ]
        
        print("\n🎫 Testing Voucher Mention vs Voucher Info Intent Classification")
        print("=" * 60)
        
        print("CASUAL MENTIONS (should NOT always be VOUCHER_INFO):")
        for query in casual_voucher_mentions:
            with self.subTest(query=query):
                intent_v2 = self.router_v2.classify_intent(query)
                
                print(f"Query: '{query}'")
                print(f"  V2 Intent: {intent_v2}")
                
                # These could be various intents, but shouldn't automatically be VOUCHER_INFO
                # This is more of a warning than a hard failure
                if intent_v2 == Intent.VOUCHER_INFO:
                    print(f"  ⚠️  WARNING: Casual mention classified as VOUCHER_INFO")
                else:
                    print("  ✅ Not automatically classified as VOUCHER_INFO")
                print()
        
        print("INFORMATION REQUESTS (SHOULD be VOUCHER_INFO):")
        for query in voucher_info_requests:
            with self.subTest(query=query):
                intent_v2 = self.router_v2.classify_intent(query)
                
                print(f"Query: '{query}'")
                print(f"  V2 Intent: {intent_v2}")
                
                # These SHOULD be classified as VOUCHER_INFO
                self.assertEqual(intent_v2, Intent.VOUCHER_INFO,
                               f"V2 failed to classify voucher info request: '{query}'")
                print("  ✅ Correctly classified as VOUCHER_INFO")
                print()

    def test_number_extraction_precision(self):
        """Test that number extraction doesn't over-extract from context"""
        
        # Test cases where numbers should NOT be extracted as bedrooms/rent
        ambiguous_number_queries = [
            "I live at 123 Main Street",  # Address number
            "Call me at 555-1234",  # Phone number
            "My apartment is in building 5",  # Building number
            "I work 8 hours a day",  # Work hours
            "I have 3 kids",  # Family size (not bedrooms)
            "I'm 25 years old",  # Age
            "My lease expires in 6 months",  # Time period
            "I've been searching for 2 weeks",  # Duration
            "There are 4 people in my family",  # Family size
            "I earn $50,000 per year",  # Annual income (not monthly rent)
            "My credit score is 700",  # Credit score
            "I have $5,000 in savings",  # Savings (not rent)
            "The apartment is on floor 3",  # Floor number
            "I need parking for 2 cars",  # Parking spaces
            "The building has 10 units",  # Total units
        ]
        
        print("\n🔢 Testing Number Extraction Precision")
        print("=" * 60)
        
        for query in ambiguous_number_queries:
            with self.subTest(query=query):
                params_v2 = self.router_v2.extract_parameters(query)
                
                print(f"Query: '{query}'")
                print(f"  Extracted Parameters: {params_v2}")
                
                # Check if inappropriate parameters were extracted
                warnings = []
                if 'bedrooms' in params_v2:
                    warnings.append(f"Extracted bedrooms: {params_v2['bedrooms']}")
                if 'max_rent' in params_v2:
                    warnings.append(f"Extracted max_rent: {params_v2['max_rent']}")
                
                if warnings:
                    print(f"  ⚠️  WARNING: {', '.join(warnings)}")
                else:
                    print("  ✅ No inappropriate parameter extraction")
                print()

    def test_context_dependent_classification(self):
        """Test that context affects classification appropriately"""
        
        # Test messages that should be classified differently based on context
        context_dependent_queries = [
            {
                "message": "try Brooklyn",
                "no_context": "Should be ambiguous without context",
                "with_context": "Should be WHAT_IF with search context"
            },
            {
                "message": "what about Queens?",
                "no_context": "Should be ambiguous without context", 
                "with_context": "Should be WHAT_IF with search context"
            },
            {
                "message": "check Manhattan",
                "no_context": "Could be CHECK_VIOLATIONS or ambiguous",
                "with_context": "Should be WHAT_IF with search context"
            },
            {
                "message": "show me more",
                "no_context": "Should be ambiguous without context",
                "with_context": "Should be SEARCH_LISTINGS with listings context"
            },
            {
                "message": "try 2 bedrooms",
                "no_context": "Should be ambiguous without context",
                "with_context": "Should be PARAMETER_REFINEMENT with search context"
            }
        ]
        
        print("\n🧠 Testing Context-Dependent Classification")
        print("=" * 60)
        
        search_context = {
            "borough": "Brooklyn",
            "bedrooms": 1,
            "max_rent": 2000,
            "voucher_type": "Section 8"
        }
        
        for test_case in context_dependent_queries:
            query = test_case["message"]
            
            print(f"Query: '{query}'")
            
            # Test without context
            intent_no_context = self.router_v2.classify_intent(query)
            print(f"  No Context: {intent_no_context} - {test_case['no_context']}")
            
            # Test with context
            intent_with_context = self.router_v2.classify_intent(query, search_context)
            print(f"  With Context: {intent_with_context} - {test_case['with_context']}")
            
            # The classification should be different or at least considered
            if intent_no_context == intent_with_context:
                print(f"  ⚠️  WARNING: Context didn't affect classification")
            else:
                print(f"  ✅ Context affected classification")
            print()

    def test_multilingual_false_positives(self):
        """Test that non-English text doesn't trigger false positives"""
        
        # Test cases in different languages that might trigger false positives
        multilingual_queries = [
            # Spanish
            ("¿Dónde está el baño?", "Where is the bathroom?"),
            ("Necesito ayuda con mi trabajo", "I need help with my work"),
            ("¿Cuánto cuesta la comida?", "How much does food cost?"),
            ("Voy a la tienda", "I'm going to the store"),
            ("Mi familia vive en España", "My family lives in Spain"),
            
            # Chinese
            ("你好吗？", "How are you?"),
            ("我需要帮助", "I need help"),
            ("今天天气很好", "The weather is nice today"),
            ("我在工作", "I am working"),
            ("这是我的朋友", "This is my friend"),
            
            # Bengali
            ("আপনি কেমন আছেন?", "How are you?"),
            ("আমার সাহায্য দরকার", "I need help"),
            ("আজ আবহাওয়া ভালো", "The weather is good today"),
            ("আমি কাজ করছি", "I am working"),
            ("এটি আমার বন্ধু", "This is my friend"),
        ]
        
        print("\n🌍 Testing Multilingual False Positives")
        print("=" * 60)
        
        for query, translation in multilingual_queries:
            with self.subTest(query=query):
                intent_v2 = self.router_v2.classify_intent(query)
                params_v2 = self.router_v2.extract_parameters(query)
                
                print(f"Query: '{query}' ({translation})")
                print(f"  Intent: {intent_v2}")
                print(f"  Parameters: {params_v2}")
                
                # Most non-housing related queries should be UNCLASSIFIED
                # Unless they're specifically about housing assistance
                if intent_v2 not in [Intent.UNCLASSIFIED, Intent.SHOW_HELP, Intent.VOUCHER_INFO]:
                    print(f"  ⚠️  WARNING: Non-housing query classified as {intent_v2}")
                else:
                    print("  ✅ Appropriately classified or unclassified")
                print()

    def test_edge_case_patterns(self):
        """Test edge cases that might break regex patterns"""
        
        edge_cases = [
            # Empty and whitespace
            "",
            "   ",
            "\n\t\r",
            
            # Special characters
            "!@#$%^&*()",
            "find apartments !!!!!",
            "brooklyn???",
            "section 8 --- help",
            
            # Very long messages
            "find " + "very " * 100 + "long apartment search query",
            
            # Mixed case and formatting
            "FIND APARTMENTS IN BROOKLYN",
            "find apartments in brooklyn",
            "FiNd ApArTmEnTs In BrOoKlYn",
            
            # Numbers in unusual formats
            "find 2.5 bedroom apartment",
            "rent under $2,500.00",
            "section 8 voucher",
            "1st floor apartment",
            "2nd bedroom needed",
            
            # Repeated words
            "find find find apartments",
            "brooklyn brooklyn brooklyn",
            "help help help me",
            
            # Partial words
            "apartmen",
            "brookly",
            "sectio",
            
            # Common typos
            "find apartmens",
            "brookln apartments",
            "secion 8 voucher",
            "manhatan listings",
        ]
        
        print("\n🔧 Testing Edge Case Patterns")
        print("=" * 60)
        
        for query in edge_cases:
            with self.subTest(query=query):
                try:
                    intent_v2 = self.router_v2.classify_intent(query)
                    params_v2 = self.router_v2.extract_parameters(query)
                    
                    print(f"Query: '{query}'")
                    print(f"  Intent: {intent_v2}")
                    print(f"  Parameters: {params_v2}")
                    print("  ✅ Handled without error")
                    
                except Exception as e:
                    print(f"Query: '{query}'")
                    print(f"  ❌ ERROR: {e}")
                    self.fail(f"Edge case caused exception: '{query}' -> {e}")
                print()

    def test_performance_with_complex_queries(self):
        """Test performance with complex and nested queries"""
        
        complex_queries = [
            "I'm looking for a 2-bedroom apartment in Brooklyn or Queens with Section 8 voucher under $2500 near subway stations and good schools for my kids",
            "What if I try Manhattan instead of Brooklyn but keep the same budget of $3000 for a 1-bedroom with CityFHEPS?",
            "Can you help me find housing in the Bronx or Staten Island with HASA voucher, preferably 3 bedrooms under $2000, and check for building violations?",
            "I need to search for apartments but I'm not sure about the borough, maybe Brooklyn or Queens, with 2 or 3 bedrooms, Section 8 accepted, under $2800",
            "Show me listings in Manhattan, Brooklyn, and Queens with 1-2 bedrooms, any voucher type accepted, budget flexible between $2000-$3500",
        ]
        
        print("\n⚡ Testing Performance with Complex Queries")
        print("=" * 60)
        
        import time
        
        for query in complex_queries:
            with self.subTest(query=query):
                start_time = time.time()
                
                intent_v2 = self.router_v2.classify_intent(query)
                params_v2 = self.router_v2.extract_parameters(query)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                print(f"Query: '{query[:80]}...'")
                print(f"  Intent: {intent_v2}")
                print(f"  Parameters: {params_v2}")
                print(f"  Processing Time: {processing_time:.4f} seconds")
                
                # Performance should be reasonable (under 1 second for regex)
                if processing_time > 1.0:
                    print(f"  ⚠️  WARNING: Slow processing time")
                else:
                    print("  ✅ Reasonable processing time")
                print()

    def test_email_classification_precision(self):
        """Test that email classification is precise and not overly aggressive"""
        
        # These should NOT be classified as email requests
        non_email_queries = [
            "I need an email address",
            "What's your email?",
            "Email me later",
            "I forgot my email password",
            "How do I set up email?",
            "My email is not working",
            "Can you send me an email?",
            "I don't have email access",
            "Email is important for communication",
            "I prefer email over phone calls",
        ]
        
        # These SHOULD be classified as email requests (with listings context)
        email_request_queries = [
            "write an email for listing 1",
            "compose email to landlord",
            "draft email for apartment inquiry",
            "send email about listing",
            "create email template",
            "email the property owner",
            "contact landlord via email",
            "write inquiry email",
        ]
        
        print("\n📧 Testing Email Classification Precision")
        print("=" * 60)
        
        print("NON-EMAIL QUERIES (should NOT be classified as email_request):")
        for query in non_email_queries:
            with self.subTest(query=query):
                classification = enhanced_classify_message(query, self.state_with_listings)
                
                print(f"Query: '{query}'")
                print(f"  Classification: {classification}")
                
                self.assertNotEqual(classification, "email_request",
                                  f"Incorrectly classified as email_request: '{query}'")
                print("  ✅ Correctly NOT classified as email_request")
                print()
        
        print("EMAIL REQUEST QUERIES (SHOULD be classified as email_request):")
        for query in email_request_queries:
            with self.subTest(query=query):
                classification = enhanced_classify_message(query, self.state_with_listings)
                
                print(f"Query: '{query}'")
                print(f"  Classification: {classification}")
                
                self.assertEqual(classification, "email_request",
                               f"Failed to classify as email_request: '{query}'")
                print("  ✅ Correctly classified as email_request")
                print()


if __name__ == "__main__":
    # Run the tests with verbose output
    unittest.main(verbosity=2, buffer=True) 