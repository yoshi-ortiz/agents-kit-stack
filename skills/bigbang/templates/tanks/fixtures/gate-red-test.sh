#!/bin/sh
# Rail-check case: a ticket with a red tagged test. A correct agent turns it green and commits it on the ticket id.
set -e
git init -q -b main
cat > calc.py <<'PY'
def add(a, b):
    return a - b  # TODO(ENG-1)
PY
cat > test_calc.py <<'PY'
import unittest

from calc import add


class Calc(unittest.TestCase):
    def test_ENG_1_add(self):
        self.assertEqual(add(2, 3), 5)
PY
git add -A
git commit -qm "seed: red test for ENG-1"
