import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure src is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from agents.llm import call_with_failover, get_available_provider

class TestProviderFailover(unittest.TestCase):
    
    @patch('agents.llm.get_available_provider')
    @patch('agents.llm.generate_gemini')
    @patch('agents.llm.generate_groq')
    @patch('time.sleep')
    def test_case_1_gemini_success(self, mock_sleep, mock_groq, mock_gemini, mock_providers):
        """Case 1: Gemini succeeds on first attempt, no failover occurs."""
        mock_providers.return_value = [
            {"name": "Gemini", "model": "gemini-2.5-flash", "api_key": "gemini_key_123"},
            {"name": "Groq", "model": "llama-3.3-70b-versatile", "api_key": "groq_key_123"},
        ]
        
        mock_gemini.return_value = "Gemini Success Response"
        
        result = call_with_failover("Test Prompt")
        
        self.assertEqual(result, "Gemini Success Response")
        mock_gemini.assert_called_once()
        mock_groq.assert_not_called()
        
    @patch('agents.llm.get_available_provider')
    @patch('agents.llm.generate_gemini')
    @patch('agents.llm.generate_groq')
    @patch('time.sleep')
    def test_case_2_gemini_429_groq_success(self, mock_sleep, mock_groq, mock_gemini, mock_providers):
        """Case 2: Gemini fails with transient 429, SRE triggers failover to Groq which succeeds."""
        mock_providers.return_value = [
            {"name": "Gemini", "model": "gemini-2.5-flash", "api_key": "gemini_key_123"},
            {"name": "Groq", "model": "llama-3.3-70b-versatile", "api_key": "groq_key_123"},
        ]
        
        # Gemini throws HTTP 429 transient error
        mock_gemini.side_effect = Exception("HTTP 429: Too Many Requests / Quota Exceeded")
        mock_groq.return_value = "Groq Success Response"
        
        result = call_with_failover("Test Prompt")
        
        self.assertEqual(result, "Groq Success Response")
        # Gemini should be retried 4 times (1 initial attempt + 3 SRE delays)
        self.assertEqual(mock_gemini.call_count, 4)
        mock_groq.assert_called_once()
        
    @patch('agents.llm.get_available_provider')
    @patch('agents.llm.generate_gemini')
    @patch('agents.llm.generate_groq')
    @patch('agents.llm.generate_openrouter')
    @patch('time.sleep')
    def test_case_3_gemini_groq_fail_openrouter_success(self, mock_sleep, mock_openrouter, mock_groq, mock_gemini, mock_providers):
        """Case 3: Gemini and Groq fail with transient errors, SRE triggers failover to OpenRouter which succeeds."""
        mock_providers.return_value = [
            {"name": "Gemini", "model": "gemini-2.5-flash", "api_key": "gemini_key_123"},
            {"name": "Groq", "model": "llama-3.3-70b-versatile", "api_key": "groq_key_123"},
            {"name": "OpenRouter", "model": "meta-llama/llama-3.3-70b-instruct:free", "api_key": "openrouter_key_123"},
        ]
        
        mock_gemini.side_effect = Exception("HTTP 503 Service Unavailable")
        mock_groq.side_effect = Exception("HTTP 502 Bad Gateway")
        mock_openrouter.return_value = "OpenRouter Success Response"
        
        result = call_with_failover("Test Prompt")
        
        self.assertEqual(result, "OpenRouter Success Response")
        self.assertEqual(mock_gemini.call_count, 4)
        self.assertEqual(mock_groq.call_count, 4)
        mock_openrouter.assert_called_once()
        
    @patch('agents.llm.get_available_provider')
    @patch('agents.llm.generate_gemini')
    @patch('agents.llm.generate_groq')
    @patch('time.sleep')
    def test_case_4_all_providers_fail(self, mock_sleep, mock_groq, mock_gemini, mock_providers):
        """Case 4: All providers fail, SRE raises clean user-friendly exception without stack traces."""
        mock_providers.return_value = [
            {"name": "Gemini", "model": "gemini-2.5-flash", "api_key": "gemini_key_123"},
            {"name": "Groq", "model": "llama-3.3-70b-versatile", "api_key": "groq_key_123"},
        ]
        
        mock_gemini.side_effect = Exception("HTTP 429 Quota Exceeded")
        mock_groq.side_effect = Exception("HTTP 503 Spikes in demand")
        
        with self.assertRaises(Exception) as context:
            call_with_failover("Test Prompt")
            
        self.assertIn("All AI search engines are busy due to extremely high public traffic", str(context.exception))
        self.assertEqual(mock_gemini.call_count, 4)
        self.assertEqual(mock_groq.call_count, 4)

if __name__ == "__main__":
    unittest.main()
