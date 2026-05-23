Produce the complete ETCS Level 2 message sequence (LinkedList) for the following scenario.

## Scenario Features

```json
{scenario_features}
```

## Similar validated chains (from semantic cache)

The following chains were retrieved as structurally similar to this scenario. Use them as sequence references — adapt all field values to the current scenario features above.

```json
{chain_examples}
```

## Relevant spec context ({spec_version})

{rag_context}

## LinkedList output schema

```json
{output_schema}
```

## Instructions

1. Output a single JSON code block (` ```json ... ``` `) containing the complete LinkedList.
2. Echo `scenario_features` **unchanged** in the `"scenario_features"` field.
3. Set `"spec_version": "{spec_version}"`.
4. Choose the sequence pattern based on `scenario_features.initial_mode`:
   - `"SR"` → Pattern A (SR → FS): PR(SR) · MA · ACK · PR(FS)
   - `"SB"` → Pattern B (SB → SR → FS): PR(SB) · PR(SR) · MA · ACK · PR(FS)
   - `"FS"` → Pattern C (emergency or update): PR(FS) · MA · ACK · PR(FS)
5. Derive section values **directly** from `scenario_features.sections` — do not invent section lengths or speeds.
6. List session-level fields in `to_instantiate`; do not put them in `scenario_params`:
   - Always in `to_instantiate`: `Q_SCALE`, `T_TRAIN`, `NID_LRBG`, `L_MESSAGE`, `M_ACK`
7. Include Packet 21 (GradientProfile) in the MA if `scenario_features.gradient_profile` is not empty.
8. Include Packet 27 (StaticSpeedProfile) in the MA if sections have different `v_max_kmh` values.
9. Add a `planner_notes` string to each message explaining its role.
