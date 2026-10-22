"""ESP32-S3 carrier board - single source of truth.

Both the schematic (.kicad_sch) and the PCB (.kicad_pcb) are generated from this file.
Units are mm. PCB origin = top-left corner of the board, y grows downwards.
"""

PROJECT = "ESP32S3_Carrier"
DATE = "2026-10-22"
REV = "1.1"

# Board outline
W = 116.0
H = 170.0
CORNER_R = 4.0
# Board position on the A4 portrait page (for the 1:1 PDF)
OX = 47.0
OY = 38.0

# Net classes
NET_CLASSES = {
    "Default": dict(track=0.25, clearance=0.2, via_d=0.6, via_drill=0.3),
    "Power": dict(track=0.6, clearance=0.25, via_d=0.8, via_drill=0.4),
    "GND": dict(track=0.5, clearance=0.25, via_d=0.8, via_drill=0.4),
}
NETCLASS_ASSIGN = {
    "+5V": "Power", "+5V_MOD": "Power", "+3V3_MOD": "Power", "GND": "GND",
    "/IR_A1": "Power", "/IR_A2": "Power", "/IR_A3": "Power", "/IR_LED_K": "Power", "/BUZ_NEG": "Power",
}

R0805 = "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"
R1206 = "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder"
C0805 = "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"
C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
CP63 = "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"
CP8 = "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"
BTN = "Button_Switch_THT:SW_PUSH_6mm"
TO92 = "Package_TO_SOT_THT:TO-92_Inline_Wide"
IRLED = "LED_THT:LED_D5.0mm_Horizontal_O1.27mm_Z3.0mm"

# DevKitC-1 v1.1 header names (top view, antenna up). J1 = left row, J3 = right row.
DEVKIT_J1 = ["3V3", "3V3", "RST", "IO4", "IO5", "IO6", "IO7", "IO15", "IO16", "IO17", "IO18",
             "IO8", "IO3", "IO46", "IO9", "IO10", "IO11", "IO12", "IO13", "IO14", "5V", "GND"]
DEVKIT_J3 = ["GND", "TX", "RX", "IO1", "IO2", "IO42", "IO41", "IO40", "IO39", "IO38", "IO37",
             "IO36", "IO35", "IO0", "IO45", "IO48", "IO47", "IO21", "IO20", "IO19", "GND", "GND"]

# ESP32-S3 GPIO -> net
GPIO_NET = {
    "IO4": "NRF1_CE", "IO5": "NRF1_CSN", "IO6": "NRF2_CE", "IO7": "NRF2_CSN",
    "IO15": "BTN_UP", "IO16": "BTN_DOWN", "IO38": "BTN_LEFT", "IO39": "BTN_RIGHT",
    "IO40": "BTN_OK", "IO41": "BTN_BACK",
    "IO17": "RFID_TX", "IO18": "I2C_SCL", "IO8": "I2C_SDA",
    "IO9": "CC_GDO0", "IO10": "CC_CS", "IO11": "SPI_MOSI", "IO12": "SPI_SCK", "IO13": "SPI_MISO",
    "IO14": "SD_CS", "IO1": "IR_RX", "IO2": "IR_TX", "IO47": "BUZ",
    "IO42": "CC_GDO2", "IO21": "NRF1_IRQ", "IO48": "NRF2_IRQ",
    "5V": "+5V", "GND": "GND",
}


def devkit_pins():
    pins = {}
    for i, n in enumerate(DEVKIT_J1):
        pins[str(i + 1)] = GPIO_NET.get(n)
    for i, n in enumerate(DEVKIT_J3):
        pins[str(i + 23)] = GPIO_NET.get(n)
    return pins


def C(ref, val, fp, net1, net2, sch, pcb):
    return dict(ref=ref, val=val, sym="Device:C", fp=fp, pins={"1": net1, "2": net2}, sch=sch, pcb=pcb)


def CP(ref, val, fp, plus, minus, sch, pcb):
    return dict(ref=ref, val=val, sym="Device:C_Polarized", fp=fp, pins={"1": plus, "2": minus}, sch=sch, pcb=pcb)


def R(ref, val, fp, n1, n2, sch, pcb):
    return dict(ref=ref, val=val, sym="Device:R", fp=fp, pins={"1": n1, "2": n2}, sch=sch, pcb=pcb)


def BTNC(ref, val, net, sch, center):
    # SW_PUSH_6mm origin is pad 1; body centre is at (3.25, 2.25)
    return dict(ref=ref, val=val, sym="Switch:SW_Push", fp=BTN, pins={"1": net, "2": "GND"},
                sch=sch, pcb=(center[0] - 3.25, center[1] - 2.25, 0), label=val)


def IRLEDC(ref, k, a, sch, pcb):
    return dict(ref=ref, val="IR LED 940nm", sym="Device:LED", fp=IRLED, pins={"1": k, "2": a}, sch=sch, pcb=pcb)


# pcb: (x, y, rotation_deg)   sch: (x, y)
COMPONENTS = [
    # --- Plug-in modules (female header sockets) ---
    dict(ref="U1", val="ESP32-S3-DevKitC-1 N16R8", sym="Carrier:ESP32-S3-DevKitC-1",
         fp="Carrier:ESP32-S3-DevKitC-1_Socket", pins=devkit_pins(), sch=(101.6, 132.08), pcb=(46.57, 108.66, 0)),
    dict(ref="J1", val="CC1101 433MHz SMA", sym="Carrier:CC1101_SMA_2x4", fp="Carrier:CC1101_SMA_2x4_Socket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "CC_GDO0", "4": "CC_CS", "5": "SPI_SCK", "6": "SPI_MOSI",
               "7": "SPI_MISO", "8": "CC_GDO2"}, sch=(228.6, 63.5), pcb=(54.19, 36.8, 0)),
    dict(ref="J2", val="NRF24L01+PA+LNA #1", sym="Carrier:NRF24L01_PA_LNA", fp="Carrier:NRF24L01_PA_LNA_Socket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "NRF1_CE", "4": "NRF1_CSN", "5": "SPI_SCK", "6": "SPI_MOSI",
               "7": "SPI_MISO", "8": "NRF1_IRQ"}, sch=(228.6, 106.68), pcb=(14.44, 37.8, 0)),
    dict(ref="J3", val="NRF24L01+PA+LNA #2", sym="Carrier:NRF24L01_PA_LNA", fp="Carrier:NRF24L01_PA_LNA_Socket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "NRF2_CE", "4": "NRF2_CSN", "5": "SPI_SCK", "6": "SPI_MOSI",
               "7": "SPI_MISO", "8": "NRF2_IRQ"}, sch=(228.6, 149.86), pcb=(93.94, 37.8, 0)),
    dict(ref="J4", val="PN532 V3 (I2C)", sym="Carrier:PN532_I2C", fp="Carrier:PN532_V3_I2C_Socket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "I2C_SDA", "4": "I2C_SCL"}, sch=(360.68, 63.5), pcb=(79.0, 71.09, 0)),
    dict(ref="J5", val="OLED 1.3in SH1106 I2C", sym="Carrier:OLED_SH1106_I2C", fp="Carrier:OLED_1.3in_I2C_Socket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "I2C_SCL", "4": "I2C_SDA"}, sch=(360.68, 99.06), pcb=(17.69, 54.6, 0)),
    dict(ref="J6", val="Catalex microSD", sym="Carrier:microSD_Catalex", fp="Carrier:microSD_Catalex_Socket",
         pins={"1": "GND", "2": "+5V_MOD", "3": "SD_MISO_RAW", "4": "SPI_MOSI", "5": "SPI_SCK", "6": "SD_CS"},
         sch=(228.6, 198.12), pcb=(76.7, 105.15, 0)),
    dict(ref="J7", val="RDM6300 125kHz", sym="Carrier:RDM6300", fp="Carrier:RDM6300_Socket",
         pins={"1": "RFID_TX5V", "2": None, "3": None, "4": "GND", "5": "+5V_MOD", "6": "RFID_ANT1", "7": "RFID_ANT2"},
         sch=(360.68, 182.88), pcb=(37.6, 107.4, 0)),
    dict(ref="J8", val="125kHz coil", sym="Connector_Generic:Conn_01x02",
         fp="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
         pins={"1": "RFID_ANT1", "2": "RFID_ANT2"}, sch=(449.58, 182.88), pcb=(4.0, 112.5, 90)),
    dict(ref="J9", val="Si5351 clock gen (3x SMA)", sym="Carrier:Si5351_7pin", fp="Carrier:Si5351_3SMA_Socket",
         pins={"1": None, "2": None, "3": None, "4": "I2C_SCL", "5": "I2C_SDA", "6": "GND", "7": "+3V3_MOD"},
         sch=(360.68, 134.62), pcb=(97.62, 149.6, 180)),

    # --- Decoupling ---
    C("C1", "100nF", C0805, "+3V3_MOD", "GND", (271.78, 63.5), (51.5, 44.0, 0)),
    CP("C2", "100uF", CP63, "+3V3_MOD", "GND", (284.48, 63.5), (56.5, 48.0, 0)),
    C("C3", "100nF", C0805, "+3V3_MOD", "GND", (271.78, 106.68), (11.3, 44.0, 0)),
    CP("C4", "100uF", CP63, "+3V3_MOD", "GND", (284.48, 106.68), (16.8, 48.0, 0)),
    C("C5", "100nF", C0805, "+3V3_MOD", "GND", (271.78, 149.86), (90.8, 44.0, 0)),
    CP("C6", "100uF", CP63, "+3V3_MOD", "GND", (284.48, 149.86), (96.3, 48.0, 0)),
    C("C7", "100nF", C0805, "+3V3_MOD", "GND", (391.16, 63.5), (69.8, 72.5, 90)),
    C("C8", "100nF", C0805, "+3V3_MOD", "GND", (391.16, 99.06), (12.0, 50.9, 0)),
    C("C9", "100nF", C0805, "+5V_MOD", "GND", (271.78, 198.12), (72.9, 106.5, 90)),
    C("C10", "100nF", C0805, "+5V_MOD", "GND", (391.16, 182.88), (24.0, 111.5, 0)),
    C("C11", "100nF", C0805, "IR_RX_VCC", "GND", (340.36, 254.0), (83.5, 9.6, 0)),
    C("C17", "100nF", C0805, "+3V3_MOD", "GND", (391.16, 134.62), (82.4, 142.8, 0)),

    # --- I2C pull-ups ---
    R("R1", "4.7k", R0805, "+3V3_MOD", "I2C_SDA", (424.18, 63.5), (63.5, 64.5, 0)),
    R("R2", "4.7k", R0805, "+3V3_MOD", "I2C_SCL", (436.88, 63.5), (63.5, 67.5, 0)),

    # --- SPI chip-select pull-ups (keep every SPI device deselected during boot) ---
    R("R12", "10k", R0805, "+3V3_MOD", "CC_CS", (462.28, 63.5), (49.0, 84.0, 90)),
    R("R13", "10k", R0805, "+3V3_MOD", "SD_CS", (474.98, 63.5), (52.5, 84.0, 90)),
    R("R14", "10k", R0805, "+3V3_MOD", "NRF1_CSN", (487.68, 63.5), (56.0, 84.0, 90)),
    R("R15", "10k", R0805, "+3V3_MOD", "NRF2_CSN", (500.38, 63.5), (59.5, 84.0, 90)),

    # --- microSD MISO cuttable bridge ---
    dict(ref="JP1", val="SD_MISO", sym="Jumper:SolderJumper_2_Bridged",
         fp="Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm",
         pins={"1": "SD_MISO_RAW", "2": "SPI_MISO"}, sch=(279.4, 213.36), pcb=(73.0, 112.1, 90)),

    # --- RDM6300 TX 5V -> 3.4V divider ---
    R("R8", "4.7k", R0805, "RFID_TX5V", "RFID_TX", (406.4, 182.88), (41.5, 113.0, 0)),
    R("R9", "10k", R0805, "RFID_TX", "GND", (419.1, 182.88), (41.5, 116.2, 0)),

    # --- IR transmitter: 3 LEDs, each with its own resistor, one low-side NPN ---
    IRLEDC("D1", "IR_LED_K", "IR_A1", (167.64, 248.92), (32.77, 10.5, 180)),
    IRLEDC("D2", "IR_LED_K", "IR_A2", (200.66, 248.92), (40.77, 10.5, 180)),
    IRLEDC("D3", "IR_LED_K", "IR_A3", (233.68, 248.92), (77.77, 10.5, 180)),
    R("R5", "47", R1206, "+5V_MOD", "IR_A1", (177.8, 231.14), (30.23, 16.2, 90)),
    R("R17", "47", R1206, "+5V_MOD", "IR_A2", (210.82, 231.14), (38.23, 16.2, 90)),
    R("R18", "47", R1206, "+5V_MOD", "IR_A3", (243.84, 231.14), (75.23, 16.2, 90)),
    dict(ref="Q1", val="PN2222A", sym="Carrier:PN2222A", fp=TO92,
         pins={"1": "GND", "2": "IR_BASE", "3": "IR_LED_K"}, sch=(182.88, 274.32), pcb=(31.5, 24.8, 0)),
    R("R3", "220", R0805, "IR_TX", "IR_BASE", (157.48, 276.86), (40.6, 23.6, 90)),
    R("R4", "10k", R0805, "IR_BASE", "GND", (167.64, 287.02), (40.6, 28.4, 90)),
    CP("C15", "100uF", CP63, "+5V_MOD", "GND", (264.16, 248.92), (30.0, 33.6, 0)),

    # --- IR receiver (lens faces the top edge) + RC supply filter ---
    dict(ref="U3", val="VS1838B", sym="Carrier:VS1838B", fp="OptoDevice:Vishay_MINICAST-3Pin",
         pins={"1": "IR_RX", "2": "GND", "3": "IR_RX_VCC"}, sch=(309.88, 254.0), pcb=(87.34, 4.1, 180)),
    R("R11", "100", R0805, "+3V3_MOD", "IR_RX_VCC", (330.2, 248.92), (83.5, 12.8, 0)),

    # --- Buzzer driver ---
    dict(ref="BZ1", val="Passive buzzer", sym="Device:Buzzer", fp="Buzzer_Beeper:Buzzer_12x9.5RM7.6",
         pins={"1": "+5V_MOD", "2": "BUZ_NEG"}, sch=(378.46, 248.92), pcb=(27.5, 158.0, 0)),
    dict(ref="D4", val="1N4148", sym="Device:D", fp="Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal",
         pins={"1": "+5V_MOD", "2": "BUZ_NEG"}, sch=(396.24, 248.92), pcb=(24.5, 167.0, 0)),
    dict(ref="Q2", val="PN2222A", sym="Carrier:PN2222A", fp=TO92,
         pins={"1": "GND", "2": "BUZ_BASE", "3": "BUZ_NEG"}, sch=(378.46, 271.78), pcb=(41.9, 152.5, 90)),
    R("R6", "1k", R0805, "BUZ", "BUZ_BASE", (355.6, 274.32), (42.3, 158.6, 90)),
    R("R7", "10k", R0805, "BUZ_BASE", "GND", (365.76, 284.48), (42.3, 163.4, 90)),

    # --- Module power switch (soft-start P-MOSFET) + 3.3 V regulator ---
    dict(ref="SW7", val="MODULE PWR", sym="Switch:SW_SPDT", fp="Button_Switch_THT:SW_Slide_SPDT_Angled_CK_OS102011MA1Q",
         pins={"1": "GND", "2": "PWR_SW", "3": None}, sch=(444.5, 228.6), pcb=(2.5, 149.0, 270)),
    R("R16", "100k", R0805, "PWR_SW", "PWR_GATE", (464.82, 228.6), (11.5, 153.5, 0)),
    R("R10", "1M", R0805, "+5V", "PWR_GATE", (477.52, 215.9), (15.2, 149.0, 90)),
    C("C16", "100nF", C0805, "PWR_GATE", "+5V_MOD", (490.22, 248.92), (16.5, 153.5, 0)),
    dict(ref="Q3", val="AO3401A", sym="Carrier:AO3401A", fp="Package_TO_SOT_SMD:SOT-23",
         pins={"1": "PWR_GATE", "2": "+5V", "3": "+5V_MOD"}, sch=(492.76, 233.68), pcb=(11.5, 149.0, 0)),
    dict(ref="U2", val="AMS1117-3.3", sym="Carrier:AMS1117-3.3", fp="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "+5V_MOD"}, sch=(538.48, 233.68), pcb=(55.0, 60.0, 0)),
    C("C12", "10uF", C1206, "+5V_MOD", "GND", (515.62, 238.76), (48.9, 62.5, 90)),
    CP("C13", "470uF", CP8, "+3V3_MOD", "GND", (558.8, 238.76), (52.0, 72.4, 0)),
    C("C14", "100nF", C0805, "+3V3_MOD", "GND", (571.5, 238.76), (60.7, 61.5, 90)),

    # --- Buttons (pull to GND, use internal pull-ups) ---
    BTNC("SW1", "UP", "BTN_UP", (66.04, 254.0), (21.5, 121.0)),
    BTNC("SW2", "DOWN", "BTN_DOWN", (66.04, 271.78), (21.5, 143.0)),
    BTNC("SW3", "LEFT", "BTN_LEFT", (66.04, 289.56), (10.0, 132.0)),
    BTNC("SW4", "RIGHT", "BTN_RIGHT", (104.14, 254.0), (33.0, 132.0)),
    BTNC("SW5", "OK", "BTN_OK", (104.14, 271.78), (106.0, 129.5)),
    BTNC("SW6", "BACK", "BTN_BACK", (104.14, 289.56), (92.0, 137.5)),
]

# Mounting holes (board only, not in the schematic)
MOUNTING = [("H1", 5.0, 5.0), ("H2", 111.0, 5.0), ("H3", 5.0, 165.0), ("H4", 111.0, 165.0)]

# Nets that need a PWR_FLAG for ERC
PWR_FLAG_NETS = ["+5V", "+5V_MOD", "GND"]

# Copper keep-out areas (both layers): (name, x1, y1, x2, y2)
KEEPOUTS = [("ESP32 antenna", 48.0, 95.0, 68.0, 107.3), ("PN532 antenna", 82.0, 55.0, 115.2, 95.4)]

# Silkscreen reference positions (board coords, angle). Unlisted parts keep the default.
REF_POS = {
    "D1": (31.5, 12.6, 0), "D2": (39.5, 12.6, 0), "D3": (76.5, 12.6, 0),
    "R5": (28.0, 16.2, 90), "R17": (36.0, 16.2, 90), "R18": (73.0, 16.2, 90),
    "Q1": (38.6, 24.8, 90), "R3": (42.8, 23.6, 90), "R4": (42.8, 28.4, 90),
    "C15": (35.9, 33.6, 90), "C11": (87.0, 9.6, 0), "R11": (87.0, 12.8, 0),
    "C1": (48.4, 44.0, 0), "C3": (8.2, 44.0, 0), "C5": (87.7, 44.0, 0),
    "C2": (62.6, 48.0, 0), "C4": (23.6, 48.0, 0), "C6": (102.4, 48.0, 0),
    "C9": (73.0, 103.1, 90), "JP1": (73.0, 116.3, 90), "C14": (62.6, 61.5, 90),
    "R1": (66.5, 64.5, 0), "R2": (66.5, 67.5, 0), "C7": (69.8, 76.2, 0),
    "R12": (49.0, 87.2, 0), "R13": (52.5, 87.2, 0), "R14": (56.0, 87.2, 0), "R15": (59.5, 87.2, 0),
    "SW7": (6.9, 158.0, 90), "Q3": (11.5, 146.4, 0), "R10": (15.2, 145.6, 0), "R16": (11.5, 155.9, 0),
    "C16": (16.5, 155.9, 0), "Q2": (39.0, 144.8, 0), "R6": (44.4, 158.6, 90), "R7": (44.4, 163.4, 90),
    "C17": (82.4, 140.9, 0),
}
