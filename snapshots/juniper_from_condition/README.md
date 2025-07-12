# juniper_from_condition

This lab showcases the Juniper `from condition` feature of `policy-statement.

There are three routers:

as65001 <-> as65002 <-> as65003

- as65001 is an IOS router exporting its loopback over BGP. It does not filter imports.
- as65002 is a JUNOS QFX router for which the behavior of `from condition` is under test.
  - To the left, it exports over BGP its loopback under the (always true) condition that a particular connected route is installed.
  - From the left, it imports from BGP any routes under the (always true) condition that a particular connected route is installed.
  - To the right, it exports over BGP its loopback under the (always false) condition that a particular route is present (it isn't).
  - From the right, it imports from BGP any routes under the (always false) condition that a particular route is present (it isn't).
  - Locally, it generates a particular aggregate under the (always true) condition that a particular connected route is installed.
  - Locally, it generates a particular aggregate under the (always false) condition that a particular route is installed (it isn't).
- as65003 is an IOS router exporting its loopback over BGP. It does not filter imports.

This lab shows the surprising result that _the always false condition is treated as always true under all contexts except BGP export_.
