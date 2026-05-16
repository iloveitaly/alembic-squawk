import re
SQUAWK_IGNORE_RE = re.compile(r"^#\s*(?:--\s*)?(squawk-.*)", re.MULTILINE)
text = """
# squawk-disable rule1
#squawk-disable rule2
# -- squawk-ignore-file rule3
#--squawk-enable rule4
    # squawk-disable indented
"""
print(SQUAWK_IGNORE_RE.findall(text))
