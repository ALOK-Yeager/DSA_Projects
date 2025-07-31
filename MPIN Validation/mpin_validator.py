from datetime import date
from typing import Optional, Dict, List, Set

# These are the official reason codes we need to use.
# It's important to stick to these exact strings as required.
REASON_COMMONLY_USED = "COMMONLY_USED"
REASON_DOB_SELF = "DEMOGRAPHIC_DOB_SELF"
REASON_DOB_SPOUSE = "DEMOGRAPHIC_DOB_SPOUSE"
REASON_ANNIVERSARY = "DEMOGRAPHIC_ANNIVERSARY"

def is_sequence(pin: str) -> bool:
    """
    Checks if a PIN is a simple sequence like '1234' or '8765'.
    It also handles "wrap-around" cases, for example, '8901', where
    the numbers circle back from 9 to 0.
    """
    if len(pin) < 2:
        return False

    # Turn the pin string into a list of numbers.
    digits = [int(d) for d in pin]

    # Figure out the step between the first two digits.
    # The modulo (%) helps handle the wrap-around from 9 to 0.
    step = (digits[1] - digits[0]) % 10
    if step > 5:  # This handles negative steps like 2 -> 1, which is -1.
        step = step - 10

    # Check if the rest of the digits follow the same step.
    for i in range(1, len(digits) - 1):
        expected_next = (digits[i] + step) % 10
        if digits[i+1] != expected_next:
            return False

    return True

def is_repetition(pin: str) -> bool:
    """
    Checks for repeating patterns, which are very common weak PINs.
    This covers simple cases like '1111' and patterns like '1212' or '123123'.
    """
    pin_length = len(pin)
    if pin_length < 2:
        return False

    # A quick check to see if all digits are the same.
    if len(set(pin)) == 1:
        return True

    # Look for repeating chunks (e.g., '12' in '1212').
    for pattern_length in range(1, pin_length // 2 + 1):
        if pin_length % pattern_length == 0:
            pattern = pin[:pattern_length]
            if pattern * (pin_length // pattern_length) == pin:
                return True

    return False

def is_palindrome(pin: str) -> bool:
    """
    Checks if the PIN reads the same forwards and backward (e.g., '1221').
    These are easy to remember, so people use them a lot.
    """
    return pin == pin[::-1]

# --- KEYPAD PATTERN DETECTION ---

# Giving each keypad number an (x, y) coordinate.
KEYPAD_COORDS = {
    '1': (0, 0), '2': (1, 0), '3': (2, 0),
    '4': (0, 1), '5': (1, 1), '6': (2, 1),
    '7': (0, 2), '8': (1, 2), '9': (2, 2),
    '0': (1, 3)
}

def _is_collinear(p1: tuple, p2: tuple, p3: tuple) -> bool:
    """
    A helper to check if three points on the keypad form a straight line.
    Using the cross-product method is a reliable way to do this that
    avoids potential division-by-zero issues.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    return (y2 - y1) * (x3 - x2) == (y3 - y2) * (x2 - x1)

def is_keypad_pattern(pin: str) -> bool:
    """
    Checks if the PIN forms a simple geometric shape on the keypad.
    People often pick PINs that are easy to type, like straight lines,
    corners, or L-shapes. This function looks for those.
    """
    if len(pin) < 3:
        return False

    # Convert the PIN digits to their (x, y) coordinates.
    try:
        coords = [KEYPAD_COORDS[d] for d in pin]
    except KeyError:
        return False  # Abort if the PIN has a non-keypad digit like '*' or '#'.

    # First, see if the PIN makes a straight line.
    if len(coords) >= 3:
        is_line = True
        for i in range(len(coords) - 2):
            if not _is_collinear(coords[i], coords[i+1], coords[i+2]):
                is_line = False
                break
        if is_line:
            return True

    # Next, check for L-shapes in 4-digit PINs.
    # An L-shape should have one right angle turn.
    if len(coords) == 4:
        right_angles = 0
        for i in range(1, 3):
            # Create vectors for the line segments.
            dx1 = coords[i][0] - coords[i-1][0]
            dy1 = coords[i][1] - coords[i-1][1]
            dx2 = coords[i+1][0] - coords[i][0]
            dy2 = coords[i+1][1] - coords[i][1]

            # The dot product is zero if the vectors are perpendicular.
            if dx1 * dx2 + dy1 * dy2 == 0:
                right_angles += 1

        if right_angles == 1:
            return True

    # Finally, check against a list of common corner-based patterns.
    if pin in {"1397", "1793", "3179", "3971", "7139", "7931", "9317", "9713"}:
        return True

    return False

# --- DATE-BASED PATTERN DETECTION ---

def _is_valid_date(d: date) -> bool:
    """
    A simple helper to make sure we're working with a real date.
    This prevents errors from trying to process something like February 30th.
    It's always good practice to validate inputs first.
    """
    if d.month < 1 or d.month > 12:
        return False

    if d.month in {1, 3, 5, 7, 8, 10, 12}:
        return 1 <= d.day <= 31
    elif d.month in {4, 6, 9, 11}:
        return 1 <= d.day <= 30
    else:  # It's February
        # Check if it's a leap year.
        is_leap = (d.year % 4 == 0 and d.year % 100 != 0) or (d.year % 400 == 0)
        return 1 <= d.day <= (29 if is_leap else 28)

    return True

def generate_date_pins(d: date) -> Set[str]:
    """
    Creates a set of all the PINs someone might create from a date.
    This covers different formats people use, like MMDD, DDMM, DDMMYY, etc.
    It also handles the "century ambiguity" problem (e.g., does '24' mean 1924 or 2024?).
    """
    # First, make sure the date is even possible.
    if not _is_valid_date(d):
        return set()

    pins = set()
    dd = f"{d.day:02d}"
    mm = f"{d.month:02d}"

    # Get the current year to help guess the century.
    current_year = date.today().year
    current_century = current_year // 100 * 100

    # Create 4-digit pins, covering both US (MMDD) and European (DDMM) styles.
    pins.add(dd + mm)
    pins.add(mm + dd)

    # Create 6-digit pins, checking both the current and previous centuries.
    for century in [current_century - 100, current_century]:
        year_in_century = d.year - century
        if 0 <= year_in_century < 100:
            yy = f"{year_in_century:02d}"
            pins.add(dd + mm + yy)
            pins.add(mm + dd + yy)
            pins.add(yy + mm + dd)

    # Just in case, also generate a PIN using the year's last two digits directly.
    yy_direct = f"{d.year % 100:02d}"
    pins.add(dd + mm + yy_direct)
    pins.add(mm + dd + yy_direct)
    pins.add(yy_direct + mm + dd)

    # Clean up the set to make sure we only have valid 4 or 6 digit PINs.
    return {p for p in pins if len(p) in {4, 6} and p.isdigit()}


# --- MAIN VALIDATOR ---

def check_pin_strength(pin: str,
                      dob_self: Optional[date] = None,
                      dob_spouse: Optional[date] = None,
                      anniversary: Optional[date] = None) -> Dict[str, object]:
    """
    This is the main function that pulls everything together.
    It checks a PIN against all the weakness criteria.
    Key principles:
    1. Follow the API rules: Only return 'WEAK' or 'STRONG'.
    2. Check inputs first: Don't process bad data.
    3. Be specific: Only flag PINs that are clearly weak for a good reason.
    4. Default to secure: If a PIN is invalid, it's not 'WEAK', it's just unusable.
       So we treat it as 'STRONG' because it can't be guessed.
    """
    reasons = []

    # First, validate the PIN format itself. This has to be the first step.
    if not pin or not pin.isdigit() or len(pin) not in {4, 6}:
        # An invalid PIN isn't a weak PIN. It's an error.
        # Per the requirements, we return STRONG with no reasons.
        return {
            "strength": "STRONG",
            "reasons": []
        }

    # Now, check for common patterns that make a PIN weak.
    if is_sequence(pin) or is_repetition(pin) or is_palindrome(pin) or is_keypad_pattern(pin):
        reasons.append(REASON_COMMONLY_USED)

    # Check if the PIN matches any personal dates, but only if the dates are valid.
    if dob_self and _is_valid_date(dob_self) and pin in generate_date_pins(dob_self):
        reasons.append(REASON_DOB_SELF)

    if dob_spouse and _is_valid_date(dob_spouse) and pin in generate_date_pins(dob_spouse):
        reasons.append(REASON_DOB_SPOUSE)

    if anniversary and _is_valid_date(anniversary) and pin in generate_date_pins(anniversary):
        reasons.append(REASON_ANNIVERSARY)

    # If we found any reasons, the PIN is weak. Otherwise, it's strong.
    return {
        "strength": "WEAK" if reasons else "STRONG",
        "reasons": reasons
    }

# --- COMPREHENSIVE TEST SUITE ---

def run_tests() -> bool:
    """
    A full set of tests to make sure the validator works correctly.
    A good test suite thinks like an attacker:
    1. Check for false positives: Make sure strong PINs are not flagged as weak.
    2. Check edge cases: Test tricky situations like leap years and wrap-around numbers.
    3. Use real-world examples: Test against actual common PINs.
    """
    test_cases = [
        # --- API Contract Tests (The most important ones) ---
        {"name": "Invalid PIN - too short", "pin": "123", "expected": {"strength": "STRONG", "reasons": []}},
        {"name": "Invalid PIN - too long", "pin": "12345", "expected": {"strength": "STRONG", "reasons": []}},
        {"name": "Invalid PIN - non-numeric", "pin": "123a", "expected": {"strength": "STRONG", "reasons": []}},
        {"name": "Invalid PIN - empty", "pin": "", "expected": {"strength": "STRONG", "reasons": []}},

        # --- False Positive Tests (Making sure we don't block good PINs) ---
        {"name": "Strong PIN - a known uncommon one", "pin": "8068", "expected": {"strength": "STRONG", "reasons": []}},
        {"name": "Strong PIN - corners in a random order", "pin": "1739", "expected": {"strength": "STRONG", "reasons": []}},
        {"name": "Strong PIN - almost a sequence", "pin": "1235", "expected": {"strength": "STRONG", "reasons": []}},
        {"name": "Strong PIN - looks like a pattern but isn't common", "pin": "1358", "expected": {"strength": "STRONG", "reasons": []}},

        # --- Sequence Tests ---
        {"name": "Sequence - simple increasing", "pin": "1234", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Sequence - wrap-around", "pin": "8901", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Sequence - decreasing", "pin": "9876", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Sequence - even numbers", "pin": "2468", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},

        # --- Repetition Tests ---
        {"name": "Repetition - all same digit", "pin": "1111", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Repetition - paired digits", "pin": "1212", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Repetition - three-digit pattern", "pin": "123123", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},

        # --- Keypad Pattern Tests ---
        {"name": "Keypad - vertical line", "pin": "2580", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Keypad - horizontal line", "pin": "456", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Keypad - diagonal line", "pin": "159", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Keypad - L-shape", "pin": "1478", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Keypad - corners in sequence", "pin": "1397", "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED]}},
        {"name": "Keypad - corners not in sequence", "pin": "1739", "expected": {"strength": "STRONG", "reasons": []}},

        # --- Date-Based Tests ---
        {"name": "DOB - Self (DDMM)", "pin": "0503", "dob_self": date(1990, 3, 5), "expected": {"strength": "WEAK", "reasons": [REASON_DOB_SELF]}},
        {"name": "DOB - Self (MMDD)", "pin": "0305", "dob_self": date(1990, 3, 5), "expected": {"strength": "WEAK", "reasons": [REASON_DOB_SELF]}},
        {"name": "DOB - Spouse (YYMMDD)", "pin": "900305", "dob_spouse": date(1990, 3, 5), "expected": {"strength": "WEAK", "reasons": [REASON_DOB_SPOUSE]}},
        {"name": "Anniversary (DDMMYY)", "pin": "050390", "anniversary": date(1990, 3, 5), "expected": {"strength": "WEAK", "reasons": [REASON_ANNIVERSARY]}},
        {"name": "Century Ambiguity - 1900s", "pin": "020198", "dob_self": date(1998, 1, 2), "expected": {"strength": "WEAK", "reasons": [REASON_DOB_SELF]}},
        {"name": "Century Ambiguity - 2000s", "pin": "020104", "dob_self": date(2004, 1, 2), "expected": {"strength": "WEAK", "reasons": [REASON_DOB_SELF]}},
        {"name": "Date Test - Non-leap year", "pin": "2902", "dob_self": date(1999, 2, 28), "expected": {"strength": "STRONG", "reasons": []}},

        # --- Multi-Reason Tests ---
        {"name": "Multiple reasons - Sequence and DOB", "pin": "1234", "dob_self": date(2012, 3, 4), "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED, REASON_DOB_SELF]}},
        {"name": "Multiple reasons - Repetition and Anniversary", "pin": "1212", "anniversary": date(1912, 12, 1), "expected": {"strength": "WEAK", "reasons": [REASON_COMMONLY_USED, REASON_ANNIVERSARY]}},
    ]

    passed = 0
    for i, test in enumerate(test_cases):
        # Set up keyword arguments for the main function.
        kwargs = {}
        if "dob_self" in test:
            kwargs["dob_self"] = test["dob_self"]
        if "dob_spouse" in test:
            kwargs["dob_spouse"] = test["dob_spouse"]
        if "anniversary" in test:
            kwargs["anniversary"] = test["anniversary"]

        try:
            result = check_pin_strength(test["pin"], **kwargs)

            # Sort reasons so the order doesn't matter for comparison.
            expected_reasons = sorted(test["expected"]["reasons"])
            actual_reasons = sorted(result["reasons"])

            if result["strength"] == test["expected"]["strength"] and actual_reasons == expected_reasons:
                print(f"✅ PASSED: {test['name']}")
                passed += 1
            else:
                print(f"❌ FAILED: {test['name']}")
                print(f"   Expected: {test['expected']}")
                print(f"   Got:      {result}")
        except Exception as e:
            print(f"❌ ERROR: {test['name']} - {str(e)}")

    total = len(test_cases)
    print("\n" + "="*50)
    print(f"TEST SUMMARY: {passed}/{total} passed ({passed/total:.1%})")
    print("="*50)

    return passed == total

if __name__ == "__main__":
    print("Running PIN Validation Test Suite...")
    run_tests()