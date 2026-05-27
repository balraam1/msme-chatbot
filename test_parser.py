import sys
sys.path.insert(0, '.')
from app.llm import parse_structured_response

test_raw = """**[LIST]**
### ✅ Eligibility `⚠️ Verify करें`
SC/ST category ke liye 35% subsidy milti hai.
*Portal: kviconline.gov.in/pmegpplus*

**[DISCLAIMER]**
> ⓘ Amounts change ho sakti hain — verify karein: kviconline.gov.in/pmegpplus

**[NEXT STEP]**
**अगला कदम:** Apply karein. Note: Main apply nahi kar sakta — visit kviconline.gov.in/pmegpplus

**[ACTIONS]**
- `PMEGP ke liye documents kya chahiye?`
- `Subsidy kaise milegi?`
"""

result = parse_structured_response(test_raw)

print(f"items count: {len(result['items'])}")
print(f"items: {result['items']}")
print(f"disclaimer: {repr(result['disclaimer'])}")
print(f"next_step: {repr(result['next_step'])}")
print(f"actions: {result['actions']}")

assert len(result['items']) == 1, f'FAIL items count: {len(result["items"])}'
assert result['items'][0]['badge'] == '⚠️ Verify करें', f'FAIL badge: {repr(result["items"][0]["badge"])}'
assert result['disclaimer'] is not None, 'FAIL: disclaimer missing'
assert len(result['actions']) == 2, f'FAIL actions: {result["actions"]}'
assert result['raw'] == test_raw, 'FAIL: raw not preserved'

print('\nALL PARSER TESTS PASSED')
