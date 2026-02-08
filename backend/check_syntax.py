import sys
import re

filename = "/Users/car/ai预测/backend/app/services/data_aggregator.py"

with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Triple Quote Audit:")
count = 0
for i, line in enumerate(lines):
    if '"""' in line:
        count += 1
        print(f"{i+1}: {line.strip()}")

print(f"Total count: {count}")
if count % 2 != 0:
    print("ODD COUNT! Unbalanced quotes.")
else:
    print("Even count (Pairing check required).")
    
# Also run compile check
try:
    compile("".join(lines), filename, 'exec')
    print("Syntax OK")
except SyntaxError as e:
    print(f"SyntaxError: {e}")
