import tomllib

BASE_PATH = r"C:\Users\inara\OneDrive\Documents\ilja\PycharmProjects\kodland-tele-bots\finalProject\\"


def toml_to_dict(toml_string: str) -> dict:
    """Parse TOML content and return a dictionary.

    :param toml_string: TOML-formatted text.
    :return: A Python dictionary representation of the TOML content.
    """
    return tomllib.loads(toml_string)


def toml_file_to_dict(file_path: str) -> dict:
    """Read a TOML file and return its contents as a dictionary.

    :param file_path: Relative path to the TOML file, resolved against `BASE_PATH`.
    :return: A dictionary representing the TOML file data.
    """
    new_path = BASE_PATH + file_path
    with open(new_path, "rb") as f:
        return tomllib.load(f)


def dict_to_toml(data: dict, path="") -> str:
    """Serialize a Python dictionary to a TOML string.

    Optionally writes the TOML output to `<path>.toml`.

    :param data: Dictionary to serialize.
    :param path: Optional file path (without `.toml`) to save output.
    :return: Serialized TOML string.
    """

    def serialize_section(d, prefix=""):
        local_lines = []
        local_sections = []

        for key, value in d.items():
            if isinstance(value, dict):
                section_name = f"{prefix}.{key}" if prefix else key
                local_sections.append((section_name, value))
            else:
                local_lines.append(f"{key} = {format_value(value)}")

        result = "\n".join(local_lines)

        for section_name, section_dict in local_sections:
            result += f"\n\n[{section_name}]\n"
            result += serialize_section(section_dict, section_name)

        return result


    result = serialize_section(data)

    if path:
        with open(f"{path}.toml", "w", encoding="utf-8") as f:
            f.write(result)

    return result


def format_value(value):
    """Marshal basic Python values into TOML literal syntax.

    :param value: Python value to format.
    :return: TOML-safe literal string for the value.
    """
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(format_value(v) for v in value) + "]"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return '""'

    raise TypeError(f"Unsupported type: {type(value)}")


# Load and print pyproject.toml for debugging when module is run directly.
newd = toml_file_to_dict(r"pyproject.toml")
print(newd)
print(dict_to_toml(newd))