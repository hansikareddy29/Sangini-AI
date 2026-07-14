import sys
import os

# Add the app directory to sys.path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agents.order_agent import extract_order

def run_tests():
    test_cases = [
        "I need 30 pickle jars and 20 papads by Friday",
        "Can I get 100 handicrafts?",
        "Neha wants 50 spices next week and also 10 pickles tomorrow",
        "I want a papad."
    ]

    print("Running Order Agent Tests...\n")
    for i, test in enumerate(test_cases):
        print(f"--- Test Case {i+1} ---")
        print(f"Input: {test}")
        try:
            result = extract_order(test)
            print(f"Output: {result.model_dump_json(indent=2)}\n")
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    run_tests()
