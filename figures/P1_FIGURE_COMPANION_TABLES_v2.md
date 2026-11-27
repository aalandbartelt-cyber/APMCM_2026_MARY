# P1 companion numeric material for redesigned figures

These are existing diagnostics and display summaries. They are not embedded in any figure or manuscript. All quantities retain their original scope and conditioning.

## F2: fold-specific uniform-null references at k=20

The event is V<=2. Each row uses one outer fold; p values are existing, unadjusted descriptive references after development selection. They are not pooled or averaged.

| Route | Fold | N | M | Hits | p |
| --- | ---: | ---: | ---: | ---: | ---: |
| H-soft | 1 | 2254 | 31 | 14 | 1.02332e-23 |
| H-soft | 2 | 2254 | 29 | 14 | 3.00804e-24 |
| H-soft | 3 | 2254 | 29 | 14 | 3.00804e-24 |
| H-soft | 4 | 2247 | 22 | 14 | 1.31848e-26 |
| H-soft | 5 | 2247 | 17 | 12 | 2.28299e-23 |
| additive_ridge | 1 | 2254 | 31 | 2 | 0.0298238 |
| additive_ridge | 2 | 2254 | 29 | 3 | 0.0018855 |
| additive_ridge | 3 | 2254 | 29 | 2 | 0.0263167 |
| additive_ridge | 4 | 2247 | 22 | 2 | 0.0156309 |
| additive_ridge | 5 | 2247 | 17 | 1 | 0.141472 |
| mean | 1 | 2254 | 31 | 1 | 0.242823 |
| mean | 2 | 2254 | 29 | 0 | 1 |
| mean | 3 | 2254 | 29 | 0 | 1 |
| mean | 4 | 2247 | 22 | 0 | 1 |
| mean | 5 | 2247 | 17 | 0 | 1 |
| random_hash | 1 | 2254 | 31 | 0 | 1 |
| random_hash | 2 | 2254 | 29 | 0 | 1 |
| random_hash | 3 | 2254 | 29 | 0 | 1 |
| random_hash | 4 | 2247 | 22 | 0 | 1 |
| random_hash | 5 | 2247 | 17 | 0 | 1 |

## A2: existing pooled diagnostic coefficients

No calibration was refitted. Only the single requested slope annotation per curve remains in the image. Bin counts and singleton high-probability bins remain documented in A2_reliability_bins.csv.

| Route | Slope | Intercept | Brier | N | Positives |
| --- | ---: | ---: | ---: | ---: | ---: |
| B-eps | 1.243553 | 0.278502 | 0.00575083 | 11256 | 128 |
| S-eps | 1.761725 | 0.979405 | 0.00612525 | 11256 | 128 |
| L-single | 0.840568 | -0.584295 | 0.01089397 | 11256 | 128 |
| L-hash4 | 0.981719 | -0.250298 | 0.00742196 | 11256 | 128 |

## A5: protocol denominators

N and M are evaluation exposures, not necessarily unique compositions. EF omits undefined zero-positive evaluations. The heatmap is protocol-level evidence, not final-model validation.

| Protocol | Evaluations | N sum | M sum | EF defined | Total budget | Defined-EF budget |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| element | 5 | 20181 | 224 | 5 | 100 | 100 |
| target | 3 | 6762 | 297 | 3 | 60 | 60 |
| xleave | 35 | 11256 | 128 | 29 | 700 | 580 |

The colour reference is the same route's frozen AB-blocked OOF metric: R-log RMSE 4.9048363921; R-log EF 60.4863492710; S-eps EF 62.2234054773. Colour is 100*(stress/reference-1), not an ease ranking across protocols.

## A6: R-log feature ladder moved out of the image

The redesigned A6 contains only reverse-ablation intervals for H-soft. This separate R-log comparison is preserved without joining the two routes into one ladder.

| Route | Feature block | RMSE | Mean EF@20 |
| --- | --- | ---: | ---: |
| R-log | F0 | 5.195443 | 27.047156 |
| R-log | F3 | 4.954692 | 57.365980 |
| R-log | F3+E1 | 4.904836 | 60.486349 |
