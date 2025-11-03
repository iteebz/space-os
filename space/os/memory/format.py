from space.lib.format import humanize_timestamp


def format_memory_entries(entries: list, raw_output: bool = False) -> str:
    output_lines = []
    current_topic = None
    for e in entries:
        if e.topic != current_topic:
            if current_topic is not None:
                output_lines.append("")
            output_lines.append(f"# {e.topic}")
            current_topic = e.topic
        core_mark = " ★" if e.core else ""
        archived_mark = " [ARCHIVED]" if e.archived_at else ""
        timestamp_display = e.created_at if raw_output else humanize_timestamp(e.created_at)
        output_lines.append(
            f"[{e.memory_id[-8:]}] [{timestamp_display}] {e.message}{core_mark}{archived_mark}"
        )
    return "\n".join(output_lines)
