import sys


def flex_args(option_name: str, option_short: str | None = None) -> None:
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


def extract_flag(
    args: list[str], long_flag: str, short_flag: str | None = None
) -> tuple[str | None, list[str]]:
    """Extract flag and optional value from args.

    Args:
        args: Argument list to parse
        long_flag: Long form (e.g., "--resume")
        short_flag: Short form (e.g., "-r")

    Returns:
        (flag_value, remaining_args) where flag_value is:
        - None if flag not present
        - "" if flag present without value
        - value if flag present with value
    """
    flags = [long_flag]
    if short_flag:
        flags.append(short_flag)

    value = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] in flags:
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                value = args[i + 1]
                i += 2
            else:
                value = ""
                i += 1
        else:
            remaining.append(args[i])
            i += 1
    return value, remaining
