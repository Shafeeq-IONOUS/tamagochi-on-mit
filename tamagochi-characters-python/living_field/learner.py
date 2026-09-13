"""
The part that actually learns.

Up to here the building has a body and rules for using it. That is embodied, but
it is not embodied AI -- nothing it does tonight is any better than what it did
last night. Replace the rules with ten if-statements and it behaves identically.

This is the missing loop: the building tries a way of expressing itself, watches
whether people stay, and gets better at holding a crowd. Nobody tells it that
the aurora works better than the radar sweep at nine o'clock in the cold. It
finds out, at this site, on this night, through its own sensor.

WHAT IT ACTUALLY IS, PLAINLY

A contextual multi-armed bandit. Each way of expressing itself is an arm; the
reward is whether people were still there afterwards. It balances trying things
it has not tried much against repeating what has worked. That is a small,
old, well-understood algorithm, and calling it that is better than calling it
something grander.

What makes it embodied is not the algorithm, it is where the reward comes from:
nobody labels anything, there is no dataset, and the only feedback is whether
actual people in an actual plaza stayed to watch. The building learns by doing
the thing, in the place, with the people.

HOW IT SITS WITH THE RULES

The rules in brain.metta do not go away, but they change job. They used to
decide. Now they CONSTRAIN: they say which expressions are appropriate for the
situation the building is in, and the learner picks among only those. So the
building can never learn its way into something inappropriate -- it cannot
discover that flinching at people gets attention and start doing it constantly,
because the rules do not offer startle unless it has genuinely been startled.

Symbolic reasoning decides what is allowed. Learning decides what is good.
"""

import json
import math
import os
import time

# How long after choosing an expression we wait before judging it. Long enough
# that somebody could arrive, notice, and decide whether to stay.
JUDGE_AFTER = 25.0

# How much a single evening can move an opinion. Deliberately slow: the
# building should not decide a world is wonderful because one person happened
# to walk past during it.
LEARNING_RATE = 0.16

# How strongly it prefers trying something it knows little about. Higher means
# more curious, lower means more set in its ways.
CURIOSITY = 0.55

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".learned.json")


class AttentionLearner:
    """Learns which expressions hold people, from watching whether they stay."""

    def __init__(self, arms, remember=True, enabled=True):
        # No sense organ, no learning.
        #
        # This is not a nicety, it is a correctness bug that already happened.
        # With no sensor attached, every observation returned a reward of zero,
        # so the building concluded that everything it does is worthless -- and
        # it punished whatever it had tried MOST, which was the useful default.
        # It starved the forecast and sat on one mode all night.
        #
        # An agent that cannot perceive the consequences of its actions must not
        # update its beliefs about them. With no sensor it simply follows the
        # rules, which is exactly what it should do.
        self.enabled = enabled
        self.arms = list(arms)
        # value: how well this expression has held people, 0 to 1.
        # tries: how many times it has been given a fair go.
        self.value = {a: 0.5 for a in self.arms}
        self.tries = {a: 0.0 for a in self.arms}
        self._pending = None          # (arm, chosen_at, presence_at_choice)
        self._remember = remember
        self.total = 0
        if remember and enabled:
            self._load()

    # -- choosing ---------------------------------------------------------
    def choose(self, allowed, t):
        """
        Pick from the expressions the rules currently permit.

        Prefers whatever has held people best, but keeps a bias towards
        anything it has not tried much -- otherwise the first thing that
        happens to work gets repeated all night and nothing else is ever
        given a chance.
        """
        allowed = [a for a in allowed if a in self.value] or self.arms
        if not self.enabled:
            # Follow the rules. allowed is already best-rank-first.
            return allowed[0]
        best, best_score = allowed[0], -1e9
        for a in allowed:
            unknown = CURIOSITY * math.sqrt(1.0 / (1.0 + self.tries[a]))
            score = self.value[a] + unknown
            if score > best_score:
                best_score, best = score, a
        return best

    # -- watching what happened -------------------------------------------
    def began(self, arm, t, presence):
        """Note that this expression has just started, and what was going on."""
        self._pending = (arm, t, presence)

    def observe(self, t, presence, touches_since):
        """
        Judge the expression that has been running, if it has run long enough.

        `presence` is how much somebody is there right now, 0 to 1.
        `touches_since` is how many people have touched it since it started.

        Reward is deliberately simple and honest: did people stay, and did
        anyone reach out. A world that empties the plaza scores badly even if
        it is beautiful, which is the whole point of measuring instead of
        guessing.
        """
        if not self.enabled or self._pending is None:
            return None
        arm, began_at, presence_then = self._pending
        if t - began_at < JUDGE_AFTER:
            return None
        self._pending = None

        stayed = min(1.0, presence)
        reached = min(1.0, touches_since / 3.0)
        # Holding somebody who was already there counts; so does drawing
        # somebody who was not.
        drew = max(0.0, presence - presence_then)
        reward = min(1.0, 0.5 * stayed + 0.35 * reached + 0.45 * drew)

        self.tries[arm] += 1.0
        self.value[arm] += LEARNING_RATE * (reward - self.value[arm])
        self.total += 1
        if self._remember and self.total % 5 == 0:
            self._save()
        return arm, reward

    # -- what it has come to think ----------------------------------------
    def ranking(self):
        return sorted(self.arms, key=lambda a: -self.value[a])

    def report(self, top=3):
        r = self.ranking()[:top]
        return "  ".join(f"{a} {self.value[a]:.2f}" for a in r)

    def _load(self):
        try:
            with open(os.path.abspath(MEMORY_FILE)) as fh:
                d = json.load(fh)
            for a in self.arms:
                if a in d.get("value", {}):
                    self.value[a] = float(d["value"][a])
                    self.tries[a] = float(d.get("tries", {}).get(a, 0.0))
            self.total = int(d.get("total", 0))
        except Exception:
            pass

    def _save(self):
        try:
            with open(os.path.abspath(MEMORY_FILE), "w") as fh:
                json.dump({"value": self.value, "tries": self.tries,
                           "total": self.total, "saved": time.time()}, fh)
        except Exception:
            pass
