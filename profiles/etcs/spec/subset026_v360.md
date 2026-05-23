# Subset-026 v3.6.0 — ETCS System Requirements Specification
## Selected Sections for ETCS Level 2 Scenario Generation

This document contains structured excerpts from SUBSET-026 v3.6.0, the normative specification for the European Train Control System (ETCS). The sections included here are those most relevant to generating and validating ETCS Level 2 message sequences.

---

## §4 — ETCS Operating Modes

### §4.1 — Overview

ETCS operating modes define the supervision behaviour of the on-board unit (OBU). Each mode determines:
- Which supervision functions are active (speed, distance, position)
- Which messages the OBU may send or receive
- What transitions are permitted

Mode information is reported in every PositionReport via the `M_MODE` field.

---

### §4.6 — Mode Definitions

#### §4.6.1 — Full Supervision (FS)

**Identifier:** FS  
**M_MODE value:** 0

FS is the normal operating mode under full RBC supervision. The on-board unit supervises the train against the Movement Authority with full accuracy.

**Entry conditions:**
- Valid MA received from RBC (NID_MESSAGE=3)
- MA acknowledged by the driver (NID_MESSAGE=8 sent)
- Train position known with sufficient accuracy
- ETCS Level 2: radio session established with responsible RBC

**Supervision in FS:**
- Position supervision: distance to End of Authority
- Speed supervision: V_MAX from Static Speed Profile (Packet 27)
- Gradient compensation: via Gradient Profile (Packet 21)

**Exit conditions:**
- MA expires without renewal → transition to SR
- Communication loss exceeding timeout → transition to TR or SR
- Mode Profile received → may transition to OS

---

#### §4.6.2 — On Sight (OS)

**Identifier:** OS  
**M_MODE value:** 1

OS mode is used when the train must enter a section that may be occupied or where route clearance cannot be guaranteed. The driver takes visual responsibility.

**Entry conditions:**
- RBC sends a Mode Profile packet (Packet 80) indicating an on-sight area
- Typically included in the MovementAuthority message

**Supervision in OS:**
- Speed limited to V_MODE_OS (typically 30–40 km/h, profile-specific)
- Driver responsible for stopping before obstacles

---

#### §4.6.3 — Shunting (SH)

**Identifier:** SH  
**M_MODE value:** 2

Low-speed shunting operation. Not normally generated in MA scenarios.

---

#### §4.6.4 — Staff Responsible (SR)

**Identifier:** SR  
**M_MODE value:** 3

SR mode is used when the driver has authority to proceed without an active MA from the RBC. This is the normal mode after establishing radio contact but before the first MA is received.

**Entry conditions:**
- Driver action (start of mission)
- Transition from SB following session establishment

**Supervision in SR:**
- Speed monitored against national/default SR speed limit
- No distance supervision (no MA)
- Position reported to RBC via PositionReport

**Key rule:** A MovementAuthority (NID_MESSAGE=3) received while in SR initiates the SR→FS transition sequence.

---

#### §4.6.5 — System Failure (SF)

**Identifier:** SF  
**M_MODE value:** 4

Entered when the on-board detects a critical failure. Emergency brake applied.

---

#### §4.6.6 — No Power (NP)

**Identifier:** NP  
**M_MODE value:** 8

OBU is powered off. No ETCS supervision.

---

#### §4.6.7 — Stand By (SB)

**Identifier:** SB  
**M_MODE value:** 9

Initial state after the OBU powers up. Awaiting driver action to initiate start of mission.

**Entry conditions:**
- Power-on

**Exit conditions:**
- Driver initiates start of mission → SR

---

### §4.6.8 — Mode Transitions

#### Transition: SB → SR

**Trigger:** Driver action (start of mission procedure)  
**Spec ref:** Subset-026 §4.6  
**Message sequence:** None mandatory in the transition itself; the train sends a PositionReport in SR mode after the transition.

---

#### Transition: SR → FS

**Trigger:** MA received and acknowledged  
**Spec ref:** Subset-026 §4.6.3  

**Required message sequence:**
1. RBC sends NID_MESSAGE=3 (MovementAuthority) with M_ACK=1
2. Train sends NID_MESSAGE=8 (Acknowledgement)
3. On-board transitions to FS
4. Train sends NID_MESSAGE=0 (PositionReport) with M_MODE=0

The SR→FS transition is the central interaction in a standard Level 2 MA scenario.

---

#### Transition: FS → SR

**Trigger:** MA expires (train reaches EOA without new MA), or communication loss  
**Spec ref:** Subset-026 §4.6.4

---

#### Transition: FS → OS

**Trigger:** Mode Profile packet received in MA indicating an on-sight area  
**Spec ref:** Subset-026 §4.6.5

---

### §4.6.9 — Invalid Mode Transitions

The following transitions are **not permitted** and must be flagged as validation errors:

| Forbidden | Reason |
|-----------|--------|
| NP → FS directly | Must go through SB and SR |
| SR → FS without prior MA | FS requires a valid MA |
| FS → SB | SB is a power-on state only |

---

## §6 — Radio Communication and Session Management (Level 2)

### §6.1 — Level 2 Architecture

In ETCS Level 2, all supervision information is transmitted via GSM-R radio between the on-board unit and the Radio Block Centre (RBC). The RBC controls a defined section of track.

### §6.2 — Session Establishment

A radio session must be established before the RBC can issue a Movement Authority.

**Session establishment sequence:**
1. OBU powers up → mode SB
2. Driver initiates start of mission → mode SR
3. OBU initiates radio connection to responsible RBC
4. RBC authenticates train (NID_ENGINE, NID_C, NID_RBC)
5. RBC establishes session → may now issue MA

**Impact on message sequencing:**
- NID_MESSAGE=3 (MA) must occur **after** the session is established
- In the message sequence model: MA must follow at least one PositionReport in SR mode (session heuristic)
- Error code `STATE_MA_BEFORE_SESSION` is raised if MA appears before the first SR PositionReport

### §6.3 — Session and Position Correlation

After session establishment, the RBC and on-board exchange position information to correlate the train's reported position with the track database. This is done via PositionReports (NID_MESSAGE=0).

---

## §7.4 — Position Report

### §7.4.1 — Purpose

The PositionReport (NID_MESSAGE=0) is sent by the train to the RBC to report:
- Current position relative to the Last Relevant Balise Group (LRBG)
- Current speed
- Current ETCS mode and level

The RBC uses PositionReports to track train position and determine when to issue or renew MAs.

### §7.4.2 — Position Report Variables

#### Q_SCALE (§7.4.2.1)

Distance and speed resolution qualifier. Applied to all distance and speed fields in the same message.

| Value | Resolution | Maximum distance |
|-------|-----------|-----------------|
| 0 | 0.1 m (10 cm) | 3,276.6 m |
| 1 | 1 m | 32,766 m |
| 2 | 10 m | 327,660 m |

**Typical use:** Q_SCALE=1 (1 m resolution) for most Level 2 scenarios.

#### NID_LRBG (§7.4.2.2)

Last Relevant Balise Group identifier. 14-bit field within the full 24-bit NID_LRBG (which includes NID_C). The LRBG is the most recently passed balise group that serves as the train's position reference.

Range: 0–16383

#### D_LRBG (§7.4.2.3)

Distance from the front of the train to the LRBG, measured in the direction the LRBG is oriented. Encoded according to Q_SCALE. Unsigned integer.

- If the train has not moved from the LRBG position: D_LRBG=0
- Increases as train moves away from LRBG in the nominal direction

#### Q_DIRLRBG (§7.4.2.4)

Direction qualifier for the LRBG.

| Value | Meaning |
|-------|---------|
| 0 | Train moving in nominal direction (same as balise link orientation) |
| 1 | Train moving in reverse (against balise orientation) |
| 2 | Unknown |

#### V_TRAIN (§7.4.2.5)

Current train speed, encoded as unsigned integer with 5 km/h resolution per bit.

| Encoded value | Speed |
|--------------|-------|
| 0 | 0 km/h (stopped) |
| 1 | 5 km/h |
| 10 | 50 km/h |
| 20 | 100 km/h |
| 32 | 160 km/h |
| 40 | 200 km/h |
| 60 | 300 km/h |
| 70 | 350 km/h |
| 1023 | Speed unknown |

Range: 0–1023 (unsigned 10 bits)

#### M_MODE (§7.4.2.6)

Current ETCS operating mode. See §4.6 for full list. Key values:

| Value | Mode |
|-------|------|
| 0 | FS — Full Supervision |
| 1 | OS — On Sight |
| 2 | SH — Shunting |
| 3 | SR — Staff Responsible |
| 4 | SF — System Failure |
| 8 | NP — No Power |
| 9 | SB — Stand By |

#### M_LEVEL (§7.4.2.7)

Current ETCS supervision level.

| Value | Level |
|-------|-------|
| 0 | Level 0 — no supervision |
| 1 | Level 1 — beacon-based |
| 2 | Level 2 — radio, RBC |
| 3 | Level STM |

For all Level 2 scenarios: M_LEVEL=2.

---

## §7.5.1 — Variable Definitions (Selected)

### D_OL

Distance from the End of Authority to the end of the overlap zone. The train may enter this zone at V_RELEASESPEED.

**Constraint:** `D_OL ≥ V_RELEASESPEED² / (2 × a_emergency)`

Typical emergency deceleration values:
- Category P1 (passenger, high speed): a = 1.2 m/s²
- Category P2 (passenger): a = 1.0 m/s²
- Category F1 (freight): a = 0.6 m/s²

Encoded with Q_SCALE. Unsigned integer.

---

### D_SECTIONTIMERSTOPLOC

Distance from the LRBG to the location where the section timer stops if the train is stopped. The timer may stop (rather than expire) if the train is stationary at or before this location.

Encoded with Q_SCALE. Unsigned integer.

---

### D_STARTOL

Distance from the End of Authority to the start of the overlap zone. Must be ≤ D_OL.

Encoded with Q_SCALE. Unsigned integer.

---

### G_A

Gradient magnitude in per mille (‰). Used in Packet 21 combined with Q_GDIR to specify the signed gradient.

Range: 0–255 (0.0‰ to 255.0‰)

---

### L_SECTION

Length of a Movement Authority section. Encoded with Q_SCALE. Unsigned integer.

The train is authorised to travel L_SECTION distance from the start of the section (previous section's EOA).

---

### L_TRAININT

Train length as an integer, encoded with Q_SCALE. Transmitted when Q_LENGTH ∈ {0, 2}.

---

### M_ACK

Acknowledgement required flag.

| Value | Meaning |
|-------|---------|
| 0 | No acknowledgement required |
| 1 | Driver acknowledgement required |

**By message type:**
- NID_MESSAGE=0 (PositionReport): M_ACK=0
- NID_MESSAGE=3 (MovementAuthority): M_ACK=1 (standard; driver must acknowledge)
- NID_MESSAGE=8 (Acknowledgement): M_ACK=0

---

### N_ITER

Number of iterations in a repeated structure within a message or packet.

- In NID_MESSAGE=3: number of MA sections (1–32)
- In Packet 21: number of gradient segments
- In Packet 27: number of speed change points after the first
- In Packet 72: number of linking entries

Range: 0–32 (unsigned 5 bits)

---

### NID_C

Country/region identifier. 10-bit unsigned integer. Combined with NID_LRBG to form a globally unique balise group identifier.

---

### Q_FRONT

Used in Packet 27 (Static Speed Profile). Specifies which part of the train the speed restriction applies to.

| Value | Meaning |
|-------|---------|
| 0 | Speed applies to train front |
| 1 | Speed applies to train rear |

Standard value: Q_FRONT=0

---

### Q_GDIR

Gradient direction qualifier. Used in Packet 21.

| Value | Meaning |
|-------|---------|
| 0 | Downhill (negative gradient — train gains speed) |
| 1 | Uphill (positive gradient — train loses speed) |

---

### Q_LENGTH

Train length reporting qualifier.

| Value | Meaning |
|-------|---------|
| 0 | Train length transmitted, integrity confirmed — L_TRAININT follows |
| 1 | No train integrity information available |
| 2 | Train length transmitted, integrity not confirmed — L_TRAININT follows |
| 3 | Train length not known |

Standard default for Level 2: Q_LENGTH=1 (no integrity information required for basic MA).

---

### Q_LINKORIENTATION

Used in Packet 72. Expected orientation of the linked balise group.

| Value | Meaning |
|-------|---------|
| 0 | Nominal orientation |
| 1 | Reverse orientation |

---

### Q_LINKREACTION

Used in Packet 72. On-board reaction if a linked balise group is not found within tolerance.

| Value | Meaning |
|-------|---------|
| 0 | Apply emergency brake |
| 1 | Apply service brake |
| 2 | No reaction |

Standard value: Q_LINKREACTION=1 (service brake)

---

### Q_LOCACC

Location accuracy tolerance for linked balise groups (Packet 72). Unsigned integer in metres.

Standard value: Q_LOCACC=12 (12 m tolerance)

---

### Q_NEWCOUNTRY

Cross-border indicator in MA sections and linking entries.

| Value | Meaning |
|-------|---------|
| 0 | Same country/region as previous section — NID_C not transmitted |
| 1 | New country/region — NID_C follows |

Standard value: Q_NEWCOUNTRY=0 (domestic scenarios)

---

### Q_OVERLAP

Overlap present flag in MovementAuthority.

| Value | Meaning |
|-------|---------|
| 0 | No overlap zone — D_STARTOL, T_OL, D_OL not transmitted |
| 1 | Overlap present — D_STARTOL, T_OL, D_OL follow |

---

### Q_SCALE

See §7.4.2.1.

---

### Q_SECTIONTIMER

Section timer present flag. For each section in the MA.

| Value | Meaning |
|-------|---------|
| 0 | No section timer — T_SECTIONTIMER and D_SECTIONTIMERSTOPLOC not transmitted |
| 1 | Section timer active — T_SECTIONTIMER and D_SECTIONTIMERSTOPLOC follow |

---

### T_OL

Overlap timer. Maximum time the train may occupy the overlap zone before the on-board applies emergency brake. In seconds.

---

### T_SECTIONTIMER

Section timer. Maximum time allowed for the train to traverse the section. If the timer expires before the train exits the section, emergency brake is applied.

**Feasibility constraint:** `T_SECTIONTIMER ≥ (L_SECTION / V_max_section_ms) × safety_factor`

Where:
- `V_max_section_ms` = section speed in m/s
- `safety_factor` = 0.5 (allowing the train half the theoretical minimum time as safety margin)

---

### T_TRAIN

Timestamp of the message, in milliseconds, modulo 36,000,000 (10-hour cycle).

Range: 0–35,999,999

This field is set by the RBC or on-board at message creation time. In the pipeline, it is filled by the Instantiator from the session clock.

---

### V_RELEASESPEED

Release speed. The maximum speed at which the train may enter the overlap zone. The on-board supervises that the train does not exceed V_RELEASESPEED when approaching the EOA.

Encoded as km/h. Range: 0–600 km/h.

**Standard values:**
- Normal scenario: 30 km/h
- Emergency stop: 0 km/h (train must stop before EOA)

---

### V_STATIC

Static speed restriction in km/h. Used in Packet 27 to specify the permitted speed at each point along the MA.

Encoded as km/h. Range: 0–600 km/h (0 = stop required).

**Note:** V_STATIC is transmitted in Packet 27, not in the MA core message. However, for the pipeline's simplified section model, V_STATIC is included in section data to represent the effective speed limit.

---

## §8.4.1 — Position Report (NID_MESSAGE = 0)

### Description

The PositionReport is sent by the train's on-board unit to the RBC to report the train's current position, speed, and ETCS state. It is the primary uplink message in ETCS Level 2.

**Direction:** Train → RBC  
**M_ACK:** 0 (no acknowledgement required)  
**Spec ref:** Subset-026 §8.4.1

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| NID_MESSAGE | uint(8) | = 0 |
| L_MESSAGE | uint(10) | Total message length in bits |
| T_TRAIN | uint(32) | Timestamp (ms mod 36,000,000) |
| M_ACK | uint(1) | = 0 |
| NID_LRBG | uint(24) | Reference balise group (NID_C + NID_LRBG) |
| Q_SCALE | uint(2) | Distance/speed resolution |
| D_LRBG | uint(15) | Distance from LRBG in Q_SCALE units |
| Q_DIRLRBG | uint(2) | Direction relative to LRBG |
| Q_LENGTH | uint(2) | Train length reporting mode |
| V_TRAIN | uint(10) | Current speed (5 km/h/bit) |
| D_LBDRBG | uint(15) | Distance from front to rear BG |
| Q_DIRTRAIN | uint(2) | Train movement direction |
| M_MODE | uint(4) | Current ETCS mode |
| M_LEVEL | uint(3) | Current ETCS level |
| NID_LTRBG | uint(8) | Last Train Reference Balise Group |

### Conditional fields

| Field | Condition | Type | Description |
|-------|-----------|------|-------------|
| L_TRAININT | Q_LENGTH ∈ {0, 2} | uint(15) | Train length in Q_SCALE units |

### Validation rules

- Q_SCALE ∈ {0, 1, 2}
- M_MODE ∈ {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14}
- M_LEVEL ∈ {0, 1, 2, 3}
- Q_LENGTH ∈ {0, 1, 2, 3}
- L_TRAININT must be present when Q_LENGTH ∈ {0, 2}
- V_TRAIN ∈ [0, 1023]

---

## §8.4.3 — Movement Authority (NID_MESSAGE = 3)

### Description

The MovementAuthority (MA) is sent by the RBC to grant the train permission to proceed to the End of Authority (EOA). It contains sections defining permitted distances and speeds, and optionally an overlap zone beyond the EOA.

**Direction:** RBC → Train  
**M_ACK:** 1 (driver acknowledgement required)  
**Spec ref:** Subset-026 §8.4.3

### Structure

#### Fixed part

| Field | Type | Description |
|-------|------|-------------|
| NID_MESSAGE | uint(8) | = 3 |
| L_MESSAGE | uint(10) | Total message length in bits |
| T_TRAIN | uint(32) | Timestamp |
| M_ACK | uint(1) | = 1 |
| NID_LRBG | uint(24) | Reference balise group |
| Q_SCALE | uint(2) | Distance resolution |
| N_ITER | uint(5) | Number of MA sections (1–32) |

#### Repeated section block (N_ITER times)

| Field | Type | Condition | Description |
|-------|------|-----------|-------------|
| L_SECTION(i) | uint(15) | always | Section length in Q_SCALE units |
| Q_SECTIONTIMER(i) | uint(1) | always | Section timer flag |
| T_SECTIONTIMER(i) | uint(10) | Q_SECTIONTIMER=1 | Timer value in seconds |
| D_SECTIONTIMERSTOPLOC(i) | uint(15) | Q_SECTIONTIMER=1 | Stop location distance |

#### End of Authority block

| Field | Type | Condition | Description |
|-------|------|-----------|-------------|
| Q_OVERLAP | uint(1) | always | Overlap flag |
| D_STARTOL | uint(15) | Q_OVERLAP=1 | Start of overlap |
| T_OL | uint(10) | Q_OVERLAP=1 | Overlap timer in seconds |
| D_OL | uint(15) | Q_OVERLAP=1 | Overlap distance |
| V_RELEASESPEED | uint(7) | always | Release speed in km/h |

### MA sections

Each section represents a corridor of movement. Sections are ordered from the current train position toward the EOA. The last section ends at the EOA.

- `L_SECTION` defines the length of each section
- `Q_SECTIONTIMER` indicates whether a section timer applies
- Speed restrictions per section are transmitted in Packet 27

### Permitted speed in MA

Speed restrictions are **not** carried in the MA core fields. They are transmitted in:
- **Packet 27 (Static Speed Profile):** overall speed profile
- **Packet 80 (Mode Profile):** for mode changes (e.g., FS→OS)

**Pipeline simplification:** The pipeline bundles V_STATIC into the section data within `scenario_params` for ease of processing. This represents the effective permitted speed for each section.

### Validation rules

- Q_SCALE ∈ {0, 1, 2}
- N_ITER ∈ [1, 32]
- T_SECTIONTIMER must be present when Q_SECTIONTIMER=1
- V_RELEASESPEED ≥ 0
- D_OL must satisfy: `D_OL ≥ V_RELEASESPEED² / (2 × a_emergency)` — see §3.14

---

## §8.4.5 — Acknowledgement (NID_MESSAGE = 8)

### Description

The Acknowledgement is sent by the train to confirm receipt of a message that required driver acknowledgement (M_ACK=1). In the standard Level 2 MA exchange, the Acknowledgement follows the MovementAuthority.

**Direction:** Train → RBC  
**M_ACK:** 0 (no further acknowledgement required)  
**Spec ref:** Subset-026 §8.4.5

### Structure

| Field | Type | Description |
|-------|------|-------------|
| NID_MESSAGE | uint(8) | = 8 |
| L_MESSAGE | uint(10) | Total message length in bits |
| T_TRAIN | uint(32) | Timestamp of the acknowledgement |
| M_ACK | uint(1) | = 0 |
| NID_LRBG | uint(24) | Current reference balise group |
| T_TRAIN_ref | uint(32) | Timestamp from the acknowledged message |

### Usage

- `T_TRAIN_ref` copies the `T_TRAIN` value from the acknowledged message (MA)
- The RBC uses `T_TRAIN_ref` to correlate the acknowledgement with the specific MA instance
- After receiving the Acknowledgement, the on-board transitions to the mode indicated in the MA (typically SR→FS)

### Validation

- Must follow a message with M_ACK=1
- `T_TRAIN_ref` should reference the T_TRAIN of the preceding MA

---

## Packet 21 — Gradient Profile

### Description

Packet 21 is included in a MovementAuthority (NID_MESSAGE=3) to transmit the gradient profile of the track ahead. The on-board unit uses this information to compute accurate braking curves.

**NID_PACKET:** 21  
**Transmitted in:** NID_MESSAGE=3  
**Required when:** Track has non-zero gradients along the MA

### Why gradient matters

The on-board braking model must compensate for gravitational force:
- **Uphill:** braking distance decreases (gravity assists braking)
- **Downhill:** braking distance increases (gravity opposes braking)

Omitting the gradient profile forces the on-board to use conservative assumptions (flat track), which may result in unnecessarily early braking.

### Structure

#### Packet header

| Field | Type | Description |
|-------|------|-------------|
| NID_PACKET | uint(8) | = 21 |
| Q_DIR | uint(2) | Valid direction: 0=nominal, 1=reverse, 2=both |
| L_PACKET | uint(13) | Packet length in bits |
| Q_SCALE | uint(2) | Distance resolution |
| N_ITER | uint(5) | Number of gradient segments |

#### Repeated segment block (N_ITER times)

| Field | Type | Description |
|-------|------|-------------|
| D_GRADIENT(i) | uint(15) | Start distance of segment from LRBG in Q_SCALE units |
| Q_GDIR(i) | uint(1) | 0=downhill, 1=uphill |
| G_A(i) | uint(8) | Gradient magnitude in per mille (0–255) |

### Construction rules

1. First segment always starts at D_GRADIENT[1]=0
2. Each segment's gradient applies from its D_GRADIENT until the next segment begins
3. The last segment's gradient applies until the EOA
4. Flat track: single segment with G_A=0
5. All segments must collectively cover the entire MA distance

### Example: +8‰ uphill for 1000m then flat to 2500m EOA

```json
{
  "N_ITER": 2,
  "segments": [
    {"D_GRADIENT": 0, "Q_GDIR": 1, "G_A": 8},
    {"D_GRADIENT": 1000, "Q_GDIR": 0, "G_A": 0}
  ]
}
```

---

## Packet 27 — Static Speed Profile

### Description

Packet 27 is included in a MovementAuthority to specify the permitted speed at each point along the route. It allows multiple speed zones within a single MA.

**NID_PACKET:** 27  
**Transmitted in:** NID_MESSAGE=3  
**Required when:** Speed changes along the MA (multiple sections with different V_STATIC)

### Structure

#### Packet header

| Field | Type | Description |
|-------|------|-------------|
| NID_PACKET | uint(8) | = 27 |
| Q_DIR | uint(2) | Valid direction |
| L_PACKET | uint(13) | Packet length in bits |
| Q_SCALE | uint(2) | Distance resolution |
| V_STATIC | uint(7) | Initial speed (applies from the start of the MA) |
| N_ITER | uint(5) | Number of subsequent speed change points |

#### Repeated speed zone block (N_ITER times)

| Field | Type | Description |
|-------|------|-------------|
| D_STATIC(i) | uint(15) | Distance from LRBG where new speed begins |
| V_STATIC(i) | uint(7) | New permitted speed in km/h |
| Q_FRONT(i) | uint(1) | 0=front of train, 1=rear of train |

### Construction rules

1. The top-level `V_STATIC` is the initial speed, applying from D=0
2. Each entry in the repeated block is a speed change point
3. For N sections with different speeds: top-level V_STATIC = section[0].v_max, then N-1 entries for sections [1..N-1]
4. `D_STATIC(i)` = cumulative distance to the start of section[i], measured from LRBG

### Example: 200 km/h for 1500m then 120 km/h for 800m

```json
{
  "V_STATIC": 200,
  "N_ITER": 1,
  "speed_zones": [
    {"D_STATIC": 1500, "V_STATIC": 120, "Q_FRONT": 0}
  ]
}
```

### When Packet 27 may be omitted

If all sections in the MA have the same `v_max_kmh`, Packet 27 may be omitted. The on-board uses the speed limit from track equipment (balise groups) or the national value.

---

## Packet 72 — Linking

### Description

Packet 72 provides "linking" information — a list of expected balise groups along the train's route. The on-board monitors that these BGs appear in the expected sequence and position.

**NID_PACKET:** 72  
**Transmitted in:** NID_MESSAGE=3  
**Required when:** Route has known balise groups that should be encountered

### Purpose

Linking serves as an integrity check:
- If a linked BG is encountered outside its expected location window: the on-board notes an inconsistency
- If a linked BG is **not found** at all: the on-board reacts according to Q_LINKREACTION

This helps detect misrouting (wrong track) and position errors.

### Structure

#### Packet header

| Field | Type | Description |
|-------|------|-------------|
| NID_PACKET | uint(8) | = 72 |
| Q_DIR | uint(2) | Valid direction |
| L_PACKET | uint(13) | Packet length in bits |
| Q_SCALE | uint(2) | Distance resolution |
| N_ITER | uint(5) | Number of linking entries |

#### Repeated linking entry (N_ITER times)

| Field | Type | Condition | Description |
|-------|------|-----------|-------------|
| D_LINK(i) | uint(15) | always | Distance to expected BG from LRBG |
| Q_NEWCOUNTRY(i) | uint(1) | always | 0=same country, 1=new country |
| NID_C(i) | uint(10) | Q_NEWCOUNTRY=1 | Country code |
| NID_BG(i) | uint(14) | always | Balise group identifier |
| Q_LINKORIENTATION(i) | uint(1) | always | 0=nominal, 1=reverse |
| Q_LINKREACTION(i) | uint(2) | always | Reaction if BG not found |
| Q_LOCACC(i) | uint(6) | always | Location accuracy tolerance in metres |

### Default values (from instantiator defaults)

| Field | Default |
|-------|---------|
| Q_NEWCOUNTRY | 0 |
| Q_LINKORIENTATION | 1 |
| Q_LINKREACTION | 1 |
| Q_LOCACC | 12 |

---

## §3.14 — Overlap

### Purpose

The overlap is a protected zone **beyond** the End of Authority. It provides an additional safety buffer: the train may enter the overlap at V_RELEASESPEED, but the RBC guarantees that no conflicting movement exists in the overlap zone.

### Parameters

| Parameter | Description |
|-----------|-------------|
| D_STARTOL | Distance from EOA to start of overlap |
| D_OL | Full overlap distance from EOA |
| T_OL | Overlap timer — if train enters and doesn't clear within T_OL: emergency brake |
| V_RELEASESPEED | Maximum speed when entering overlap |

### Braking distance constraint

The overlap must be long enough for the train to stop from V_RELEASESPEED:

```
D_OL ≥ V_RELEASESPEED² / (2 × a_emergency)
```

| Category | a_emergency (m/s²) | V_release=30 km/h min D_OL | V_release=20 km/h min D_OL |
|----------|-------------------|--------------------------|--------------------------|
| P1 | 1.2 | 28.9 m | 12.9 m |
| P2 | 1.0 | 34.7 m | 15.4 m |
| F1 | 0.6 | 57.9 m | 25.7 m |

**Validation rule (KINE_OVERLAP_SHORT_FOR_RELEASE_SPEED):** D_OL below the computed minimum triggers a WARNING (not an error, as it may be intentional in some scenarios).

---

## §7.5.2 — Train Category and Speed Limits

### Train categories in this pipeline

| Category | Max Speed | a_emergency | a_typical | Notes |
|----------|-----------|-------------|-----------|-------|
| P1 | 350 km/h | 1.2 m/s² | 0.9 m/s² | High-speed passenger |
| P2 | 200 km/h | 1.0 m/s² | 0.7 m/s² | Conventional passenger |
| F1 | 140 km/h | 0.6 m/s² | 0.4 m/s² | Freight |

**Validation rule (KINE_SPEED_EXCEEDS_CATEGORY_MAX):** V_STATIC in any MA section exceeding the category maximum raises an ERROR.

---

## Message Interaction Summary

### Standard MA Cycle (Level 2)

```
Train → RBC  : NID_MESSAGE=0  PositionReport  (M_MODE=SR)
RBC   → Train: NID_MESSAGE=3  MovementAuthority  (M_ACK=1)
               [Optional Packet 21 — Gradient Profile]
               [Optional Packet 27 — Static Speed Profile]
               [Optional Packet 72 — Linking]
Train → RBC  : NID_MESSAGE=8  Acknowledgement
Train → RBC  : NID_MESSAGE=0  PositionReport  (M_MODE=FS)
```

### Session Establishment + First MA

```
Train → RBC  : NID_MESSAGE=0  PositionReport  (M_MODE=SB)  ← power-on
               [radio session establishment]
Train → RBC  : NID_MESSAGE=0  PositionReport  (M_MODE=SR)  ← session active
RBC   → Train: NID_MESSAGE=3  MovementAuthority  (M_ACK=1)
Train → RBC  : NID_MESSAGE=8  Acknowledgement
Train → RBC  : NID_MESSAGE=0  PositionReport  (M_MODE=FS)
```

### Emergency Stop

```
Train → RBC  : NID_MESSAGE=0  PositionReport  (M_MODE=FS, V_TRAIN>0)
RBC   → Train: NID_MESSAGE=3  MovementAuthority  (V_RELEASESPEED=0, short L_SECTION, V_STATIC=0)
Train → RBC  : NID_MESSAGE=8  Acknowledgement
Train → RBC  : NID_MESSAGE=0  PositionReport  (M_MODE=FS, V_TRAIN=0)
```

---

## Cross-Message Consistency Rules

### LRBG Consistency

All messages in the same session that reference NID_LRBG should reference the same LRBG unless the train has passed a new balise group (in which case the new LRBG supersedes the old).

Error code: `CROSS_LRBG_INCONSISTENCY`

### MA Acknowledgement Pairing

Every MA with M_ACK=1 must be followed by an Acknowledgement (NID_MESSAGE=8). An MA without a subsequent Acknowledgement in the sequence is an error.

Error code: `CROSS_ACK_MISSING_FOR_MA`

### Q_SCALE Session Consistency

Q_SCALE should be consistent across all messages in the same session. Different Q_SCALE values in different messages within the same session may cause position computation errors.

Error code: `CROSS_QSCALE_INCONSISTENCY`

---

## Reference: Numeric Encoding Examples

### Q_SCALE = 1 (1 m resolution) examples

| Physical distance | Encoded value |
|-----------------|--------------|
| 0 m | 0 |
| 100 m | 100 |
| 1000 m | 1000 |
| 2000 m | 2000 |
| 32766 m | 32766 (maximum) |

### V_TRAIN encoding (5 km/h resolution)

| Speed (km/h) | Encoded value |
|-------------|--------------|
| 0 | 0 |
| 5 | 1 |
| 50 | 10 |
| 100 | 20 |
| 160 | 32 |
| 200 | 40 |
| 350 | 70 |

### T_SECTIONTIMER feasibility formula

For a section of length L (metres) and maximum speed V (m/s):

```
T_minimum = (L / V) × safety_factor
```

With safety_factor=0.5 (50% of theoretical minimum travel time):

| L_SECTION | V_STATIC | T_minimum |
|-----------|---------|-----------|
| 1000 m | 200 km/h (55.6 m/s) | 9.0 s |
| 1000 m | 160 km/h (44.4 m/s) | 11.3 s |
| 500 m | 100 km/h (27.8 m/s) | 9.0 s |
| 2000 m | 160 km/h (44.4 m/s) | 22.5 s |
