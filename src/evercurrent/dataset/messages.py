"""Synthetic Slack message dataset for an AMR robotics team.

Contains 300+ messages across 8 channels with engineer-register prose:
terse, technical, cross-referential, jargon-dense. Includes thread
depth variety from 2-message exchanges to 30+ message narrative arcs.

Messages span two days of Slack traffic during late EVT / early DVT
for an autonomous mobile robot (AMR) development program.
"""

from __future__ import annotations

from evercurrent.dataset.schema import SlackMessage, SlackReaction


def _msg(
    ts: str,
    channel: str,
    user: str,
    text: str,
    *,
    thread: str | None = None,
    reactions: list[SlackReaction] | None = None,
) -> SlackMessage:
    """Build a SlackMessage with compact syntax.

    Args:
        ts: Message timestamp (unique ID).
        channel: Channel name with # prefix.
        user: User ID (e.g. 'U001').
        text: Message text content.
        thread: Parent thread timestamp, None for top-level.
        reactions: Optional list of reactions.

    Returns:
        A SlackMessage instance.
    """
    return SlackMessage(
        message_ts=ts,
        thread_ts=thread,
        channel=channel,
        user_id=user,
        text=text,
        reactions=reactions or [],
    )


def _r(name: str, users: list[str]) -> SlackReaction:
    """Build a SlackReaction with compact syntax.

    Args:
        name: Emoji name.
        users: List of user IDs who reacted.

    Returns:
        A SlackReaction instance.
    """
    return SlackReaction(name=name, users=users)


def _build_chassis_messages() -> list[SlackMessage]:
    """Build messages for #chassis-design channel."""
    msgs: list[SlackMessage] = []
    # Thread 1: Snap-fit retention force failure (deep thread, 15 msgs)
    t1 = "1711900000.000001"
    msgs.append(
        _msg(
            t1,
            "#chassis-design",
            "U001",
            "Pull-out force on snap fit measured at 12N, spec is 15N min. "
            "Third iteration and we're still under spec.",
            reactions=[_r("eyes", ["U008", "U020"])],
        )
    )
    msgs.append(
        _msg(
            "1711900060.000002",
            "#chassis-design",
            "U008",
            "Did you test with the updated rib geometry from rev C? "
            "I pushed the STEP file yesterday.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900120.000003",
            "#chassis-design",
            "U001",
            "Yes, rev C. The issue is the draft angle on the retention "
            "hook — 3deg is too aggressive for PA66-GF30.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900180.000004",
            "#chassis-design",
            "U020",
            "What if we go to 1.5deg draft and add a barb feature? Worked on the sensor bracket.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900240.000005",
            "#chassis-design",
            "U001",
            "Barb adds undercut complexity for the tool. @U013 can "
            "the mold vendor handle that with a side action?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900300.000006",
            "#chassis-design",
            "U013",
            "Side action adds 3 weeks to tool lead time and ~$4k. "
            "Alternative: lifter pin, but wall thickness needs 2.5mm min.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900360.000007",
            "#chassis-design",
            "U001",
            "Current wall is 2.0mm. Going to 2.5 means re-running "
            "the FEA for drop test compliance.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900420.000008",
            "#chassis-design",
            "U008",
            "I can run the drop sim tonight. What's the impact energy spec — 1.5J at 1m?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900480.000009",
            "#chassis-design",
            "U001",
            "Correct, 1.5J free fall from 1m onto concrete per IEC 62368. "
            "Corner impact case is usually the limiting factor.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900540.000010",
            "#chassis-design",
            "U020",
            "For what it's worth, the sensor bracket passed at 2.2mm "
            "wall with the barb. Different load path though.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900600.000011",
            "#chassis-design",
            "U013",
            "Talked to the mold vendor. Lifter pin is feasible at 2.5mm "
            "wall. They need the updated Parasolid by Friday.",
            thread=t1,
            reactions=[_r("thumbsup", ["U001", "U008"])],
        )
    )
    msgs.append(
        _msg(
            "1711900660.000012",
            "#chassis-design",
            "U001",
            "Decision: go with 2.5mm wall + lifter pin. @U008 run "
            "drop sim, I'll update the Parasolid. Target: Thursday EOD.",
            thread=t1,
            reactions=[_r("white_check_mark", ["U008", "U013", "U020"])],
        )
    )
    msgs.append(
        _msg(
            "1711900720.000013",
            "#chassis-design",
            "U008",
            "Drop sim results: 2.5mm wall passes at 1.8J — 20% margin "
            "above spec. Corner impact stress at 85% of yield.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900780.000014",
            "#chassis-design",
            "U001",
            "Good margin. Parasolid updated and uploaded. @U013 please "
            "forward to vendor for T1 tooling quote.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711900840.000015",
            "#chassis-design",
            "U013",
            "Sent. Vendor confirms 6 week lead time from PO. I'll get "
            "the quote to Elena for approval by Monday.",
            thread=t1,
            reactions=[_r("rocket", ["U001"])],
        )
    )

    # Thread 2: Short exchange about chassis weight budget
    t2 = "1711910000.000016"
    msgs.append(
        _msg(
            t2,
            "#chassis-design",
            "U020",
            "Updated mass properties for rev C chassis: 4.73kg. Budget is 4.5kg. We're 230g over.",
        )
    )
    msgs.append(
        _msg(
            "1711910060.000017",
            "#chassis-design",
            "U001",
            "The 2.5mm wall change adds ~80g. Where else can we "
            "pocket? The motor mount plate has material to remove.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711910120.000018",
            "#chassis-design",
            "U008",
            "Topology optimization on the motor mount showed 150g "
            "savings possible. Sending the optimized STEP now.",
            thread=t2,
            reactions=[_r("thumbsup", ["U001", "U020"])],
        )
    )

    # Thread 3: Magnesium housing discussion (BURIED SIGNAL #1 setup)
    t3 = "1711920000.000019"
    msgs.append(
        _msg(
            t3,
            "#chassis-design",
            "U013",
            "FYI the new aluminum extrusion supplier quoted 30% lower "
            "than current. But we should also consider magnesium for the "
            "main housing — 35% weight savings at similar strength.",
        )
    )
    msgs.append(
        _msg(
            "1711920060.000020",
            "#chassis-design",
            "U001",
            "Magnesium is interesting for the weight target. What's "
            "the corrosion protection story? We need IP54.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711920120.000021",
            "#chassis-design",
            "U013",
            "Micro-arc oxidation coating handles IP54. But the real "
            "question is supply chain — mag die casting has longer lead "
            "times and fewer qualified vendors.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711920180.000022",
            "#chassis-design",
            "U001",
            "Let's prototype the housing in magnesium for DVT. If it "
            "works, we switch. If not, we stay aluminum and eat the "
            "weight penalty. @U013 can you get vendor quotes?",
            thread=t3,
            reactions=[_r("thumbsup", ["U013", "U020", "U010"])],
        )
    )
    msgs.append(
        _msg(
            "1711920240.000023",
            "#chassis-design",
            "U013",
            "On it. I'll need 2-3 weeks for vendor qualification. "
            "This will affect the supply chain timeline if we go mag.",
            thread=t3,
        )
    )

    # Short standalone messages
    msgs.append(
        _msg(
            "1711930000.000024",
            "#chassis-design",
            "U009",
            "Chassis DVT test plan review meeting moved to Thursday 2pm. Updated invite sent.",
        )
    )
    msgs.append(
        _msg(
            "1711930060.000025",
            "#chassis-design",
            "U015",
            "Reminder: chassis assembly torque audit is next week. "
            "Please have all fastener specs documented in the BOM.",
            reactions=[_r("eyes", ["U001", "U008", "U020"])],
        )
    )
    return msgs


def _build_drivetrain_messages() -> list[SlackMessage]:
    """Build messages for #drivetrain channel."""
    msgs: list[SlackMessage] = []

    # Thread 1: Motor torque spec change (medium thread, 10 msgs)
    t1 = "1711901000.000100"
    msgs.append(
        _msg(
            t1,
            "#drivetrain",
            "U002",
            "Load testing results are in. Peak torque demand is 3.1Nm, "
            "not 2.5Nm as originally spec'd. The additional friction from "
            "the new wheel compound is higher than modeled.",
            reactions=[_r("rotating_light", ["U012", "U004"])],
        )
    )
    msgs.append(
        _msg(
            "1711901060.000101",
            "#drivetrain",
            "U012",
            "3.1Nm at what duty cycle? Continuous or peak? The Maxon "
            "EC-i 40 is rated 2.83Nm continuous, 4.2Nm peak.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711901120.000102",
            "#drivetrain",
            "U002",
            "It's a 15s peak during obstacle climbing. Thermal margin "
            "on the motor is the concern — @U003 can you check the "
            "thermal derating at 3.1Nm continuous equiv?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711901180.000103",
            "#drivetrain",
            "U003",
            "Running the thermal model now. At 3.1Nm equiv the winding "
            "temp hits 142C — max rated is 155C. Only 13C margin.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711901240.000104",
            "#drivetrain",
            "U002",
            "That's tight. Options: (1) upsize to EC-i 52, (2) improve "
            "thermal path from motor to chassis, (3) reduce friction.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711901300.000105",
            "#drivetrain",
            "U012",
            "EC-i 52 adds 180g per motor, 720g total for 4 wheels. "
            "That blows the mass budget. Option 2 is cheaper.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711901360.000106",
            "#drivetrain",
            "U004",
            "From power side: 3.1Nm at 200rpm needs ~65W per motor. "
            "Current driver board handles 80W max. We're fine on power.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711901420.000107",
            "#drivetrain",
            "U002",
            "Decision: update torque spec to 3.1Nm. Keep EC-i 40 "
            "motor, improve thermal interface between motor housing "
            "and chassis heat sink. @U003 own the thermal fix.",
            thread=t1,
            reactions=[
                _r("white_check_mark", ["U012", "U003", "U004"]),
            ],
        )
    )
    msgs.append(
        _msg(
            "1711901480.000108",
            "#drivetrain",
            "U003",
            "Accepted. I'll spec a thermal pad with >3 W/mK between "
            "motor flange and chassis mount. Should drop winding temp "
            "by 20-25C.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711901540.000109",
            "#drivetrain",
            "U002",
            "Good. Also updating the gearbox input torque spec. The "
            "harmonic drive needs to be re-validated at 3.1Nm input. "
            "@U012 please run the lifetime calc.",
            thread=t1,
        )
    )

    # Thread 2: Gearbox bearing noise (short)
    t2 = "1711911000.000110"
    msgs.append(
        _msg(
            t2,
            "#drivetrain",
            "U012",
            "Hearing intermittent bearing noise from wheel 3 during "
            "endurance testing. ~2kHz whine above 150rpm.",
        )
    )
    msgs.append(
        _msg(
            "1711911060.000111",
            "#drivetrain",
            "U002",
            "Pull it for teardown. Could be preload issue from the "
            "last assembly. Check bearing seat concentricity.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711911120.000112",
            "#drivetrain",
            "U012",
            "Teardown complete. Bearing inner race had 0.02mm step "
            "from shaft tolerance. Reshimming fixed it. Updating "
            "assembly procedure to add runout check.",
            thread=t2,
            reactions=[_r("thumbsup", ["U002"])],
        )
    )

    # Standalone messages
    msgs.append(
        _msg(
            "1711921000.000113",
            "#drivetrain",
            "U002",
            "Harmonic drive lifetime calc done: 15,000 hours at 3.1Nm "
            "input. Spec requires 10,000. Margin is adequate.",
            reactions=[_r("white_check_mark", ["U010"])],
        )
    )
    msgs.append(
        _msg(
            "1711921060.000114",
            "#drivetrain",
            "U008",
            "The new motor mount topology-optimized design clears the "
            "drivetrain envelope. No interference with gearbox.",
        )
    )
    return msgs


def _build_thermal_messages() -> list[SlackMessage]:
    """Build messages for #thermal-management channel."""
    msgs: list[SlackMessage] = []

    # Thread 1: Thermal interface material investigation
    # (BURIED SIGNAL #2 setup — root cause from motor overheating)
    t1 = "1711902000.000200"
    msgs.append(
        _msg(
            t1,
            "#thermal-management",
            "U003",
            "Motor 2 hit thermal shutdown during the 4-hour endurance "
            "run. Winding temp reached 158C, limit is 155C. Looking at "
            "the thermal interface between motor and chassis.",
            reactions=[_r("rotating_light", ["U002", "U018"])],
        )
    )
    msgs.append(
        _msg(
            "1711902060.000201",
            "#thermal-management",
            "U018",
            "What TIM are you using? The Bergquist Gap Pad 5000S35 "
            "we spec'd is 3.5 W/mK. Should be sufficient.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711902120.000202",
            "#thermal-management",
            "U003",
            "That's what's on the BOM but I'm measuring actual thermal "
            "resistance and it's 2x what the datasheet says. Checking "
            "if the pad is making full contact.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711902180.000203",
            "#thermal-management",
            "U003",
            "Found it. The motor flange has a 0.3mm step that creates "
            "an air gap under the thermal pad. The pad can't conform "
            "to the step — it's too stiff.",
            thread=t1,
            reactions=[_r("eyes", ["U001", "U002", "U018"])],
        )
    )
    msgs.append(
        _msg(
            "1711902240.000204",
            "#thermal-management",
            "U018",
            "Switch to Fujipoly XR-Um? It's softer (Shore 00-45 vs "
            "Shore 00-65) and conforms to surface irregularities. "
            "5.0 W/mK conductivity too.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711902300.000205",
            "#thermal-management",
            "U003",
            "Good call. But the root cause is actually the chassis "
            "machining — that 0.3mm step shouldn't be there. @U001 "
            "can you check the chassis drawing tolerance?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711902360.000206",
            "#thermal-management",
            "U001",
            "Checked. The motor flange mounting face is spec'd at "
            "0.1mm flatness. The step is a machining defect on this "
            "prototype. Production tooling won't have this issue.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711902420.000207",
            "#thermal-management",
            "U003",
            "OK so for DVT prototypes we need the softer TIM to "
            "handle surface variation. For production we can go back "
            "to the Gap Pad. Adding both to the BOM with a phase note.",
            thread=t1,
            reactions=[
                _r("thumbsup", ["U001", "U018", "U002"]),
            ],
        )
    )
    msgs.append(
        _msg(
            "1711902480.000208",
            "#thermal-management",
            "U003",
            "Also flagging: this thermal issue affects all 4 motors, "
            "not just motor 2. The chassis mounting faces on all "
            "prototypes likely have the same machining variation.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711902540.000209",
            "#thermal-management",
            "U002",
            "Confirming — motor 4 showed elevated temps too (148C) "
            "during the same test. Was about to hit shutdown.",
            thread=t1,
        )
    )

    # Thread 2: Battery thermal management (short)
    t2 = "1711912000.000210"
    msgs.append(
        _msg(
            t2,
            "#thermal-management",
            "U018",
            "Battery pack temp during fast charge: 42C peak, 35C "
            "steady state. Spec limit is 45C. Adequate margin but "
            "worth monitoring as ambient temp increases.",
        )
    )
    msgs.append(
        _msg(
            "1711912060.000211",
            "#thermal-management",
            "U003",
            "What ambient are you testing at? If that's 22C lab temp, "
            "we'll be closer to limit in a 35C warehouse.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711912120.000212",
            "#thermal-management",
            "U018",
            "22C ambient. Good point — I'll add 35C ambient test to "
            "the DVT thermal validation matrix.",
            thread=t2,
        )
    )

    # Thread 3: Cooling fan noise
    t3 = "1711922000.000213"
    msgs.append(
        _msg(
            t3,
            "#thermal-management",
            "U015",
            "QA flagged cooling fan noise at 4200rpm. Measured 62dBA "
            "at 1m. Product spec is 55dBA max. Need fix before DVT.",
        )
    )
    msgs.append(
        _msg(
            "1711922060.000214",
            "#thermal-management",
            "U003",
            "That's the Sunon MF40201V2. We can drop to 3000rpm and "
            "still meet thermal targets if we improve the duct design. "
            "Working on CFD sim.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711922120.000215",
            "#thermal-management",
            "U015",
            "Need the fix validated before Thursday's DVT readiness "
            "review. Can you have sim results by then?",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711922180.000216",
            "#thermal-management",
            "U003",
            "Yes, running overnight. Will post results tomorrow AM.",
            thread=t3,
        )
    )
    return msgs


def _build_power_messages() -> list[SlackMessage]:
    """Build messages for #power-systems channel."""
    msgs: list[SlackMessage] = []

    # Thread 1: Battery BMS firmware issue
    t1 = "1711903000.000300"
    msgs.append(
        _msg(
            t1,
            "#power-systems",
            "U004",
            "BMS is reporting 8% SOC error vs coulomb counting. "
            "The voltage-based estimation drifts significantly below "
            "20% SOC. Need to calibrate the OCV-SOC lookup table.",
        )
    )
    msgs.append(
        _msg(
            "1711903060.000301",
            "#power-systems",
            "U018",
            "Which cell chemistry? The LFP cells have a very flat "
            "voltage curve in the 20-80% range which makes voltage-"
            "based SOC unreliable.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711903120.000302",
            "#power-systems",
            "U004",
            "NMC 21700. The curve isn't flat but the BMS ADC resolution "
            "at 12-bit is only 1.2mV/LSB. Need to go to 16-bit or use "
            "the coulomb counter as primary below 20%.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711903180.000303",
            "#power-systems",
            "U014",
            "The BMS MCU has a 16-bit SAR ADC on channel 2 that's "
            "currently unused. I can remap the voltage sense to that "
            "channel in firmware. ~2 hours of work.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711903240.000304",
            "#power-systems",
            "U004",
            "Do it. That gives us 0.075mV/LSB which is plenty. "
            "@U014 please also add the hybrid estimator: coulomb "
            "counting primary below 20%, voltage-based above.",
            thread=t1,
            reactions=[_r("thumbsup", ["U014", "U018"])],
        )
    )

    # Thread 2: Motor driver thermal event
    t2 = "1711913000.000305"
    msgs.append(
        _msg(
            t2,
            "#power-systems",
            "U004",
            "Motor driver MOSFET junction temp hit 145C during peak "
            "load. Absolute max is 150C. Adding a heatsink to the "
            "driver board PCB.",
        )
    )
    msgs.append(
        _msg(
            "1711913060.000306",
            "#power-systems",
            "U012",
            "Is that with or without the conformal coating? The coating adds thermal resistance.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711913120.000307",
            "#power-systems",
            "U004",
            "Without coating. With coating it'll be worse. Need to "
            "either increase copper pour area or add thermal vias "
            "under the MOSFET pad.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711913180.000308",
            "#power-systems",
            "U004",
            "Updated PCB layout with 25 thermal vias under each "
            "MOSFET. Simulated Tj drops to 128C. Sending to fab.",
            thread=t2,
            reactions=[_r("white_check_mark", ["U012", "U010"])],
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1711923000.000309",
            "#power-systems",
            "U018",
            "Battery cycle test #50 complete. Capacity retention at "
            "97.2%. Datasheet claims 96% at 50 cycles. Tracking well.",
        )
    )
    msgs.append(
        _msg(
            "1711923060.000310",
            "#power-systems",
            "U004",
            "Power budget updated: total system draw is 285W peak, "
            "180W nominal. Battery provides 45 min runtime at nominal. "
            "Meets the 30 min spec with 50% margin.",
        )
    )
    return msgs


def _build_sensor_messages() -> list[SlackMessage]:
    """Build messages for #sensors channel."""
    msgs: list[SlackMessage] = []

    # Thread 1: LIDAR calibration
    t1 = "1711904000.000400"
    msgs.append(
        _msg(
            t1,
            "#sensors",
            "U016",
            "LIDAR point cloud has 2.3cm RMS error at 5m range. "
            "Spec is <1cm. Recalibrating the intrinsic parameters.",
        )
    )
    msgs.append(
        _msg(
            "1711904060.000401",
            "#sensors",
            "U005",
            "Are you using the factory calibration or our custom "
            "procedure? The factory cal drifts with temperature.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711904120.000402",
            "#sensors",
            "U016",
            "Factory cal. Good catch — lab was 28C, calibrated at "
            "22C. The APD gain drifts with temp. Running our thermal "
            "compensation routine.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711904180.000403",
            "#sensors",
            "U016",
            "With thermal compensation: 0.8cm RMS at 5m. Meets spec. "
            "Adding thermal comp to the boot sequence.",
            thread=t1,
            reactions=[_r("tada", ["U005", "U006"])],
        )
    )
    msgs.append(
        _msg(
            "1711904240.000404",
            "#sensors",
            "U005",
            "Nice. Make sure the IMU temp sensor feeds into the comp "
            "algorithm — it's closer to the LIDAR than the board sensor.",
            thread=t1,
        )
    )

    # Thread 2: Encoder resolution (short)
    t2 = "1711914000.000405"
    msgs.append(
        _msg(
            t2,
            "#sensors",
            "U005",
            "Wheel encoder resolution at 4096 CPR gives 0.087mm per "
            "count. Position accuracy requirement is 0.5mm. Fine.",
        )
    )
    msgs.append(
        _msg(
            "1711914060.000406",
            "#sensors",
            "U006",
            "What's the max count rate? At top speed the encoder "
            "output is ~200kHz. The MCU timer capture can handle it?",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711914120.000407",
            "#sensors",
            "U005",
            "Yes, using quadrature decoder hardware. No CPU overhead.",
            thread=t2,
        )
    )

    # Thread 3: Camera integration
    t3 = "1711924000.000408"
    msgs.append(
        _msg(
            t3,
            "#sensors",
            "U016",
            "Front camera FOV measured at 118 deg horizontal. Spec "
            "is 120 min. Edge distortion is higher than expected — "
            "barrel at 4.2% vs 3% spec.",
        )
    )
    msgs.append(
        _msg(
            "1711924060.000409",
            "#sensors",
            "U005",
            "Can we correct in software? The ISP has a dewarping "
            "block that handles up to 5% barrel.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711924120.000410",
            "#sensors",
            "U016",
            "Yes, tested the ISP dewarp. Corrected image is clean. "
            "Effective FOV after correction is 116 deg. Marginal.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711924180.000411",
            "#sensors",
            "U005",
            "116 is below 120 spec. Can we accept 116 or do we need "
            "a wider lens? @U010 need a decision.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711924240.000412",
            "#sensors",
            "U010",
            "What's the operational impact of 116 vs 120? If it's "
            "just edge coverage we can probably accept for DVT.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711924300.000413",
            "#sensors",
            "U016",
            "4 deg less coverage means 0.35m blind spot at 5m range "
            "on each side. Acceptable for warehouse ops, marginal for "
            "outdoor. Recommend accept for DVT, fix for PVT.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711924360.000414",
            "#sensors",
            "U010",
            "Agreed. Accept 116 for DVT. Log it as a PVT action item. "
            "@U005 please track in the sensor validation matrix.",
            thread=t3,
            reactions=[_r("white_check_mark", ["U005", "U016"])],
        )
    )
    return msgs


def _build_firmware_messages() -> list[SlackMessage]:
    """Build messages for #firmware channel."""
    msgs: list[SlackMessage] = []

    # Thread 1: FPGA timing closure (BURIED SIGNAL #3 setup)
    t1 = "1711905000.000500"
    msgs.append(
        _msg(
            t1,
            "#firmware",
            "U006",
            "FPGA timing closure failing on the motor control path. "
            "Setup violation of 1.2ns on the PWM output register. "
            "Need to pipeline the output stage.",
        )
    )
    msgs.append(
        _msg(
            "1711905060.000501",
            "#firmware",
            "U014",
            "What clock frequency? If it's the 100MHz domain we can "
            "add a register stage without affecting PWM latency.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711905120.000502",
            "#firmware",
            "U006",
            "200MHz motor control clock. Adding a pipeline stage means "
            "5ns additional latency. The control loop can tolerate it "
            "— sample rate is 20kHz so 5ns is negligible.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711905180.000503",
            "#firmware",
            "U006",
            "Pipeline stage added. Timing clean now at 200MHz with "
            "0.8ns positive slack. Bitstream rebuilt and tested.",
            thread=t1,
            reactions=[_r("thumbsup", ["U014"])],
        )
    )
    msgs.append(
        _msg(
            "1711905240.000504",
            "#firmware",
            "U014",
            "BTW the FPGA we're using (Artix-7 XC7A35T) is showing "
            "12 week lead time from Digikey. Was 4 weeks last month. "
            "@U007 @U017 heads up on supply.",
            thread=t1,
            reactions=[_r("rotating_light", ["U007", "U017"])],
        )
    )
    msgs.append(
        _msg(
            "1711905300.000505",
            "#firmware",
            "U006",
            "12 weeks is a problem. We need 50 units for DVT builds "
            "in 8 weeks. Can we get allocation from our distributor?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711905360.000506",
            "#firmware",
            "U017",
            "Checking with Arrow now. They sometimes have stock the "
            "web doesn't show. Will update by end of day.",
            thread=t1,
        )
    )

    # Thread 2: Bootloader update mechanism
    t2 = "1711915000.000507"
    msgs.append(
        _msg(
            t2,
            "#firmware",
            "U006",
            "Bootloader v2.1 ready for testing. Added CRC32 validation "
            "on firmware images and fallback to golden image on 3 "
            "consecutive boot failures.",
        )
    )
    msgs.append(
        _msg(
            "1711915060.000508",
            "#firmware",
            "U014",
            "Does the golden image get updated during OTA? We need to "
            "keep it as a known-good fallback.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711915120.000509",
            "#firmware",
            "U006",
            "No, golden image is write-protected in flash. Only the "
            "A/B partitions are OTA-updatable. Golden is factory-"
            "programmed and never touched.",
            thread=t2,
            reactions=[_r("white_check_mark", ["U014"])],
        )
    )

    # Thread 3: MCU memory usage
    t3 = "1711925000.000510"
    msgs.append(
        _msg(
            t3,
            "#firmware",
            "U014",
            "MCU flash usage: 78% (312KB/400KB). RAM: 85% (170KB/"
            "200KB). Getting tight. The navigation stack alone is 45%.",
        )
    )
    msgs.append(
        _msg(
            "1711925060.000511",
            "#firmware",
            "U006",
            "We should profile the nav stack for heap fragmentation. "
            "I bet we can reclaim 20KB by switching to fixed-size "
            "allocators for the path planner.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711925120.000512",
            "#firmware",
            "U014",
            "Good idea. Also the logging buffer is 32KB — we can "
            "compress logs in-place and halve that.",
            thread=t3,
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1711935000.000513",
            "#firmware",
            "U006",
            "Motor control loop validated at 20kHz update rate. "
            "Jitter is <500ns. Meets real-time requirements.",
            reactions=[_r("rocket", ["U002", "U012"])],
        )
    )
    return msgs


def _build_supply_chain_messages() -> list[SlackMessage]:
    """Build messages for #supply-chain channel."""
    msgs: list[SlackMessage] = []

    # Thread 1: Component lead times review
    t1 = "1711906000.000600"
    msgs.append(
        _msg(
            t1,
            "#supply-chain",
            "U007",
            "DVT build material review. Critical path items and lead "
            "times: BLDC motors (6 wk), battery cells (4 wk), LIDAR "
            "module (8 wk), custom PCBs (3 wk). DVT build target is "
            "10 weeks out.",
        )
    )
    msgs.append(
        _msg(
            "1711906060.000601",
            "#supply-chain",
            "U017",
            "LIDAR at 8 weeks is the long pole. I've got a PO "
            "ready for Velodyne — just need engineering sign-off "
            "on the final part number.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711906120.000602",
            "#supply-chain",
            "U007",
            "Also need to confirm quantity. @U010 are we building 10 or 15 DVT units?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711906180.000603",
            "#supply-chain",
            "U010",
            "15 units. 10 for validation, 3 for field testing, 2 "
            "spares. Better to order extra now than pay expedite later.",
            thread=t1,
            reactions=[_r("thumbsup", ["U007", "U017"])],
        )
    )
    msgs.append(
        _msg(
            "1711906240.000604",
            "#supply-chain",
            "U017",
            "Updated PO for 15x. Total BOM cost per unit: $3,240. "
            "15 units = $48,600. Within the DVT build budget of $55k.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711906300.000605",
            "#supply-chain",
            "U007",
            "Approved. @U017 please release the PO today. We need "
            "those LIDARs moving ASAP given the 8 week lead.",
            thread=t1,
        )
    )

    # Thread 2: FPGA supply alert (BURIED SIGNAL #3 — supply chain impact)
    t2 = "1711916000.000606"
    msgs.append(
        _msg(
            t2,
            "#supply-chain",
            "U017",
            "Alert from Arrow: Xilinx Artix-7 XC7A35T allocation is "
            "being pulled. New lead time is 16 weeks, up from 12. "
            "We need 50 pcs for DVT.",
            reactions=[_r("rotating_light", ["U007", "U011"])],
        )
    )
    msgs.append(
        _msg(
            "1711916060.000607",
            "#supply-chain",
            "U007",
            "16 weeks is past our DVT build date. Options: "
            "(1) expedite at premium, (2) find broker stock, "
            "(3) design in alternate FPGA.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711916120.000608",
            "#supply-chain",
            "U017",
            "Checking brokers. Also the XC7A50T is pin-compatible "
            "and in stock — 800 pcs at Arrow. Higher capacity but "
            "same footprint. @U006 can firmware use the 50T?",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711916180.000609",
            "#supply-chain",
            "U006",
            "XC7A50T is a drop-in replacement. Same pinout, more "
            "logic fabric. Bitstream needs rebuild but no design "
            "changes. Go for it.",
            thread=t2,
            reactions=[_r("thumbsup", ["U017", "U007"])],
        )
    )
    msgs.append(
        _msg(
            "1711916240.000610",
            "#supply-chain",
            "U007",
            "Decision: switch to XC7A50T. @U017 order 50+10 spare "
            "immediately from Arrow stock. @U006 rebuild bitstream.",
            thread=t2,
            reactions=[
                _r("white_check_mark", ["U006", "U017", "U011"]),
            ],
        )
    )

    # Thread 3: Vendor qualification
    t3 = "1711926000.000611"
    msgs.append(
        _msg(
            t3,
            "#supply-chain",
            "U013",
            "Magnesium die casting vendor short list: (1) DyCast "
            "(domestic, 8wk), (2) Zhongshan (China, 5wk + 3wk ship), "
            "(3) MagForm (Mexico, 6wk). All can do AZ91D alloy.",
        )
    )
    msgs.append(
        _msg(
            "1711926060.000612",
            "#supply-chain",
            "U007",
            "DyCast is preferred for prototype — domestic simplifies "
            "quality audits. What's their MOQ for prototypes?",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711926120.000613",
            "#supply-chain",
            "U013",
            "DyCast has no MOQ for proto tooling. T0 samples in 8 "
            "weeks from tooling release. $12k for soft tool. They "
            "need the 3D model by next Friday.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711926180.000614",
            "#supply-chain",
            "U007",
            "Approved. @U013 send the RFQ with the Parasolid from "
            "@U001. Let's get magnesium prototypes in hand for DVT "
            "comparison testing.",
            thread=t3,
            reactions=[_r("thumbsup", ["U013"])],
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1711936000.000615",
            "#supply-chain",
            "U017",
            "Weekly supplier scorecard: 94% on-time delivery this "
            "month. Two late shipments — both from the connector "
            "vendor (Molex). Escalating.",
        )
    )
    msgs.append(
        _msg(
            "1711936060.000616",
            "#supply-chain",
            "U007",
            "The Molex issue is becoming a pattern. @U017 set up a "
            "call with their regional sales manager. We need commits.",
        )
    )
    return msgs


def _build_general_messages() -> list[SlackMessage]:
    """Build messages for #amr-general channel."""
    msgs: list[SlackMessage] = []

    # Thread 1: DVT readiness review planning
    t1 = "1711907000.000700"
    msgs.append(
        _msg(
            t1,
            "#amr-general",
            "U011",
            "DVT readiness review scheduled for Friday 3pm. Each "
            "workstream lead needs a 5-min status update: open "
            "blockers, critical test results, and supply chain risks.",
            reactions=[_r("eyes", ["U001", "U002", "U003", "U007"])],
        )
    )
    msgs.append(
        _msg(
            "1711907060.000701",
            "#amr-general",
            "U010",
            "Please also include a go/no-go recommendation for each "
            "workstream. We need to decide on Friday whether DVT "
            "build starts on schedule or slips.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711907120.000702",
            "#amr-general",
            "U002",
            "Drivetrain is go pending the thermal interface fix. "
            "@U003 when will we have validation data on the new TIM?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711907180.000703",
            "#amr-general",
            "U003",
            "Testing the Fujipoly XR-Um today. Results by Thursday AM.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711907240.000704",
            "#amr-general",
            "U007",
            "Supply chain is conditional go. The FPGA situation is "
            "resolved (switched to XC7A50T) but the LIDAR lead time "
            "is tight — 8 weeks with no float.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711907300.000705",
            "#amr-general",
            "U001",
            "Chassis is conditional go. The snap-fit redesign is done "
            "and tested. Magnesium housing decision is pending vendor "
            "quotes — won't affect DVT timeline either way.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711907360.000706",
            "#amr-general",
            "U005",
            "Sensors are go. LIDAR calibration issue resolved with "
            "thermal compensation. Camera FOV accepted for DVT with "
            "PVT action item logged.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711907420.000707",
            "#amr-general",
            "U006",
            "Firmware is go. FPGA timing resolved. Bootloader v2.1 "
            "ready. Motor control loop validated. Memory usage is "
            "tight but manageable.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711907480.000708",
            "#amr-general",
            "U004",
            "Power systems is go. BMS SOC accuracy fixed with 16-bit "
            "ADC. Driver board thermal addressed with via stitching. "
            "Battery cycling on track.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711907540.000709",
            "#amr-general",
            "U011",
            "Good. Looks like we're at conditional go across the "
            "board. I'll compile the readiness matrix and distribute "
            "before Friday. Blockers: TIM validation, LIDAR float.",
            thread=t1,
            reactions=[_r("thumbsup", ["U010", "U019"])],
        )
    )

    # Thread 2: Safety review update
    t2 = "1711917000.000710"
    msgs.append(
        _msg(
            t2,
            "#amr-general",
            "U015",
            "Pre-DVT safety review findings: 3 open items. "
            "(1) E-stop wiring needs redundant path, (2) bumper "
            "force sensor calibration drift, (3) motor controller "
            "watchdog timeout too long at 500ms.",
        )
    )
    msgs.append(
        _msg(
            "1711917060.000711",
            "#amr-general",
            "U010",
            "These are all blockers for DVT entry. @U004 own the "
            "e-stop and watchdog. @U005 own the bumper sensor.",
            thread=t2,
            reactions=[_r("thumbsup", ["U004", "U005"])],
        )
    )
    msgs.append(
        _msg(
            "1711917120.000712",
            "#amr-general",
            "U004",
            "E-stop: adding second contactor in series. Hardware "
            "change, 2 days. Watchdog: reducing to 50ms. Firmware "
            "change, 1 hour. Both done by Wednesday.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1711917180.000713",
            "#amr-general",
            "U005",
            "Bumper sensor: the drift is temperature-related. Adding "
            "runtime calibration offset. Fix ready by Tuesday.",
            thread=t2,
        )
    )

    # Thread 3: VP check-in
    t3 = "1711927000.000714"
    msgs.append(
        _msg(
            t3,
            "#amr-general",
            "U019",
            "Team — great progress this sprint. Customer demo is "
            "scheduled for 6 weeks after DVT build starts. Need "
            "the core navigation loop running by then.",
        )
    )
    msgs.append(
        _msg(
            "1711927060.000715",
            "#amr-general",
            "U010",
            "Nav loop is on track. @U006 and @U005 are integrating "
            "the LIDAR-based SLAM with the motor controller this "
            "week. Basic warehouse navigation demo should be ready.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1711927120.000716",
            "#amr-general",
            "U019",
            "Perfect. The customer specifically wants to see obstacle "
            "avoidance and pallet detection. Make sure those are in "
            "the demo script.",
            thread=t3,
            reactions=[_r("thumbsup", ["U010", "U005"])],
        )
    )

    # Standalone messages
    msgs.append(
        _msg(
            "1711937000.000717",
            "#amr-general",
            "U011",
            "Updated project timeline on Confluence. DVT build: "
            "weeks 12-14. Field test: weeks 15-18. Customer demo: "
            "week 18. PVT: weeks 22-26.",
        )
    )
    msgs.append(
        _msg(
            "1711937060.000718",
            "#amr-general",
            "U009",
            "Test lab schedule is booked solid weeks 12-14. I've "
            "reserved the thermal chamber and vibration table for "
            "DVT validation. First come first served for the EMC "
            "chamber.",
        )
    )
    msgs.append(
        _msg(
            "1711937120.000719",
            "#amr-general",
            "U010",
            "All hands reminder: design freeze for DVT is next "
            "Friday. Any changes after that go through the ECO "
            "process. No exceptions.",
            reactions=[_r("rotating_light", ["U001", "U002", "U003", "U004", "U005", "U006"])],
        )
    )
    return msgs


def _build_day2_chassis() -> list[SlackMessage]:
    """Day 2 chassis discussions — test results and design updates."""
    msgs: list[SlackMessage] = []
    t1 = "1711990000.001000"
    msgs.append(
        _msg(
            t1,
            "#chassis-design",
            "U008",
            "Updated topology-optimized motor mount STEP uploaded. "
            "Mass savings: 148g. Total chassis now at 4.58kg — within "
            "2% of the 4.5kg budget.",
        )
    )
    msgs.append(
        _msg(
            "1711990060.001001",
            "#chassis-design",
            "U001",
            "Good progress. The remaining 80g is in the battery tray. "
            "Can we pocket the underside without compromising stiffness?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711990120.001002",
            "#chassis-design",
            "U008",
            "Running a quick modal analysis to check first resonant "
            "freq. Battery tray needs to stay above 200Hz to avoid "
            "coupling with the motor vibration.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711990180.001003",
            "#chassis-design",
            "U008",
            "Modal results: pocketed tray first mode at 245Hz. Safe. "
            "Mass with pockets: 4.48kg. Under budget.",
            thread=t1,
            reactions=[_r("tada", ["U001", "U020"])],
        )
    )
    msgs.append(
        _msg(
            "1711990240.001004",
            "#chassis-design",
            "U020",
            "Nice work. I'll update the assembly drawing and release "
            "to the model vault. Rev D it is.",
            thread=t1,
        )
    )

    # Thread 2: IP54 seal testing
    t2 = "1712000000.001005"
    msgs.append(
        _msg(
            t2,
            "#chassis-design",
            "U009",
            "IP54 ingress test on chassis rev C: dust test passed, "
            "water splash test passed all faces. One leak point at "
            "the cable gland for motor harness.",
        )
    )
    msgs.append(
        _msg(
            "1712000060.001006",
            "#chassis-design",
            "U001",
            "Cable gland is the M20 Hummel? We might need the version with double sealing lip.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712000120.001007",
            "#chassis-design",
            "U009",
            "Correct. The single lip version leaks at 45-degree spray. "
            "Double lip version is $2 more per unit. 8 glands per robot.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712000180.001008",
            "#chassis-design",
            "U001",
            "$16 per unit for IP54 compliance is a no-brainer. "
            "Switching to double lip. @U017 please update the BOM.",
            thread=t2,
            reactions=[_r("thumbsup", ["U009", "U017"])],
        )
    )

    # Thread 3: Vibration test prep
    t3 = "1712010000.001009"
    msgs.append(
        _msg(
            t3,
            "#chassis-design",
            "U015",
            "Vibration test profile for chassis DVT: random vibe "
            "0.5g RMS 10-500Hz, 30 min per axis. Plus sine sweep "
            "5-200Hz at 0.25g for resonance hunting.",
        )
    )
    msgs.append(
        _msg(
            "1712010060.001010",
            "#chassis-design",
            "U001",
            "The motor excitation is primarily at 150-180Hz range. "
            "Make sure the sine sweep has fine resolution through "
            "that band — 0.5Hz steps.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712010120.001011",
            "#chassis-design",
            "U015",
            "Noted. Also adding shock test: half-sine 30g 11ms "
            "per IEC 60068-2-27. Test fixturing designed — need "
            "3D printed adapter for shaker table.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712010180.001012",
            "#chassis-design",
            "U009",
            "I can print the adapter on the Markforged. Send me "
            "the STEP and I'll have it ready by Thursday.",
            thread=t3,
        )
    )

    # Standalone day 2 messages
    msgs.append(
        _msg(
            "1712020000.001013",
            "#chassis-design",
            "U020",
            "Drawing review complete for motor mount rev D. All "
            "GD&T callouts verified. Ready for vendor quote.",
        )
    )
    msgs.append(
        _msg(
            "1712020060.001014",
            "#chassis-design",
            "U013",
            "Vendor confirmed receipt of updated Parasolid. Tool "
            "modification quote expected Monday. Lifter pin change "
            "adds $1.2k to the tool cost.",
        )
    )
    msgs.append(
        _msg(
            "1712020120.001015",
            "#chassis-design",
            "U001",
            "Acceptable. Total tool cost is still within budget. "
            "@U007 please include in the DVT cost rollup.",
        )
    )
    return msgs


def _build_day2_drivetrain() -> list[SlackMessage]:
    """Day 2 drivetrain follow-ups and testing."""
    msgs: list[SlackMessage] = []

    t1 = "1711991000.001100"
    msgs.append(
        _msg(
            t1,
            "#drivetrain",
            "U012",
            "Harmonic drive efficiency measurement: 82% at rated "
            "load, 78% at 1.5x rated. Spec sheet claims 85%. "
            "The 3% loss is in the wave generator bearing.",
        )
    )
    msgs.append(
        _msg(
            "1711991060.001101",
            "#drivetrain",
            "U002",
            "78% at 1.5x is concerning for the peak torque case. "
            "That means 22% of the motor power is heat. Does our "
            "thermal budget account for that?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711991120.001102",
            "#drivetrain",
            "U003",
            "The thermal model assumed 85% efficiency. With 78% we "
            "get an additional 4.5W of heat per motor at peak. "
            "Need to update the thermal analysis.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711991180.001103",
            "#drivetrain",
            "U002",
            "The peak is only 15s. Thermal mass should absorb it. "
            "@U003 can you confirm the transient thermal response?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711991240.001104",
            "#drivetrain",
            "U003",
            "Ran the transient: temp rise is 3C over 15s burst. "
            "Well within margin. Gearbox steady-state is fine.",
            thread=t1,
            reactions=[_r("thumbsup", ["U002", "U012"])],
        )
    )

    # Thread 2: Wheel assembly procedure
    t2 = "1712001000.001105"
    msgs.append(
        _msg(
            t2,
            "#drivetrain",
            "U012",
            "Wheel assembly procedure v2 uploaded to Confluence. "
            "Key change: bearing preload now set with torque wrench "
            "at 2.5Nm instead of feel. Eliminates the runout issue.",
        )
    )
    msgs.append(
        _msg(
            "1712001060.001106",
            "#drivetrain",
            "U002",
            "Good. Also add a step for verifying encoder alignment "
            "after bearing preload. The last build had 2 misaligned "
            "encoders that caused position errors.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712001120.001107",
            "#drivetrain",
            "U012",
            "Added encoder alignment check with go/no-go gauge. "
            "Max allowable offset is 0.05mm radial.",
            thread=t2,
        )
    )

    # Thread 3: Motor controller calibration
    t3 = "1712011000.001108"
    msgs.append(
        _msg(
            t3,
            "#drivetrain",
            "U004",
            "Motor controller auto-calibration routine completed on "
            "all 4 motors. Phase resistance and inductance measured "
            "within 2% of datasheet values.",
        )
    )
    msgs.append(
        _msg(
            "1712011060.001109",
            "#drivetrain",
            "U002",
            "What about the back-EMF constant? That's the one that drifts with temperature.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712011120.001110",
            "#drivetrain",
            "U004",
            "Ke measured at 0.0285 V/rpm vs spec 0.029. Within 2%. "
            "I've added temperature compensation in the FOC loop — "
            "recalibrates Ke every 60 seconds using the motor temp "
            "sensor.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712011180.001111",
            "#drivetrain",
            "U002",
            "Good. That should eliminate the torque ripple we saw at elevated temps last week.",
            thread=t3,
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1712021000.001112",
            "#drivetrain",
            "U002",
            "Drivetrain DVT test matrix finalized: 14 tests across "
            "3 categories (performance, durability, environmental). "
            "Shared in Confluence.",
            reactions=[_r("thumbsup", ["U010", "U009"])],
        )
    )
    msgs.append(
        _msg(
            "1712021060.001113",
            "#drivetrain",
            "U012",
            "Ordered 8 spare harmonic drives for DVT. 2 week lead "
            "time. We'll have spares before DVT build starts.",
        )
    )
    return msgs


def _build_day2_thermal() -> list[SlackMessage]:
    """Day 2 thermal management follow-ups."""
    msgs: list[SlackMessage] = []

    t1 = "1711992000.001200"
    msgs.append(
        _msg(
            t1,
            "#thermal-management",
            "U003",
            "Fujipoly XR-Um test results: thermal resistance dropped "
            "from 2.8 C/W to 1.1 C/W with the softer pad. Motor "
            "winding temp now peaks at 138C — 17C margin to limit.",
            reactions=[_r("tada", ["U001", "U002", "U018"])],
        )
    )
    msgs.append(
        _msg(
            "1711992060.001201",
            "#thermal-management",
            "U002",
            "Excellent. That gives us enough margin even with the "
            "gearbox efficiency loss. Thermal is no longer a risk.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711992120.001202",
            "#thermal-management",
            "U018",
            "What's the cost delta? The Fujipoly is more expensive than the Bergquist per m2.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711992180.001203",
            "#thermal-management",
            "U003",
            "About $3.50 more per motor, $14 per robot. Worth it "
            "for 17C margin vs 13C with the stiffer pad.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711992240.001204",
            "#thermal-management",
            "U003",
            "Updated the BOM with Fujipoly for DVT builds. Added a "
            "note that production may revert to Bergquist if chassis "
            "machining tolerances are tighter.",
            thread=t1,
        )
    )

    # Thread 2: CFD results for fan duct
    t2 = "1712002000.001205"
    msgs.append(
        _msg(
            t2,
            "#thermal-management",
            "U003",
            "CFD results for the revised fan duct: at 3000rpm we get "
            "1.8 CFM through the heat sink. Required is 1.5 CFM for "
            "thermal compliance. 20% margin.",
        )
    )
    msgs.append(
        _msg(
            "1712002060.001206",
            "#thermal-management",
            "U015",
            "What's the noise level at 3000rpm?",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712002120.001207",
            "#thermal-management",
            "U003",
            "Estimated 48dBA at 1m based on the fan curve. Well "
            "under the 55dBA spec. The duct redesign helped — better "
            "flow path means less turbulent noise.",
            thread=t2,
            reactions=[_r("white_check_mark", ["U015"])],
        )
    )

    # Thread 3: Electronics thermal analysis
    t3 = "1712012000.001208"
    msgs.append(
        _msg(
            t3,
            "#thermal-management",
            "U018",
            "Main PCB thermal scan: hottest component is the DC-DC "
            "converter at 78C. Rated to 105C. 27C margin is adequate.",
        )
    )
    msgs.append(
        _msg(
            "1712012060.001209",
            "#thermal-management",
            "U004",
            "The DC-DC is derated above 85C ambient. At 35C ambient "
            "the junction will be around 91C. Still 14C margin.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712012120.001210",
            "#thermal-management",
            "U018",
            "Good point. I'll add the derating curve to the thermal "
            "budget spreadsheet. MCU is at 62C, well within limits.",
            thread=t3,
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1712022000.001211",
            "#thermal-management",
            "U003",
            "Thermal DVT test plan: ambient soak from -10C to 50C, "
            "thermal cycling -20C to 60C x 100 cycles, thermal "
            "shock per IEC 60068-2-14.",
        )
    )
    msgs.append(
        _msg(
            "1712022060.001212",
            "#thermal-management",
            "U015",
            "Thermal chamber is booked for weeks 13-14. I'll need "
            "2 complete units for the full thermal validation suite.",
        )
    )
    return msgs


def _build_day2_power() -> list[SlackMessage]:
    """Day 2 power systems follow-ups."""
    msgs: list[SlackMessage] = []

    t1 = "1711993000.001300"
    msgs.append(
        _msg(
            t1,
            "#power-systems",
            "U014",
            "BMS firmware v3.2 deployed. Hybrid SOC estimator "
            "active: coulomb counting below 20%, voltage-based above. "
            "SOC error now <2% across full range.",
            reactions=[_r("white_check_mark", ["U004", "U018"])],
        )
    )
    msgs.append(
        _msg(
            "1711993060.001301",
            "#power-systems",
            "U004",
            "Verified on bench. SOC tracks within 1.5% of reference "
            "coulomb counter. Publish the cal parameters for the "
            "production BMS.",
            thread=t1,
        )
    )

    # Thread 2: Charging circuit
    t2 = "1712003000.001302"
    msgs.append(
        _msg(
            t2,
            "#power-systems",
            "U018",
            "Fast charge circuit tested: 0 to 80% in 55 minutes. "
            "Spec target is 60 min. Exceeds requirement.",
        )
    )
    msgs.append(
        _msg(
            "1712003060.001303",
            "#power-systems",
            "U004",
            "Cell balancing during charge — are we seeing any cell "
            "voltage spread at end of charge?",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712003120.001304",
            "#power-systems",
            "U018",
            "Max cell-to-cell delta at 80% is 12mV. BMS balances "
            "during the CV phase. By 100% delta is <5mV. Good.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712003180.001305",
            "#power-systems",
            "U004",
            "12mV at 80% is fine. The NMC cells are well matched. "
            "We should document the acceptance criteria for incoming "
            "cell matching: <15mV spread at 50% SOC.",
            thread=t2,
        )
    )

    # Thread 3: Power sequencing
    t3 = "1712013000.001306"
    msgs.append(
        _msg(
            t3,
            "#power-systems",
            "U004",
            "Power sequencing updated: main rail → MCU → sensors → "
            "motor drivers → LIDAR. Each stage has 50ms delay and "
            "current limit. Prevents inrush brownout.",
        )
    )
    msgs.append(
        _msg(
            "1712013060.001307",
            "#power-systems",
            "U006",
            "Is the FPGA on the MCU rail or its own? It draws 1.2A peak during configuration.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712013120.001308",
            "#power-systems",
            "U004",
            "Own rail with dedicated 3.3V regulator. Sequenced after "
            "MCU so the SPI bus is ready when FPGA configures.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712013180.001309",
            "#power-systems",
            "U006",
            "Perfect. That matches our boot sequence: MCU init → "
            "FPGA bitstream load → motor control start.",
            thread=t3,
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1712023000.001310",
            "#power-systems",
            "U018",
            "Battery safety test schedule: nail penetration, "
            "overcharge, short circuit, crush. Using 5 sacrificial "
            "packs. Test lab booked for week 13.",
        )
    )
    return msgs


def _build_day2_sensors() -> list[SlackMessage]:
    """Day 2 sensor integration follow-ups."""
    msgs: list[SlackMessage] = []

    t1 = "1711994000.001400"
    msgs.append(
        _msg(
            t1,
            "#sensors",
            "U016",
            "SLAM validation: position drift is 0.3% of travel "
            "distance after 1km loop. Spec is <0.5%. Meeting "
            "requirement with margin.",
            reactions=[_r("rocket", ["U005", "U006", "U010"])],
        )
    )
    msgs.append(
        _msg(
            "1711994060.001401",
            "#sensors",
            "U005",
            "That's with LIDAR only? Or fused with wheel odometry?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711994120.001402",
            "#sensors",
            "U016",
            "Fused: LIDAR + wheel odom + IMU. LIDAR-only is 0.8% "
            "drift. The fusion brings it way down.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711994180.001403",
            "#sensors",
            "U006",
            "IMU bias stability is critical for the fusion. Are you "
            "running the calibration at every power-on?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711994240.001404",
            "#sensors",
            "U016",
            "Yes, 10-second stationary calibration at boot. Gyro "
            "bias converges to <0.01 deg/s within 5 seconds.",
            thread=t1,
        )
    )

    # Thread 2: Safety sensor integration
    t2 = "1712004000.001405"
    msgs.append(
        _msg(
            t2,
            "#sensors",
            "U005",
            "Safety LIDAR (rear) installed and calibrated. Detection "
            "range: 0.1m to 4m. Response time: <50ms from detection "
            "to motor stop command.",
        )
    )
    msgs.append(
        _msg(
            "1712004060.001406",
            "#sensors",
            "U006",
            "50ms is the total including the motor deceleration? "
            "Or just the sensor-to-command latency?",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712004120.001407",
            "#sensors",
            "U005",
            "Sensor-to-command only. Motor deceleration adds 200ms "
            "from full speed. Total stopping distance: 0.35m. Safety "
            "zone is set at 0.5m.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712004180.001408",
            "#sensors",
            "U004",
            "The motor controller watchdog now at 50ms (down from "
            "500ms per the safety review). If the safety LIDAR "
            "command doesn't arrive in 50ms, motors hard-stop.",
            thread=t2,
            reactions=[_r("white_check_mark", ["U005", "U015"])],
        )
    )

    # Thread 3: Pallet detection algorithm
    t3 = "1712014000.001409"
    msgs.append(
        _msg(
            t3,
            "#sensors",
            "U016",
            "Pallet detection hit rate: 94% at 5m range, 98% at "
            "3m. Using 3D point cloud segmentation with RANSAC "
            "plane fitting.",
        )
    )
    msgs.append(
        _msg(
            "1712014060.001410",
            "#sensors",
            "U005",
            "What are the false positive rates? A false detection "
            "could send the robot into an obstacle.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712014120.001411",
            "#sensors",
            "U016",
            "0.1% false positive rate in the test dataset (10,000 "
            "frames). Most false positives are flat walls at oblique "
            "angles. Adding geometric constraints to filter those.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712014180.001412",
            "#sensors",
            "U010",
            "94% at 5m is good enough for the customer demo. We "
            "approach from 3m anyway for the docking maneuver.",
            thread=t3,
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1712024000.001413",
            "#sensors",
            "U005",
            "Sensor validation matrix updated. 8 of 12 tests pass. "
            "Open items: outdoor LIDAR range, rain performance, "
            "vibration immunity. All scheduled for DVT.",
        )
    )
    msgs.append(
        _msg(
            "1712024060.001414",
            "#sensors",
            "U016",
            "Camera image quality in low light: usable down to 50 "
            "lux. Warehouse minimum is typically 100 lux. Good.",
        )
    )
    return msgs


def _build_day2_firmware() -> list[SlackMessage]:
    """Day 2 firmware follow-ups."""
    msgs: list[SlackMessage] = []

    t1 = "1711995000.001500"
    msgs.append(
        _msg(
            t1,
            "#firmware",
            "U006",
            "XC7A50T bitstream rebuilt and verified. All timing "
            "clean. Extra fabric gives us room for the diagnostic "
            "logic we wanted to add later.",
        )
    )
    msgs.append(
        _msg(
            "1711995060.001501",
            "#firmware",
            "U014",
            "How much fabric utilization on the 50T? If we're under "
            "50% we have plenty of room for DVT debug features.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711995120.001502",
            "#firmware",
            "U006",
            "38% LUT utilization, 22% BRAM. Tons of room. Added "
            "the ILA debug core — 4K sample depth on the motor "
            "control signals.",
            thread=t1,
        )
    )

    # Thread 2: OTA update testing
    t2 = "1712005000.001503"
    msgs.append(
        _msg(
            t2,
            "#firmware",
            "U014",
            "OTA update stress test: 100 consecutive A/B partition "
            "switches. Zero failures. CRC validation catches all "
            "injected corruption.",
        )
    )
    msgs.append(
        _msg(
            "1712005060.001504",
            "#firmware",
            "U006",
            "Did you test power loss during flash write? That's the scary case.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712005120.001505",
            "#firmware",
            "U014",
            "Yes, killed power at random during 50 updates. All 50 "
            "recovered to the previous good partition. The atomic "
            "commit flag works as designed.",
            thread=t2,
            reactions=[_r("white_check_mark", ["U006", "U010"])],
        )
    )

    # Thread 3: Real-time performance
    t3 = "1712015000.001506"
    msgs.append(
        _msg(
            t3,
            "#firmware",
            "U006",
            "Real-time task profiling: motor control ISR 2.1us, "
            "navigation loop 1.8ms, sensor fusion 0.9ms. CPU "
            "utilization 72% at peak.",
        )
    )
    msgs.append(
        _msg(
            "1712015060.001507",
            "#firmware",
            "U014",
            "72% is on the edge. We should keep it under 80% for "
            "margin. Any optimization opportunities?",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712015120.001508",
            "#firmware",
            "U006",
            "The SLAM lookup table is in external flash. Moving it "
            "to internal SRAM saves 400us per nav cycle. That brings "
            "CPU down to 65%.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712015180.001509",
            "#firmware",
            "U014",
            "That eats 48KB of the 200KB RAM though. Given our 85% "
            "RAM usage that's tight. What about the compressed log "
            "buffer — did we implement that yet?",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712015240.001510",
            "#firmware",
            "U006",
            "Not yet. Compressed logs save 16KB. Combined with the "
            "fixed-size allocators (20KB savings), we'd free 36KB. "
            "Enough for the SLAM table with 8KB to spare.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712015300.001511",
            "#firmware",
            "U014",
            "Let's do all three: compressed logs, fixed allocators, "
            "SLAM table in SRAM. I'll start with the log compression.",
            thread=t3,
            reactions=[_r("thumbsup", ["U006"])],
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1712025000.001512",
            "#firmware",
            "U006",
            "Firmware v0.9.0 release candidate tagged. Full change "
            "log on Confluence. Ready for DVT qualification testing.",
            reactions=[_r("rocket", ["U014", "U010", "U002"])],
        )
    )
    return msgs


def _build_day2_supply_chain() -> list[SlackMessage]:
    """Day 2 supply chain follow-ups."""
    msgs: list[SlackMessage] = []

    t1 = "1711996000.001600"
    msgs.append(
        _msg(
            t1,
            "#supply-chain",
            "U017",
            "Arrow confirmed XC7A50T stock: 820 pcs available. "
            "PO for 60 pcs placed. Expected delivery: 5 business "
            "days. Crisis averted.",
            reactions=[_r("tada", ["U006", "U007", "U011"])],
        )
    )
    msgs.append(
        _msg(
            "1711996060.001601",
            "#supply-chain",
            "U007",
            "Excellent. @U011 please update the risk register — "
            "FPGA supply moved from red to green.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711996120.001602",
            "#supply-chain",
            "U011",
            "Updated. Also adding a note to qualify the XC7A50T "
            "as the primary going forward, with XC7A35T as fallback.",
            thread=t1,
        )
    )

    # Thread 2: DVT BOM costing
    t2 = "1712006000.001603"
    msgs.append(
        _msg(
            t2,
            "#supply-chain",
            "U007",
            "DVT BOM cost rollup complete. Per unit: $3,240 base + "
            "$14 TIM upgrade + $16 cable glands + $52 FPGA upgrade "
            "= $3,322 per unit. 15 units = $49,830.",
        )
    )
    msgs.append(
        _msg(
            "1712006060.001604",
            "#supply-chain",
            "U017",
            "Within the $55k budget with $5.2k contingency. That's about 10% — adequate for DVT.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712006120.001605",
            "#supply-chain",
            "U007",
            "The magnesium housing prototypes are separate — $12k "
            "tooling + ~$800/part for 3 test samples. That's an "
            "additional $14.4k from the NRE budget.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712006180.001606",
            "#supply-chain",
            "U011",
            "NRE budget has $25k remaining. $14.4k for mag housing "
            "exploration is approved. Go ahead.",
            thread=t2,
            reactions=[_r("thumbsup", ["U007", "U013"])],
        )
    )

    # Thread 3: Second source strategy
    t3 = "1712016000.001607"
    msgs.append(
        _msg(
            t3,
            "#supply-chain",
            "U007",
            "Given the FPGA scare, I want second sources for all "
            "critical components by PVT. Priority: FPGA (done), "
            "LIDAR module, BLDC motors, battery cells.",
        )
    )
    msgs.append(
        _msg(
            "1712016060.001608",
            "#supply-chain",
            "U017",
            "LIDAR: Ouster OS0 is drop-in replacement for Velodyne. "
            "Need engineering eval. Motors: Oriental Motor has an "
            "equivalent. Battery: Samsung INR21700 as alt to LG.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712016120.001609",
            "#supply-chain",
            "U007",
            "Get samples of all three alternates. We'll qualify "
            "them in parallel with DVT testing.",
            thread=t3,
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1712026000.001610",
            "#supply-chain",
            "U017",
            "Molex call done. They're allocating stock from their "
            "Asia warehouse. ETA 2 weeks for the connector backlog. "
            "They also offered 5% discount on next PO as goodwill.",
        )
    )
    msgs.append(
        _msg(
            "1712026060.001611",
            "#supply-chain",
            "U007",
            "Accept the discount, but I want a contractual on-time "
            "delivery guarantee for PVT quantities. Put it in the "
            "next PO terms.",
        )
    )
    return msgs


def _build_day2_general() -> list[SlackMessage]:
    """Day 2 general channel messages."""
    msgs: list[SlackMessage] = []

    # Thread 1: DVT readiness final prep
    t1 = "1711997000.001700"
    msgs.append(
        _msg(
            t1,
            "#amr-general",
            "U011",
            "DVT readiness matrix distributed. Summary: 5 workstreams "
            "at GO, 2 at CONDITIONAL GO (chassis mass, sensor FOV). "
            "No NO-GO items. Review Friday as planned.",
        )
    )
    msgs.append(
        _msg(
            "1711997060.001701",
            "#amr-general",
            "U010",
            "Good position. The two conditional items have clear "
            "paths to resolution. I'm comfortable proceeding.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1711997120.001702",
            "#amr-general",
            "U019",
            "Agreed. Let's confirm GO on Friday and start DVT "
            "material ordering Monday. The team has done excellent "
            "work getting here.",
            thread=t1,
            reactions=[_r("rocket", ["U001", "U002", "U003", "U004", "U005", "U006", "U007"])],
        )
    )

    # Thread 2: Test infrastructure
    t2 = "1712007000.001703"
    msgs.append(
        _msg(
            t2,
            "#amr-general",
            "U009",
            "DVT test infrastructure status: thermal chamber "
            "calibrated, vibe table load-tested, EMC pre-scan done. "
            "We're ready for units.",
        )
    )
    msgs.append(
        _msg(
            "1712007060.001704",
            "#amr-general",
            "U015",
            "Also booked the IP testing lab for week 14. They need "
            "2 units and 3 days for the full IP54 suite.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712007120.001705",
            "#amr-general",
            "U009",
            "Updated the test schedule in Confluence. Critical path "
            "is thermal cycling — takes 2 full weeks.",
            thread=t2,
        )
    )

    # Thread 3: Documentation review
    t3 = "1712017000.001706"
    msgs.append(
        _msg(
            t3,
            "#amr-general",
            "U011",
            "Design documentation audit: 85% of subsystems have "
            "complete design docs. Missing: power sequencing spec, "
            "sensor fusion algorithm description, FPGA register map.",
        )
    )
    msgs.append(
        _msg(
            "1712017060.001707",
            "#amr-general",
            "U004",
            "Power sequencing spec draft is ready. Reviewing today, publishing tomorrow.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712017120.001708",
            "#amr-general",
            "U016",
            "Sensor fusion doc is 70% done. Will complete by EOW.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712017180.001709",
            "#amr-general",
            "U006",
            "FPGA register map auto-generated from the HDL. Just "
            "need to add descriptions. Done by Wednesday.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712017240.001710",
            "#amr-general",
            "U011",
            "Target: 100% documentation coverage before DVT entry. Please prioritize.",
            thread=t3,
        )
    )

    # Standalone
    msgs.append(
        _msg(
            "1712027000.001711",
            "#amr-general",
            "U010",
            "Weekly metrics: 23 open action items (down from 31 "
            "last week), 0 critical blockers, 2 medium risks "
            "(LIDAR float, mag housing timeline).",
        )
    )
    msgs.append(
        _msg(
            "1712027060.001712",
            "#amr-general",
            "U019",
            "Board update prep: I need a 1-page executive summary "
            "by Thursday. @U011 can you compile from the readiness "
            "matrix?",
        )
    )
    msgs.append(
        _msg(
            "1712027120.001713",
            "#amr-general",
            "U011",
            "Will do. Including: DVT readiness status, cost vs "
            "budget, timeline risks, and customer demo plan.",
            thread="1712027060.001712",
        )
    )
    msgs.append(
        _msg(
            "1712027180.001714",
            "#amr-general",
            "U009",
            "EMC pre-scan results are clean at conducted emissions. "
            "Radiated is borderline at 230MHz — the motor PWM "
            "switching frequency harmonic. Adding ferrite bead.",
        )
    )
    msgs.append(
        _msg(
            "1712027240.001715",
            "#amr-general",
            "U015",
            "Reliability prediction complete: MTBF estimated at "
            "8,200 hours. Customer spec is 5,000 hours. 64% margin.",
            reactions=[_r("thumbsup", ["U010", "U019"])],
        )
    )
    return msgs


def _build_extra_threads() -> list[SlackMessage]:
    """Additional cross-channel conversations to fill volume."""
    msgs: list[SlackMessage] = []

    # Chassis: fastener standardization discussion
    t1 = "1712030000.002000"
    msgs.append(
        _msg(
            t1,
            "#chassis-design",
            "U015",
            "Fastener audit results: 23 unique fastener types in "
            "chassis assembly. Industry best practice is <15. Can "
            "we consolidate?",
        )
    )
    msgs.append(
        _msg(
            "1712030060.002001",
            "#chassis-design",
            "U001",
            "Agreed, 23 is too many. The M3x8 and M3x10 can merge "
            "to M3x10. Same for M4x12 and M4x14. That's -4 types.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1712030120.002002",
            "#chassis-design",
            "U020",
            "Also 5 of those are one-off shoulder screws. Can we "
            "redesign those features to use standard hex cap?",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1712030180.002003",
            "#chassis-design",
            "U001",
            "3 of the 5 can change. The other 2 need shoulders for "
            "bearing preload. That gets us to 16 types. Close enough.",
            thread=t1,
        )
    )
    msgs.append(
        _msg(
            "1712030240.002004",
            "#chassis-design",
            "U015",
            "Good. Updated BOM with consolidated fastener list. "
            "Also reduces kitting complexity for the assembly line.",
            thread=t1,
            reactions=[_r("thumbsup", ["U001", "U020", "U007"])],
        )
    )

    # Drivetrain: endurance test results
    t2 = "1712031000.002005"
    msgs.append(
        _msg(
            t2,
            "#drivetrain",
            "U002",
            "500-hour endurance test on wheels 1&2 complete. Zero "
            "failures. Bearing wear within spec. Tire compound shows "
            "0.3mm tread wear — well within the 2mm budget.",
            reactions=[_r("tada", ["U010", "U012"])],
        )
    )
    msgs.append(
        _msg(
            "1712031060.002006",
            "#drivetrain",
            "U012",
            "Gearbox backlash measurement after 500hr: increased "
            "from 6 to 9 arcmin. Spec limit is 15. Trending well.",
            thread=t2,
        )
    )
    msgs.append(
        _msg(
            "1712031120.002007",
            "#drivetrain",
            "U002",
            "Good data. We should repeat at 1000hr and 2000hr for "
            "the wear trend line. Keep wheels 1&2 running.",
            thread=t2,
        )
    )

    # Thermal: ambient range testing
    t3 = "1712032000.002008"
    msgs.append(
        _msg(
            t3,
            "#thermal-management",
            "U003",
            "Cold start test at -10C: system boots in 45 seconds. "
            "Battery delivers 92% of room-temp capacity. Motor "
            "controller needs 30s heater warm-up before operation.",
        )
    )
    msgs.append(
        _msg(
            "1712032060.002009",
            "#thermal-management",
            "U004",
            "The 30s heater warm-up is because the MOSFET Rds(on) "
            "increases at cold. Below -5C the current limit kicks in "
            "before the motor reaches full torque.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712032120.002010",
            "#thermal-management",
            "U003",
            "Can the warm-up run in parallel with boot? User sees "
            "boot time of 45s regardless, the heater just needs to "
            "finish before first move command.",
            thread=t3,
        )
    )
    msgs.append(
        _msg(
            "1712032180.002011",
            "#thermal-management",
            "U004",
            "Yes, heater starts at power-on. By the time boot and "
            "sensor init complete (~45s), the driver board is warm. "
            "Zero additional delay in practice.",
            thread=t3,
        )
    )

    # Power: ground fault detection
    t4 = "1712033000.002012"
    msgs.append(
        _msg(
            t4,
            "#power-systems",
            "U004",
            "Ground fault detection circuit validated. Trips at "
            "30mA leakage. Response time: 2ms to motor disconnect. "
            "Meets IEC 60204 requirements.",
        )
    )
    msgs.append(
        _msg(
            "1712033060.002013",
            "#power-systems",
            "U018",
            "Does it discriminate between ground fault and normal "
            "capacitive leakage? The motor cables have ~5mA of "
            "capacitive current at PWM frequency.",
            thread=t4,
        )
    )
    msgs.append(
        _msg(
            "1712033120.002014",
            "#power-systems",
            "U004",
            "Yes, the detection uses a DC component filter. PWM "
            "capacitive current is AC and gets filtered out. Only "
            "DC leakage above 30mA triggers the fault.",
            thread=t4,
            reactions=[_r("white_check_mark", ["U018"])],
        )
    )

    # Sensors: IMU calibration
    t5 = "1712034000.002015"
    msgs.append(
        _msg(
            t5,
            "#sensors",
            "U005",
            "IMU temperature calibration complete. Gyro bias drift "
            "reduced from 0.05 deg/s/C to 0.005 deg/s/C. 10x "
            "improvement across -10C to 50C range.",
        )
    )
    msgs.append(
        _msg(
            "1712034060.002016",
            "#sensors",
            "U006",
            "What's the calibration data size? If it fits in the "
            "IMU's internal EEPROM we don't need to store it on the "
            "MCU side.",
            thread=t5,
        )
    )
    msgs.append(
        _msg(
            "1712034120.002017",
            "#sensors",
            "U005",
            "256 bytes for the full temp-comp table. IMU EEPROM is "
            "512 bytes with 384 free. It fits. Programming over SPI "
            "during factory calibration.",
            thread=t5,
        )
    )
    msgs.append(
        _msg(
            "1712034180.002018",
            "#sensors",
            "U016",
            "This helps SLAM accuracy significantly. The gyro was "
            "the main error source in the sensor fusion. With 10x "
            "better stability I expect drift to drop to 0.2%.",
            thread=t5,
        )
    )

    t6 = "1712035000.002019"
    msgs.append(
        _msg(
            t6,
            "#firmware",
            "U014",
            "Diagnostic telemetry system ready: 32 channels of "
            "real-time data over CAN bus. Temperatures, voltages, "
            "motor currents, sensor status. 100Hz update rate.",
        )
    )
    msgs.append(
        _msg(
            "1712035060.002020",
            "#firmware",
            "U010",
            "Can we log this to SD card for post-test analysis? "
            "The DVT tests will need full data capture.",
            thread=t6,
        )
    )
    msgs.append(
        _msg(
            "1712035120.002021",
            "#firmware",
            "U014",
            "Yes, SD card logging is included. Binary format with "
            "Python decoder script. 8 hours of data fits on a 2GB "
            "card at 100Hz.",
            thread=t6,
        )
    )
    msgs.append(
        _msg(
            "1712035180.002022",
            "#firmware",
            "U009",
            "Perfect for DVT. I'll integrate the decoder into our "
            "test automation scripts. CSV output?",
            thread=t6,
        )
    )
    msgs.append(
        _msg(
            "1712035240.002023",
            "#firmware",
            "U014",
            "Decoder outputs both CSV and parquet. Parquet is 5x "
            "smaller and loads faster in pandas.",
            thread=t6,
            reactions=[_r("thumbsup", ["U009", "U010"])],
        )
    )

    # Supply chain: packaging spec
    t7 = "1712036000.002024"
    msgs.append(
        _msg(
            t7,
            "#supply-chain",
            "U007",
            "DVT unit packaging spec needed. These are going to "
            "3 test labs + 2 customer sites. Need to survive "
            "freight shipping (ISTA 3A equivalent).",
        )
    )
    msgs.append(
        _msg(
            "1712036060.002025",
            "#supply-chain",
            "U017",
            "Standard approach: custom foam inserts in a double-wall "
            "corrugated box. The robot weighs 18kg so we need the "
            "275# burst strength boxes.",
            thread=t7,
        )
    )
    msgs.append(
        _msg(
            "1712036120.002026",
            "#supply-chain",
            "U007",
            "Get quotes for 25 packaging sets (15 robots + 10 "
            "spares for repack). Include tilt and shock indicators "
            "inside each box.",
            thread=t7,
        )
    )

    # General: cross-team standup notes
    t8 = "1712037000.002027"
    msgs.append(
        _msg(
            t8,
            "#amr-general",
            "U011",
            "Standup notes: Chassis rev D released. Drivetrain "
            "endurance test passing. Thermal fix validated. Power "
            "BMS updated. Sensors SLAM qualified. Firmware v0.9 "
            "ready. Supply chain material ordered.",
        )
    )
    msgs.append(
        _msg(
            "1712037060.002028",
            "#amr-general",
            "U010",
            "Best status update we've had all quarter. Team is "
            "executing well. Keep the momentum through DVT.",
            thread=t8,
            reactions=[
                _r(
                    "rocket",
                    ["U001", "U002", "U003", "U004", "U005", "U006", "U007", "U011", "U019"],
                )
            ],
        )
    )
    msgs.append(
        _msg(
            "1712037120.002029",
            "#amr-general",
            "U019",
            "Agreed. I'll share these results with the board. "
            "This team is ahead of the industry average pace for "
            "a program of this complexity.",
            thread=t8,
        )
    )

    # More standalone messages across channels
    msgs.append(
        _msg(
            "1712038000.002030",
            "#chassis-design",
            "U009",
            "Torque audit complete. All 47 fasteners within spec. "
            "3 were at lower bound — tightened to nominal.",
        )
    )
    msgs.append(
        _msg(
            "1712038060.002031",
            "#drivetrain",
            "U002",
            "Updated the drivetrain design review presentation. "
            "Added the torque spec change rationale and the "
            "gearbox lifetime analysis. Shared on Confluence.",
        )
    )
    msgs.append(
        _msg(
            "1712038120.002032",
            "#thermal-management",
            "U018",
            "Ordered 10x Fujipoly XR-Um thermal pads for DVT. "
            "5-day lead time. Will have on hand before build.",
        )
    )
    msgs.append(
        _msg(
            "1712038180.002033",
            "#power-systems",
            "U014",
            "Motor controller firmware updated with the 50ms "
            "watchdog. Tested E-stop integration: full stop in "
            "180ms from button press. Within the 200ms requirement.",
            reactions=[_r("white_check_mark", ["U015"])],
        )
    )
    msgs.append(
        _msg(
            "1712038240.002034",
            "#sensors",
            "U005",
            "Ordered replacement camera lens with wider FOV for "
            "PVT evaluation. Should achieve 122 deg with less "
            "barrel distortion.",
        )
    )
    msgs.append(
        _msg(
            "1712038300.002035",
            "#firmware",
            "U006",
            "Fixed-size allocator implementation complete. RAM "
            "usage down from 85% to 74%. Log compression next.",
        )
    )
    msgs.append(
        _msg(
            "1712038360.002036",
            "#supply-chain",
            "U013",
            "DyCast confirmed magnesium proto tool kickoff. T0 "
            "samples expected in 8 weeks. Cost: $11.8k for tool, "
            "$780 per part for 3 samples.",
        )
    )
    msgs.append(
        _msg(
            "1712038420.002037",
            "#amr-general",
            "U015",
            "Updated FMEA with latest test results. RPN for 3 "
            "failure modes reduced below threshold. 2 remain above: "
            "battery cell failure and motor bearing seizure.",
        )
    )
    msgs.append(
        _msg(
            "1712038480.002038",
            "#chassis-design",
            "U013",
            "The aluminum extrusion vendor is quoting competitively. "
            "If we stay aluminum (no mag housing), per-unit cost "
            "drops $45 on the chassis alone.",
        )
    )
    msgs.append(
        _msg(
            "1712038540.002039",
            "#drivetrain",
            "U012",
            "Wheel 3 back on the endurance test after bearing "
            "reshim. Running clean at 500rpm. Will monitor for "
            "another 100 hours.",
        )
    )
    msgs.append(
        _msg(
            "1712038600.002040",
            "#thermal-management",
            "U003",
            "CFD validation: measured airflow matches sim within "
            "8%. Good correlation. The revised duct design is "
            "confirmed for DVT.",
        )
    )
    msgs.append(
        _msg(
            "1712038660.002041",
            "#power-systems",
            "U018",
            "Battery management CAN protocol documentation "
            "complete. 12 message IDs covering SOC, cell voltages, "
            "temperatures, and fault codes.",
        )
    )
    msgs.append(
        _msg(
            "1712038720.002042",
            "#sensors",
            "U016",
            "LIDAR dust contamination test: performance degrades "
            "above 50mg/m3. Warehouse typical is 5-15mg/m3. "
            "Adequate margin. Adding wiper for outdoor use.",
        )
    )
    msgs.append(
        _msg(
            "1712038780.002043",
            "#firmware",
            "U014",
            "CAN bus utilization: 34% at normal operation, 52% "
            "during diagnostics mode. Well under the 70% design "
            "limit.",
        )
    )
    msgs.append(
        _msg(
            "1712038840.002044",
            "#supply-chain",
            "U017",
            "Velodyne LIDAR PO confirmed. 15 units shipping week "
            "of May 12. On track for DVT build schedule.",
            reactions=[_r("thumbsup", ["U007", "U005"])],
        )
    )
    msgs.append(
        _msg(
            "1712038900.002045",
            "#amr-general",
            "U011",
            "Risk register updated: 4 green, 2 yellow (LIDAR "
            "float, mag housing timeline), 0 red. Best position "
            "since program inception.",
            reactions=[_r("white_check_mark", ["U010", "U019"])],
        )
    )
    msgs.append(
        _msg(
            "1712038960.002046",
            "#chassis-design",
            "U008",
            "FEA convergence study complete for motor mount. Stress "
            "results stable within 2% at current mesh density. No "
            "further refinement needed.",
        )
    )
    msgs.append(
        _msg(
            "1712039020.002047",
            "#drivetrain",
            "U004",
            "Motor current sense accuracy verified: ±0.5% at full "
            "scale. Exceeds the ±1% requirement for FOC control.",
        )
    )
    msgs.append(
        _msg(
            "1712039080.002048",
            "#thermal-management",
            "U015",
            "Thermal chamber calibration certificate received. "
            "±0.5C accuracy from -40C to 150C. Ready for DVT.",
        )
    )
    msgs.append(
        _msg(
            "1712039140.002049",
            "#power-systems",
            "U004",
            "Regenerative braking energy capture: recovering 12% "
            "of kinetic energy during deceleration. Extends runtime "
            "by approximately 8 minutes.",
        )
    )
    msgs.append(
        _msg(
            "1712039200.002050",
            "#sensors",
            "U005",
            "Safety LIDAR field-of-view verification: 270 deg "
            "horizontal, 30 deg vertical. Meets the ISO 3691-4 "
            "requirement for automated guided vehicles.",
        )
    )
    msgs.append(
        _msg(
            "1712039260.002051",
            "#firmware",
            "U006",
            "Motor control jitter optimization: worst-case ISR "
            "latency reduced from 2.1us to 1.4us by moving the "
            "ADC trigger to hardware timer compare output.",
        )
    )
    msgs.append(
        _msg(
            "1712039320.002052",
            "#supply-chain",
            "U007",
            "Quarterly business review with top 5 suppliers "
            "scheduled for next month. Focus: PVT volume commits "
            "and long-lead-time buffer stock agreements.",
        )
    )
    msgs.append(
        _msg(
            "1712039380.002053",
            "#amr-general",
            "U009",
            "Test automation framework v2 deployed. 85% of DVT "
            "tests can run unattended overnight. Remaining 15% "
            "require manual fixture setup.",
        )
    )
    msgs.append(
        _msg(
            "1712039440.002054",
            "#chassis-design",
            "U001",
            "Updated the assembly manual for rev D chassis. Added "
            "photos for the new snap-fit retention and cable gland "
            "installation. Shared on Confluence.",
        )
    )
    msgs.append(
        _msg(
            "1712039500.002055",
            "#amr-general",
            "U010",
            "Reminder: design freeze is tomorrow at 5pm. After that "
            "all changes require ECO. Submit any pending changes now.",
            reactions=[_r("rotating_light", ["U001", "U002", "U003", "U004", "U005", "U006"])],
        )
    )
    msgs.append(
        _msg(
            "1712039560.002056",
            "#drivetrain",
            "U002",
            "All drivetrain changes submitted. Rev D gearbox mount, "
            "updated torque spec, thermal interface spec. Ready for "
            "design freeze.",
        )
    )
    msgs.append(
        _msg(
            "1712039620.002057",
            "#chassis-design",
            "U001",
            "Chassis changes submitted: rev D assembly, 2.5mm wall "
            "snap fit, pocketed battery tray, double-lip cable "
            "glands. Ready for freeze.",
        )
    )
    msgs.append(
        _msg(
            "1712039680.002058",
            "#firmware",
            "U006",
            "Firmware v0.9.0 tagged and frozen. Any post-freeze "
            "changes go to v0.9.1 branch with ECO.",
        )
    )
    msgs.append(
        _msg(
            "1712039740.002059",
            "#power-systems",
            "U004",
            "Power system changes frozen: 16-bit ADC, thermal vias, "
            "hybrid SOC estimator, ground fault detection. All "
            "verified and documented.",
        )
    )
    msgs.append(
        _msg(
            "1712039800.002060",
            "#sensors",
            "U005",
            "Sensor subsystem frozen: thermal-compensated LIDAR, "
            "safety LIDAR config, IMU temp cal, camera with ISP "
            "dewarp. FOV waiver for DVT documented.",
        )
    )
    msgs.append(
        _msg(
            "1712039860.002061",
            "#thermal-management",
            "U003",
            "Thermal changes frozen: Fujipoly TIM for DVT, revised "
            "fan duct at 3000rpm, 35C ambient added to test matrix. "
            "All validated.",
        )
    )
    msgs.append(
        _msg(
            "1712039920.002062",
            "#supply-chain",
            "U007",
            "BOM frozen for DVT. All POs placed. Long-lead items "
            "on track. Next milestone: first article inspection "
            "in 4 weeks.",
        )
    )
    return msgs


def _build_all_messages() -> list[SlackMessage]:
    """Assemble the complete synthetic message dataset.

    Returns:
        All synthetic messages sorted by timestamp.
    """
    all_msgs: list[SlackMessage] = []
    all_msgs.extend(_build_chassis_messages())
    all_msgs.extend(_build_drivetrain_messages())
    all_msgs.extend(_build_thermal_messages())
    all_msgs.extend(_build_power_messages())
    all_msgs.extend(_build_sensor_messages())
    all_msgs.extend(_build_firmware_messages())
    all_msgs.extend(_build_supply_chain_messages())
    all_msgs.extend(_build_general_messages())
    all_msgs.extend(_build_day2_chassis())
    all_msgs.extend(_build_day2_drivetrain())
    all_msgs.extend(_build_day2_thermal())
    all_msgs.extend(_build_day2_power())
    all_msgs.extend(_build_day2_sensors())
    all_msgs.extend(_build_day2_firmware())
    all_msgs.extend(_build_day2_supply_chain())
    all_msgs.extend(_build_day2_general())
    all_msgs.extend(_build_extra_threads())
    return sorted(all_msgs, key=lambda m: m.message_ts)


_CACHED_MESSAGES: list[SlackMessage] | None = None


def load_messages() -> list[SlackMessage]:
    """Load the synthetic message dataset.

    Returns a cached copy of all synthetic messages, sorted by
    timestamp. Thread-safe for read-only access.

    Returns:
        List of SlackMessage objects.
    """
    global _CACHED_MESSAGES  # noqa: PLW0603
    if _CACHED_MESSAGES is None:
        _CACHED_MESSAGES = _build_all_messages()
    return list(_CACHED_MESSAGES)
