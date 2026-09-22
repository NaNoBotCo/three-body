==============================================================================
THE THREE-BODY PROBLEM
==============================================================================


The mathematics of the three-body problem in plain words, with the equations
printed and read out loud, the pictures computed from the equations, and the
orbits found rather than copied.

LIVE: https://nanobotco.github.io/three-body/

WHAT IS ON IT
------------------------------------------------------------------------------


  -  MATH — 13 chapters: the inverse-square law, two bodies solved in closed
     form, the equations for three, the ten conserved quantities and the two
     theorems that say there are no more of the usable kind, chaos and the
     Lyapunov time, the restricted problem and the five Lagrange points,
     Euler's line and Lagrange's triangle, the figure eight and the shape
     sphere, Sundman's convergent and useless series, singularities, how it is
     stepped on a computer, and what usually happens. 34 equations, each with
     a plain reading underneath.
  -  ORBITS — 9 periodic orbits, found here by scanning 40,000 starting speeds
     and then solving each near-miss until it closed. Each one carries its
     initial conditions, its period and the distance it returns to.
  -  HISTORY — 27 events, Newton 1687 to Webb at L2.
  -  CODE — the whole thing in thirty lines of Python with no libraries, which
     prints the figure eight as characters and checks its own energy.
  -  WORDS — 38 terms. SOURCES — 45.
  -  10 demos in the browser, all running the same leapfrog as the Python.

FIGURES COMPUTED AT BUILD TIME, NOT TYPED
------------------------------------------------------------------------------


      LYAPUNOV TIME FOR THE REFERENCE START
          value: 3.5144 time units

      SUN–EARTH L1, FROM THE QUINTIC
          value: 1,491,539 km

      RANDOM TRIPLES THAT EJECTED A BODY IN 60 TIME UNITS
          value: 435 of 643 (67.7%)

      THE SAME STARTS AT A THIRD OF THE STEP
          value: same share, 69% of individual triples end the same way


The last row is the point of the site in one line: the statistics are
reproducible and the trajectories are not.

BUILD
------------------------------------------------------------------------------


      python3 tools/find_orbits.py scan      # the return map over starting speeds (~3.5 min)
      python3 -c "import sys;sys.path.insert(0,'tools');import find_orbits as F;F.harvest(0.12)"
      python3 tools/draw.py                  # the pictures
      python3 tests/check_data.py            # the gate: every orbit re-integrated here
      ./publish.sh                           # build/ → docs/, which GitHub Pages serves
      python3 tools/serve.py 8846            # http://127.0.0.1:8846/three-body/


Needs Python 3, numpy and pillow. three_body.py needs nothing.

LICENCE
------------------------------------------------------------------------------


Code MIT. Text, data and pictures CC BY 4.0 — use them, credit NaNoBotCo, link
back.
