import sys
sys.path.insert(0, '.')
from backend.logic.roe_analyzer import analyze_roe
from backend.logic.growth_analyzer import analyze_growth
from backend.logic.valuation_analyzer import analyze_valuation
import pprint

dt = '2025-09-15'
print(f"--- ROE on {dt} ---")
pprint.pprint(analyze_roe('ABB', evaluation_date=dt))

print(f"\n--- Growth on {dt} ---")
pprint.pprint(analyze_growth('ABB', evaluation_date=dt))

print(f"\n--- Valuation on {dt} ---")
pprint.pprint(analyze_valuation('ABB', evaluation_date=dt))

