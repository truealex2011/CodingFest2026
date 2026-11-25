import re

MAX_NAME_LEN = 20
_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёҮүӨөҺһ0-9 _\-]+$")


class NameError_(ValueError):
    pass


def validate_name(raw: str | None) -> str:
    name = " ".join((raw or "").split())
    if not name:
        raise NameError_("Имя не может быть пустым. Введите, как вас зовут.")
    if len(name) > MAX_NAME_LEN:
        raise NameError_(f"Имя слишком длинное: максимум {MAX_NAME_LEN} символов.")
    if not _NAME_RE.match(name):
        raise NameError_("Используйте только буквы, цифры, пробел, дефис и «_».")
    if not any(ch.isalpha() for ch in name):
        raise NameError_("В имени должна быть хотя бы одна буква.")
    return name
