#!/usr/bin/env python3
"""
Run Living Field.

    python3 run_living_field.py                 window only
    python3 run_living_field.py plucky-eagle    window + the simulator

Press ? nothing. Press D for the demo, R to race. The keys are listed in
living_field/run.py and printed in the window.
"""
import sys
from living_field.run import main

if __name__ == "__main__":
    sys.exit(main())
