#!/bin/sh
# The known answer for gate-red-test: proves the fixture and grader agree, at $0.
set -e
printf 'def add(a, b):\n    return a + b\n' > calc.py
git commit -qam "ENG-1: add returns the sum"
