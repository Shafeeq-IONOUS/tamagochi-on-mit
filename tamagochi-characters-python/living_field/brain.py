"""
The brain.

Reads brain.metta and answers one question, twice a second: given how the
building is feeling, what should it express?

There are two ways it can answer, and both use the SAME rules file.

  1. If the MeTTa runtime (hyperon) is installed, the rules run as an actual
     MeTTa program, in the language they are written in.
  2. If it is not, a small matcher in this file reads the same rules and
     applies them itself.

Doing it this way was deliberate. The alternative -- MeTTa rules plus a Python
copy of the same logic as a backup -- means two sets of rules that drift apart,
and the backup is the one that runs on the night. Here there is one file. If
somebody edits a rule, both paths change together, and the fallback cannot
quietly disagree with what the rules say.

Worth being clear about what MeTTa is doing, because it would be easy to
overclaim: it is deciding which of a handful of behaviours to express, from
symbolic descriptions of an internal state. That is a genuine use of symbolic
reasoning and it is honestly quite small. It is not generating the imagery, and
saying so is better than pretending otherwise.
"""

import os
import re

RULES_PATH = os.path.join(os.path.dirname(__file__), "brain.metta")

VALID = {"startle", "attention", "memory", "dream", "tree", "forecast",
         "reef", "radar", "aurora", "sounding", "seismic"}


# ---------------------------------------------------------------------------
# Reading the rules
# ---------------------------------------------------------------------------
_RULE_RE = re.compile(
    r"^\(=\s*\(decide\s+(.+?)\)\s*\(\s*(\d+)\s+([a-z\-]+)\s*\)\s*\)\s*$"
)


def load_rules(path=RULES_PATH):
    """
    Pull the rules out of the MeTTa file, in order.

    Each becomes (rank, patterns, answer), where a pattern is either a literal
    word to match or None for a blank that matches anything. Sorted by rank,
    because rank -- not position in the file -- is what decides which rule wins.
    """
    rules = []
    with open(path) as fh:
        for line in fh:
            line = line.split(";")[0].strip()
            if not line:
                continue
            m = _RULE_RE.match(line)
            if not m:
                continue
            pats = [None if p.startswith("$") else p for p in m.group(1).split()]
            if len(pats) == 5 and m.group(3) in VALID:
                rules.append((int(m.group(2)), pats, m.group(3)))
    rules.sort(key=lambda r: r[0])
    return rules


def _best(results):
    """
    Pick the winner out of everything MeTTa matched.

    MeTTa hands back every rule that fits, in no promised order, so the rank
    inside each result is what decides. Lowest wins. This is the whole reason
    ranks exist -- see the note at the top of brain.metta.
    """
    best_rank, best = 10 ** 9, None
    for atom in results:
        parts = str(atom).strip().strip("()").split()
        if len(parts) == 2 and parts[0].isdigit():
            rank, answer = int(parts[0]), parts[1]
            if rank < best_rank:
                best_rank, best = rank, answer
    return best or "sounding"


# ---------------------------------------------------------------------------
class Brain:
    """Answers 'what should I express?'. Never raises, never blocks."""

    def __init__(self, prefer_metta=True):
        self.rules = load_rules()
        self.engine = "rules"       # what actually ran
        self._metta = None
        if prefer_metta:
            self._try_metta()

    def _try_metta(self):
        """Start the real MeTTa runtime if this machine has it."""
        try:
            from hyperon import MeTTa
        except Exception:
            return
        try:
            m = MeTTa()
            with open(RULES_PATH) as fh:
                m.run(fh.read())
            # Prove it actually answers before trusting it with the building.
            probe = m.run("!(decide alone low low low none)")
            if probe and probe[0] and _best(probe[0]) in VALID:
                self._metta = m
                self.engine = "metta"
        except Exception:
            self._metta = None

    def decide(self, facts):
        """
        facts comes from Creature.facts(). Returns one behaviour name.

        Falls back quietly. A brain that throws an exception in front of a
        crowd is worse than a brain that is briefly boring.
        """
        args = (facts["contact"], facts["arousal"], facts["curiosity"],
                facts["fatigue"], facts["crowd"])

        if self._metta is not None:
            try:
                res = self._metta.run(f"!(decide {' '.join(args)})")
                if res and res[0]:
                    answer = _best(res[0])
                    if answer in VALID:
                        return answer
            except Exception:
                self._metta = None          # stop trying; use the rules
                self.engine = "rules"

        return self._match(args)

    def _match(self, args):
        """The same rules, applied here. Lowest rank that fits wins."""
        for _rank, pats, answer in self.rules:
            if all(p is None or p == a for p, a in zip(pats, args)):
                return answer
        return "sounding"

    def allowed(self, facts):
        """
        Every expression the rules permit for this situation, best rank first.

        This is the rules changing job. They used to decide; now they say what
        is APPROPRIATE and the learner picks among those. It matters for more
        than tidiness: it means the building cannot learn its way into
        something it should not do. It can never discover that flinching gets
        attention and start flinching at everybody, because the rules simply do
        not offer startle unless it has genuinely been startled.

        Symbolic reasoning decides what is allowed. Learning decides what is
        good. Neither can override the other.
        """
        args = (facts["contact"], facts["arousal"], facts["curiosity"],
                facts["fatigue"], facts["crowd"])
        out = []
        for _rank, pats, answer in self.rules:
            if all(p is None or p == a for p, a in zip(pats, args)):
                if answer not in out:
                    out.append(answer)
        return out or ["sounding"]

    def explain(self, facts):
        """
        Which rule fired, in plain English. Worth having: during a demo you can
        say exactly why the building did what it did, rather than gesturing at
        a black box.
        """
        args = (facts["contact"], facts["arousal"], facts["curiosity"],
                facts["fatigue"], facts["crowd"])
        for rank, pats, answer in self.rules:
            if all(p is None or p == a for p, a in zip(pats, args)):
                said = " ".join(p if p else "any" for p in pats)
                return f"#{rank} ({said}) -> {answer}"
        return "no rule matched"
