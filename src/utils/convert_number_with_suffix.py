def convert_number_with_suffix(number_str: str) -> int:
    """
    Converts a string number with a suffix (k, m, b) to an integer.

    Args:
        number_str (str): The string number to convert.

    Returns:
        int: The converted integer.
    """
    number_str = number_str.replace(",", "")
    if number_str[-1].lower() == "k":
        return int(float(number_str[:-1]) * 1e3)
    elif number_str[-1].lower() == "m":
        return int(float(number_str[:-1]) * 1e6)
    elif number_str[-1].lower() == "b":
        return int(float(number_str[:-1]) * 1e9)
    else:
        return int(number_str)
