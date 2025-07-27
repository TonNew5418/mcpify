def add(a, b):
    """Return the sum of a and b."""
    return a + b


def subtract(a, b):
    """Return the difference of a and b (a - b)."""
    return a - b


def multiply(a, b):
    """Return the product of a and b."""
    return a * b


def divide(a, b):
    """Return the quotient of a and b (a / b). Raises ZeroDivisionError if b is zero."""
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero.")
    return a / b


def get_random_quote():
    """Return a random inspirational math quote."""
    quotes = [
        "Mathematics is not about numbers, equations, computations or algorithms: it is about understanding.",
        "Pure mathematics is, in its way, the poetry of logical ideas.",
        "Mathematics is the most beautiful and most powerful creation of the human spirit.",
        "In mathematics, the art of proposing a question must be held of higher value than solving it.",
    ]
    from random import choice

    return choice(quotes)


def get_weather():
    """Return a random weather condition and temperature."""
    from random import choice, randint

    conditions = [
        "Sunny",
        "Cloudy",
        "Rainy",
        "Partly Cloudy",
        "Thunderstorms",
        "Snowy",
        "Windy",
    ]
    temp = randint(-10, 40)  # Temperature in Celsius
    condition = choice(conditions)
    return f"{condition} with temperature of {temp}°C"
