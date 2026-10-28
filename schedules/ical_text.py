"""RFC 5545 text encoding shared by calendar downloads and subscriptions."""


def escape_ical(value):
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def fold_ical_line(value):
    """Fold content lines without splitting UTF-8 characters (75 octets)."""
    lines = []
    line = ""
    size = 0
    for character in value:
        width = len(character.encode("utf-8"))
        if size + width > 75:
            lines.append(line)
            line = " "
            size = 1
        line += character
        size += width
    lines.append(line)
    return "\r\n".join(lines)
