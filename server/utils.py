import re


def extract_paragraph_around(doc:str, left:int, right:int, max_window_length=1024):
    par_marks = [m.span(0)[0] for m in re.finditer("\n\n", doc)]
    left_mark = max(m for m in par_marks if m <= left)
    right_mark = min(m for m in par_marks if m >= right)

    add_left = ""
    add_right = ""

    if left_mark < left - max_window_length:
        left_mark = left - max_window_length
        add_left = "..."

    if right_mark > right + max_window_length:
        right_mark = right + max_window_length
        add_right = "..."

    return doc[left_mark:right_mark].strip()
