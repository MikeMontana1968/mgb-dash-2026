# MGB Dash 2026 — Vehicle Physical Specifications

## Car
- **Make/Model:** 1970 MGB US convertible
- **Windshield wipers:** Three-wiper model

## Tires
- **Tire diameter:** 26.5"

## Drivetrain
- **Final differential gear ratio:** 3.909

### Transmission Gear Ratios (4-speed manual)

| Gear    | Ratio |
|---------|-------|
| First   | 3.41  |
| Second  | 2.166 |
| Third   | 1.38  |
| Fourth  | 1.00  |
| Reverse | 3.09  |

### Motor RPM by Speed and Gear

```
Motor RPM = Speed × (63360 / (π × TireDia)) / 60 × FinalDrive × GearRatio
         = Speed × 49.59 × GearRatio
```

| Speed    | 1st (3.41) | 2nd (2.166) | 3rd (1.38) | 4th (1.00) | Ideal Gear |
|----------|-----------|-------------|-----------|-----------|------------|
| 20 mph   | 3,382     | 2,148       | 1,369     | 992       | 2nd        |
| 30 mph   | 5,073     | 3,222       | 2,053     | 1,488     | 3rd        |
| 40 mph   | 6,764     | 4,297       | 2,737     | 1,984     | 4th        |
| 50 mph   | 8,455     | 5,371       | 3,422     | 2,479     | 4th        |
| 60 mph   | 10,146    | 6,445       | 4,106     | 2,975     | 4th        |

Ideal gear selects the highest gear keeping the Leaf EM57 motor above ~1,000 RPM.
The EM57 produces peak torque (254 Nm) from 0–3,008 RPM; peak power (80 kW) at ~9,795 RPM.

## Speedometer
- **Stepper motor:** 28BYJ-48
- **Driver board:** ULN2003
