"""Threading utilities."""
from threading import Thread


def autotask(func):
    """Decorator to run a function in a background daemon thread."""
    def decor(*args, **kwargs):
        t = Thread(target=func, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()

    return decor