import functools
import traceback


def safe_call(default=None):
    """
    decorator ป้องกันไม่ให้ระบบล่ม ถ้ามี exception จะคืน default
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"[STABILITY] Error in {fn.__name__}: {e}")
                traceback.print_exc()
                return default
        return wrapper
    return deco
