#!/usr/bin/python3
# Guard for the public docs of this repository.
#
# - README.md sells and installs the packages; build commands live in BUILDING.md.
#   A build command in a README code block, a "$ " line or an inline code span fails.
# - README.md links to BUILDING.md, and BUILDING.md exists.
# - The internal documents moved to the private ops repo stay out of the tree
#   (AI assistant files, the backlogs, the workflow plan).
#
# Usage: check-public-docs.py [--self-test]   (run from the repository root)

import re
import subprocess
import sys

BUILD_TOOLS = {"rpmbuild", "mock", "spectool", "make", "meson", "cmake", "ninja",
               "livecd-creator", "livemedia-creator", "pnpm"}
PROMPTS = re.compile(r"^\s*(?:<[^>]*>\s*)?(?:\S*[$#]\s+)")
SEPARATORS = re.compile(r"&&|\|\||;|\|")
INTERNAL = re.compile(r"(^|/)CLAUDE\.md$|(^|/)\.claude/|^TODO\.md$|^GH-ACTION\.md$|^rack/TODO\.txt$")


def command_lines(text):
    """Yield (line number, command text) for every command a README shows."""
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.startswith("$ "):
            yield n, PROMPTS.sub("", line, count=1)
        else:
            for span in re.findall(r"`([^`]+)`", line):
                yield n, span


def build_commands(text):
    found = []
    for n, cmd in command_lines(text):
        for part in SEPARATORS.split(cmd):
            words = part.split()
            while words and (words[0] == "sudo" or "=" in words[0]):
                words.pop(0)
            if words and words[0] in BUILD_TOOLS:
                found.append((n, words[0]))
    return found


def check(readme, building_exists, tracked):
    errors = []
    for n, tool in build_commands(readme):
        errors.append("README.md:%d: build command '%s' belongs in BUILDING.md" % (n, tool))
    if not building_exists:
        errors.append("BUILDING.md is missing")
    if "BUILDING.md" not in readme:
        errors.append("README.md does not point to BUILDING.md")
    for path in tracked:
        if INTERNAL.search(path):
            errors.append("%s: internal document, it lives in the private ops repo" % path)
    return errors


def self_test():
    good = "Install:\n```\n$ sudo dnf install x\n```\nMake sure to read `dnf`.\nSee BUILDING.md.\n"
    cases = [
        ("a clean README passes", check(good, True, ["README.md", "x/x.spec"]), 0),
        ("rpmbuild in a code block fails",
         check(good + "```\n$ rpmbuild -ba x.spec\n```\n", True, []), 1),
        ("a root-prompt mock line fails",
         check(good + "```\n<chroot> sh-5.0# mock --clean\n```\n", True, []), 1),
        ("make after && fails", check(good + "$ cd x && make\n", True, []), 1),
        ("an inline span fails", check(good + "Run `cmake -B build`.\n", True, []), 1),
        ("prose 'make' passes", check(good + "We make packages.\n", True, []), 0),
        ("a missing BUILDING.md fails", check(good, False, []), 1),
        ("a README without the link fails", check("Install.\n", True, []), 1),
        ("CLAUDE.md anywhere fails", check(good, True, ["CLAUDE.md", "x/CLAUDE.md"]), 2),
        ("root TODO.md fails, a package TODO passes", check(good, True, ["TODO.md", "x/TODO.md"]), 1),
    ]
    ok = True
    for name, errors, want in cases:
        if len(errors) == want:
            print("ok   self-test: %s" % name)
        else:
            ok = False
            print("FAIL self-test: %s: %r" % (name, errors))
    print("SELF-TEST OK" if ok else "SELF-TEST FAILED")
    return 0 if ok else 1


def main():
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                             check=True).stdout.splitlines()
    try:
        open("BUILDING.md").close()
        building = True
    except FileNotFoundError:
        building = False
    errors = check(readme, building, tracked)
    for e in errors:
        print(e)
    print("PUBLIC-DOCS %s" % ("FAIL" if errors else "OK"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
