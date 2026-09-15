"""The three product roles and their historical physical Shortcut variants."""

SHORTCUT_PROFILES = {
    "CREATE": {
        "target": "Blink",
        "oracle": "Blink Create Test",
        "candidate": "Blink Create Stage2 WORK",
    },
    "DONE": {
        "target": "Blink DONE",
        "oracle": "Blink DONE Test",
        "candidate": None,
    },
    "FILES": {
        "target": "Blink Files",
        "oracle": "Blink Files",
        "candidate": "Blink Files Stage2 VIEW TEST",
    },
}


def product_roles() -> tuple[str, ...]:
    return tuple(SHORTCUT_PROFILES)
