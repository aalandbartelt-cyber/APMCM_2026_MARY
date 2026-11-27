# P1 visual redesign v2

2026-11-27. The user's latest visual instructions supersede the previous rejected eight-figure design. F1 v3 is accepted and remains byte-for-byte unchanged.

## Reference foundation

Read in the requested order: reference 30 in full; figure playbook sections 13-16; reference 25 sections 25.9-25.12. The required D plotting template remains the actual style foundation through apply_apmcm_style() followed by use_times_new_roman().

## Encoding decisions

- F2: four explicit route colours, shapes and dashes; labelled k=20 and EF=1 references. The low-EF window has a source-region rectangle, two connecting lines, a bounded zoom label, and the same x-coordinate semantics and series marks. It covers the original data range k=1-100, EF=0-1.5; extra axis padding is only layout space.
- F3: steel-blue metal / hatched amber nonmetal stacks; all four Pareto symbols have matched keys and direct route labels.
- A1: zero-centred blue-white-amber bias heat strip, signed values for grayscale; RMSE circles and absolute-error q95 diamonds.
- A2: only reliability observations, an ideal diagonal, route names and one requested slope annotation per curve. Full coefficients and counts move to companion numeric material. Every observed route and the ideal line has an explicit matching key.
- A3: four rank violins with all raw ranks; a fixed graphics-only kernel in log10 rank, no estimated bandwidth or model fitting. Reverse and forward costs use the blue/amber ends of the common diverging palette on opposite sides of a white zero, with explicit direction keys; intensity adds no further variable. Quantiles have four separate shape keys.
- A4: single-to-mean-of-ten slope graphs; pool identity is redundant in colour, line pattern and shape. Nearby value labels use short leaders to unchanged data coordinates.
- A5: route-specific raw metrics annotated in a matrix; colour encodes signed percentage change from the same route's existing AB-blocked OOF reference. This is not a cross-protocol difficulty ranking. Continuous colourbars count as legends, with their quantity and centre explicitly labelled.
- A6: existing bilateral 95% interval whiskers, square/circle point estimates and a vertical zero line. Grey crosses zero, amber stays above, blue stays below. There is no zero-to-point stem.

## Palette amendment

The current directive explicitly changes F2 baseline colours and F3 metal/nonmetal colours and requires steel-blue/amber/green/brick/pink families. palette_redesign_v2.json records this authorised amendment; palette_frozen.json remains the historical approval and is not overwritten. F1 is the user's explicit unchanged exception. The historical all-eight-colour Delta-E assertion is not silently attributed to the amended palette; grayscale readability is checked on each actual export using shapes, dashes, hatch, position and signed numbers.

## Delivery discipline

No overall titles, embedded tables, explanatory sentences, or lollipop plots in the revised eight figures. All figures have nine technical/design checks plus matching-legend review. Full colour and grayscale PNGs were visually inspected; no physical print test was performed. Every PDF uses embedded Times New Roman at 8.5 pt or larger and retains native 170 mm width. Sources, models, code and the fit ledger remain unchanged. All new writes are confined to figures/.
