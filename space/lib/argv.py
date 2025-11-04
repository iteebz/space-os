import sys
from typing import Optional


def flex_args(option_name: str, option_short: Optional[str] = None) -> None:
    """Reorder argv so option precedes subcommand.

    Args:
        option_name: Long option name (e.g., "as" for "--as")
        option_short: Short option name (e.g., "a" for "-a")
    """
    args = sys.argv[1:]
    if not args:
        return
    
    option_long = f"--{option_name}"
    option_flags = [option_long]
    if option_short:
        option_flags.append(f"-{option_short}")
    
    option_idx = None
    option_value = None
    
    for i, arg in enumerate(args):
        if arg in option_flags and i + 1 < len(args):
            option_idx = i
            option_value = args[i + 1]
            break
    
    if option_idx is None:
        return
    
    if option_idx > 0 and not args[0].startswith("-"):
        args_list = list(args)
        args_list.pop(option_idx + 1)
        args_list.pop(option_idx)
        args_list.insert(0, option_long)
        args_list.insert(1, option_value)
        sys.argv[1:] = args_list
