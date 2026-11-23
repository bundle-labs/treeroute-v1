"""Print the staged PAPER_FACTS.md lines that differ from the live file (read only).

Usage: py -3.9 -I -B show_facts_changes.py <live PAPER_FACTS.md> <staged PAPER_FACTS.md>
Added lines are printed whole; for a replaced line only the changed span is printed.
"""
import difflib
import sys


def main():
    sys.stdout.reconfigure(encoding="ascii", errors="backslashreplace")
    with open(sys.argv[1], encoding="utf-8", newline="") as f:
        old = f.read().split("\n")
    with open(sys.argv[2], encoding="utf-8", newline="") as f:
        new = f.read().split("\n")
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "insert":
            for k in range(b1, b2):
                print("ADDED L%d: %s" % (k + 1, new[k]))
        elif op == "replace":
            for ka, kb in zip(range(a1, a2), range(b1, b2)):
                o, n = old[ka], new[kb]
                i = 0
                while i < min(len(o), len(n)) and o[i] == n[i]:
                    i += 1
                j = 0
                while j < min(len(o), len(n)) - i and o[-1 - j] == n[-1 - j]:
                    j += 1
                print("REPLACED L%d -> L%d" % (ka + 1, kb + 1))
                print("   old span: %s" % o[max(0, i - 60): len(o) - j + 10])
                print("   new span: %s" % n[max(0, i - 60): len(n) - j + 10])
        elif op != "equal":
            print("OTHER", op, a1, a2, b1, b2)


if __name__ == "__main__":
    main()
