# Where the loop continued — 2026-09-16

The historical `WHERE_WE_STOPPED.md` checkpoint records the prior automatic
HUMAN_STOP state for EXP-MEM-001. The human explicitly overrode that stop.

EXP-MEM-001 remains closed as `INVALIDATED`; its sizing and one accuracy-blind
map-repair artifacts are preserved. The allowed recap is:

> Bajo el mapa random y el repair top-50, controles estructurales quedaron
> silenciosos en 5 celdas; AUC primario n=0; no hay evidencia válida de memoria
> ni de ventaja topológica en ese protocolo.

`EXP-MEM-002` is preregistered and starts with Q0: an accuracy-blind check of
train/test liveness and rate matching for connectome, DP, weight permutation,
ER, and ring across the frozen delay grid. Missing cells remain visible and
are not scored as a topology loss. No EXP-A or EXP-GLU branch is authorized
unless a later complete instrument produces an interpretable curve. Q0 and
the one permitted map-2 follow-up both ended `INSTRUMENT_INCOMPLETE`; the E1
fail-closed hygiene pass is committed as `dfdf7dd` and the current full suite
passes 72 tests.
