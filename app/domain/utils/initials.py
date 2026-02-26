import unicodedata

PALETTE = [
    "#2563EB",  # blue-600
    "#16A34A",  # green-600
    "#DC2626",  # red-600
    "#9333EA",  # purple-600
    "#EA580C",  # orange-600
    "#0891B2",  # cyan-600
    "#4F46E5",  # indigo-600
    "#059669",  # emerald-600
    "#D97706",  # amber-600
    "#DB2777",  # pink-600
]


def normalize_char(ch: str) -> str:
    base = unicodedata.normalize("NFD", ch)
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return base.upper()[0]


def hash_char(ch: str) -> int:
    return (ord(ch) * 2654435761) & 0xFFFFFFFF


def color_for_letter(letter: str) -> str:
    idx = hash_char(letter) % len(PALETTE)
    return PALETTE[idx]


def generate_initials_and_colors(first_name: str, last_name: str):
    first = normalize_char(first_name[0])
    last = normalize_char(last_name[0])

    initials = f"{first}{last}"
    colors = f"{color_for_letter(first)},{color_for_letter(last)}"

    return initials, colors
