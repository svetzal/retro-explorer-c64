#!/usr/bin/env python3
"""Check a document against the mechanical rules of ASD-STE100.

The checks are deterministic. Each one reports only what a machine can decide
without knowledge of grammar: sentence length, paragraph length, semicolons,
phrases such as "and then", and a curated list of common non-STE words.

The script does not check the passive voice, noun clusters, or judgement rules
such as "one instruction per sentence". Those need a person or an agent
reading the text.

Sentences and paragraphs are read across wrapped lines. Front matter, code
fences, tables, link targets, URLs and inline code are not prose and are not
checked. A word or a phrase in double quotes is a mention, so the word-choice
and phrase checks ignore it.

This script is self-contained. It paraphrases STE principles and does not
embed the ASD-STE100 dictionary, which is ASD copyright. For word-level
authority, download the specification from https://www.asd-ste100.org/.

  ste_check.py DOCUMENT.md            flag mechanical violations
  ste_check.py DOCUMENT.md --json     same, as JSON
  ste_check.py A.md B.md              check several files

Exit code is 1 when findings exist, so the script works as a gate.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PROCEDURAL_LIMIT = 20
DESCRIPTIVE_LIMIT = 25
PARAGRAPH_LIMIT = 6

# Words that commonly open an instruction. Used only to decide which sentence
# length limit applies; not a claim about the STE dictionary.
IMPERATIVE_OPENERS = set("""
add apply check clean click close configure confirm connect copy create delete
disable disconnect do download edit enable enter examine export find flush get
import insert install keep list load lock log make monitor move obey open
paste pause press pull push put read reboot remove rename repeat replace
restart restore resume review run save select send set show shut start stop
tap test try turn type unlock update upload use verify wait write
""".split())

# Common non-STE words in engineering documentation, with replacements. A
# curated example list, not the controlled dictionary.
WORD_CHOICE = {
    "ensure": "make sure",
    "verify": "make sure, or 'do a check of'",
    "utilize": "use",
    "utilise": "use",
    "leverage": "use",
    "perform": "do",
    "execute": "do (for a step; 'run' a program is a technical verb)",
    "commence": "start",
    "initiate": "start",
    "terminate": "stop",
    "cease": "stop",
    "sufficient": "enough",
    "attempt": "try",
    "additional": "more",
    "assist": "help",
    "indicate": "show",
    "approximately": "about",
    "demonstrate": "show",
    "facilitate": "help, or rebuild the sentence",
    "modification": "change",
    "modifications": "changes",
    "functionality": "function, or name the behavior",
    "aforementioned": "name the thing again",
    "via": "with, through, or by",
}

PHRASES = {
    "and then": "split into two instructions",
    "in order to": "to",
    "prior to": "before",
    "subsequent to": "after",
    "in the event of": "if",
    "at this point in time": "now",
    "carry out": "do",
    "make sure to": "a direct instruction ('Do X.', with 'Make sure that' for conditions)",
}
# Whole words only, and across a line wrap.
PHRASE_PATTERNS = {
    phrase: re.compile(r"\b" + r"\s+".join(map(re.escape, phrase.split())) + r"\b",
                       re.IGNORECASE)
    for phrase in PHRASES
}

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^\s*#")
TABLE_ROW = re.compile(r"^\s*\|")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
BLOCKQUOTE = re.compile(r"^\s*(>\s?)+")
LINK_DEFINITION = re.compile(r"^\s*\[[^\]]+\]:\s")
HTML_COMMENT = re.compile(r"^\s*<!--.*-->\s*$")
INLINE_CODE = re.compile(r"`[^`]*`")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
LINK_LABEL = re.compile(r"\]\[[^\]]*\]")
URL = re.compile(r"<?https?://[^\s>]+>?")
HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")
HTML_ENTITY = re.compile(r"&#?\w+;")
# Text in double quotes names a word or a phrase. It does not use it.
QUOTED = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d')
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")

# A full stop after one of these does not end a sentence.
ABBREVIATIONS = {"e.g.", "i.e.", "vs.", "cf.", "Dr.", "Mr.", "Mrs.", "Ms."}
# A full stop after one of these does not end a sentence before a number.
NUMBER_ABBREVIATIONS = {"No.", "Vol.", "Fig.", "p.", "pp."}
# A person's initial, as in "LeRoy W. Gross".
INITIAL = re.compile(r"^[A-Z]\.$")
SENTENCE_END = re.compile(r"[.!?]+[\"')\]*_]*\s+")
# A link that follows the end of a sentence is a citation for that sentence.
TRAILING_CITATION = re.compile(r"(?<=[.!?])\s+\[[^\]]*\](?=\s|$)")
# A citation link or a bold label that stands alone is not a sentence.
NOT_A_SENTENCE = re.compile(r"^(\[[^\]]*\][.,]?|\*\*[^*]+\*\*[.:]?|__[^_]+__[.:]?)$")


def clean(line):
    """Replace what is not prose. Inline code and URLs each count as one word."""
    line = INLINE_CODE.sub("CODE", line)
    line = LINK_TARGET.sub("]", line)
    line = LINK_LABEL.sub("]", line)
    line = URL.sub("URL", line)
    line = HTML_TAG.sub("", line)
    line = HTML_ENTITY.sub(" ", line)
    return line


def unquoted(text):
    """Blank the text in double quotes, and keep every offset."""
    return QUOTED.sub(lambda match: " " * len(match.group()), text)


def ends_sentence(text, match):
    """Decide whether the punctuation at this match ends a sentence.

    When the text does not decide, split. A split can only make a sentence
    shorter, so it cannot cause a false sentence-length finding.
    """
    following = text[match.end():match.end() + 1]
    if following.islower():
        return False
    before = text[:match.start() + 1].split()
    preceding = before[-1].lstrip("\"'([*_")
    if INITIAL.match(preceding) and len(before) > 1 and before[-2][:1].isupper():
        return False
    if preceding in ABBREVIATIONS:
        return False
    if preceding in NUMBER_ABBREVIATIONS and following.isdigit():
        return False
    return True


def sentences(text):
    """Split prose into (offset, sentence) pairs."""
    # Blank each trailing citation, and keep the offsets of the text after it.
    text = TRAILING_CITATION.sub(lambda match: " " * len(match.group()), text)
    found = []
    start = 0
    for match in SENTENCE_END.finditer(text):
        if ends_sentence(text, match):
            found.append((start, text[start:match.end()].strip()))
            start = match.end()
    found.append((start, text[start:].strip()))
    return [(offset, sent) for offset, sent in found
            if WORD.search(sent) and not NOT_A_SENTENCE.match(sent)]


def words(sentence):
    return WORD.findall(sentence)


def base_form(token):
    """Reduce an inflected form to a base the word-choice table may hold."""
    for strip in ("ing", "ed", "es", "s", "d"):
        if token.endswith(strip) and len(token) - len(strip) >= 4:
            stem = token[: -len(strip)]
            for candidate in (stem, stem + "e"):
                if candidate in WORD_CHOICE:
                    return candidate
    return token


def check_word_choice(lowered, findings, path, lineno, where=""):
    seen = set()
    for tok in lowered:
        base = tok if tok in WORD_CHOICE else base_form(tok)
        if base in WORD_CHOICE and base not in seen:
            seen.add(base)
            shown = base if base == tok else f"{tok} ({base})"
            findings.append((path, lineno, "word-choice",
                             f"\"{shown}\"{where} — prefer: {WORD_CHOICE[base]}"))


def check_sentence(sent, findings, path, lineno):
    toks = words(sent)
    lowered = [t.lower() for t in toks]

    procedural = lowered[0] in IMPERATIVE_OPENERS
    limit = PROCEDURAL_LIMIT if procedural else DESCRIPTIVE_LIMIT
    if len(toks) > limit:
        kind = "procedural" if procedural else "descriptive"
        findings.append((path, lineno, "sentence-length",
                         f"{len(toks)} words in a {kind} sentence (limit {limit}): "
                         f"\"{sent[:60]}...\""))

    mentioned = [t.lower() for t in words(unquoted(sent))]
    check_word_choice(mentioned, findings, path, lineno)


def check_heading(text, findings, path, lineno):
    """Headings are not sentences, but the word-choice rule still applies — a
    title is the first thing a scanning reader parses."""
    lowered = [t.lower() for t in words(unquoted(clean(text)))]
    check_word_choice(lowered, findings, path, lineno, " in heading")


def check_block(lines, findings, path):
    """Check one paragraph or one list item. Return its number of sentences.

    `lines` holds (line number, cleaned text) pairs. The block is joined so
    that a sentence or a phrase can continue across a line wrap.
    """
    starts = []
    offset = 0
    for lineno, text in lines:
        starts.append((offset, lineno))
        offset += len(text) + 1
        if ";" in text:
            findings.append((path, lineno, "semicolon",
                             "semicolon — split into two sentences or use a list"))
    joined = " ".join(text for _, text in lines)

    def line_at(position):
        return [lineno for start, lineno in starts if start <= position][-1]

    for phrase, pattern in PHRASE_PATTERNS.items():
        for match in pattern.finditer(unquoted(joined)):
            findings.append((path, line_at(match.start()), "phrase",
                             f"\"{phrase}\" — prefer: {PHRASES[phrase]}"))

    found = sentences(joined)
    for position, sent in found:
        check_sentence(sent, findings, path, line_at(position))
    return len(found)


def check_file(path):
    findings = []
    name = str(path)
    in_fence = False
    in_front_matter = False
    block = []
    block_is_list = False
    para_sentences = 0
    para_start = 0

    def flush_block():
        nonlocal block, para_sentences
        if block:
            count = check_block(block, findings, name)
            if not block_is_list:
                para_sentences += count
            block = []

    def end_paragraph():
        nonlocal para_sentences, block_is_list
        flush_block()
        if para_sentences > PARAGRAPH_LIMIT:
            findings.append((name, para_start, "paragraph-length",
                             f"{para_sentences} sentences in one paragraph "
                             f"(limit {PARAGRAPH_LIMIT})"))
        para_sentences = 0
        block_is_list = False

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if lineno == 1 and raw.strip() == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            in_front_matter = raw.strip() != "---"
            continue
        if FENCE.match(raw):
            end_paragraph()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if HEADING.match(raw):
            end_paragraph()
            check_heading(raw.lstrip(" #"), findings, name, lineno)
            continue
        if TABLE_ROW.match(raw) or LINK_DEFINITION.match(raw) or HTML_COMMENT.match(raw):
            end_paragraph()
            continue

        raw = BLOCKQUOTE.sub("", raw)
        if not raw.strip():
            end_paragraph()
            continue

        if LIST_ITEM.match(raw):
            # Each list item is its own block. It is not part of a paragraph.
            flush_block()
            block_is_list = True
            raw = LIST_ITEM.sub("", raw)
        elif not block and not block_is_list and para_sentences == 0:
            para_start = lineno
        # A line that follows a list item with no blank line continues that item.
        block.append((lineno, clean(raw).strip()))

    end_paragraph()
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = ap.parse_args()

    findings = []
    for path in args.files:
        if not path.exists():
            print(f"error: {path} does not exist", file=sys.stderr)
            return 2
        findings.extend(check_file(path))

    if args.json:
        print(json.dumps([
            {"file": f, "line": n, "check": c, "message": m}
            for f, n, c, m in findings
        ], indent=2))
    else:
        for f, n, c, m in findings:
            print(f"{f}:{n} [{c}] {m}")
        if not findings:
            print("clean — no mechanical findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
