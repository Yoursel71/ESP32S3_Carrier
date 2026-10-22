"""ESP32-S3 tasiyici kart - tek kaynak tasarim verisi.

Sema (.kicad_sch) ve PCB (.kicad_pcb) bu dosyadan uretilir.
Koordinatlar mm. PCB: kart sol ust kosesi (0,0), y asagi dogru.
"""

PROJE = "ESP32S3_Tasiyici"
TARIH = "2026-10-22"
REV = "1.0"

# Kart olculeri
W = 116.0
H = 155.0
KOSE_R = 4.0
# A4 dikey sayfada kartin konumu (1:1 PDF icin)
OX = 47.0
OY = 42.0

# Net siniflari: (iz genisligi, bosluk)
NET_SINIFLARI = {
    "Default": dict(track=0.25, clearance=0.2, via_d=0.6, via_drill=0.3),
    "Guc": dict(track=0.6, clearance=0.25, via_d=0.8, via_drill=0.4),
    "GND": dict(track=0.5, clearance=0.25, via_d=0.8, via_drill=0.4),
}
NET_SINIF_ATAMA = {
    "+5V": "Guc", "+5V_MOD": "Guc", "+3V3_MOD": "Guc", "GND": "GND",
    "/IR_LED_A": "Guc", "/IR_LED_K": "Guc", "/BUZ_NEG": "Guc",
}

R0805 = "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"
R1206 = "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder"
C0805 = "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"
C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"
CP63 = "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"
CP8 = "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"
BTN = "Button_Switch_THT:SW_PUSH_6mm"
TO92 = "Package_TO_SOT_THT:TO-92_Inline_Wide"

# DevKitC-1 pin adlari (ust gorunum, anten yukari). J1 = sol sira, J3 = sag sira.
DEVKIT_J1 = ["3V3", "3V3", "RST", "IO4", "IO5", "IO6", "IO7", "IO15", "IO16", "IO17", "IO18",
             "IO8", "IO3", "IO46", "IO9", "IO10", "IO11", "IO12", "IO13", "IO14", "5V", "GND"]
DEVKIT_J3 = ["GND", "TX", "RX", "IO1", "IO2", "IO42", "IO41", "IO40", "IO39", "IO38", "IO37",
             "IO36", "IO35", "IO0", "IO45", "IO48", "IO47", "IO21", "IO20", "IO19", "GND", "GND"]

# ESP32 GPIO -> net
GPIO_NET = {
    "IO4": "NRF1_CE", "IO5": "NRF1_CSN", "IO6": "NRF2_CE", "IO7": "NRF2_CSN",
    "IO15": "BTN_UP", "IO16": "BTN_DOWN", "IO38": "BTN_LEFT", "IO39": "BTN_RIGHT",
    "IO40": "BTN_OK", "IO41": "BTN_BACK",
    "IO17": "RFID_TX", "IO18": "I2C_SCL", "IO8": "I2C_SDA",
    "IO9": "CC_GDO0", "IO10": "CC_CS", "IO11": "SPI_MOSI", "IO12": "SPI_SCK", "IO13": "SPI_MISO",
    "IO14": "SD_CS", "IO1": "IR_RX", "IO2": "IR_TX", "IO47": "BUZ",
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
    # SW_PUSH_6mm orijini pad1; govde merkezi (3.25, 2.25)
    return dict(ref=ref, val=val, sym="Switch:SW_Push", fp=BTN, pins={"1": net, "2": "GND"},
                sch=sch, pcb=(center[0] - 3.25, center[1] - 2.25, 0), etiket=val)


# pcb: (x, y, aci_derece)  sch: (x, y)
BILESENLER = [
    # --- Moduller (disi header soketleri) ---
    dict(ref="U1", val="ESP32-S3-DevKitC-1 N16R8", sym="Tasiyici:ESP32-S3-DevKitC-1",
         fp="Tasiyici:ESP32-S3-DevKitC-1_Soket", pins=devkit_pins(), sch=(101.6, 152.4), pcb=(46.57, 93.66, 0)),
    dict(ref="J1", val="CC1101 433MHz SMA", sym="Tasiyici:CC1101_SMA_2x4", fp="Tasiyici:CC1101_SMA_2x4_Soket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "CC_GDO0", "4": "CC_CS", "5": "SPI_SCK", "6": "SPI_MOSI",
               "7": "SPI_MISO", "8": None}, sch=(228.6, 63.5), pcb=(20.19, 36.8, 0)),
    dict(ref="J2", val="NRF24L01+PA+LNA #1", sym="Tasiyici:NRF24L01_PA_LNA", fp="Tasiyici:NRF24L01_PA_LNA_Soket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "NRF1_CE", "4": "NRF1_CSN", "5": "SPI_SCK", "6": "SPI_MOSI",
               "7": "SPI_MISO", "8": None}, sch=(228.6, 106.68), pcb=(53.69, 37.8, 0)),
    dict(ref="J3", val="NRF24L01+PA+LNA #2", sym="Tasiyici:NRF24L01_PA_LNA", fp="Tasiyici:NRF24L01_PA_LNA_Soket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "NRF2_CE", "4": "NRF2_CSN", "5": "SPI_SCK", "6": "SPI_MOSI",
               "7": "SPI_MISO", "8": None}, sch=(228.6, 149.86), pcb=(81.69, 37.8, 0)),
    dict(ref="J4", val="PN532 V3 (I2C)", sym="Tasiyici:PN532_I2C", fp="Tasiyici:PN532_V3_I2C_Soket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "I2C_SDA", "4": "I2C_SCL"}, sch=(360.68, 63.5), pcb=(79.0, 71.09, 0)),
    dict(ref="J5", val="OLED 1.3in SH1106 I2C", sym="Tasiyici:OLED_SH1106_I2C", fp="Tasiyici:OLED_1.3in_I2C_Soket",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "I2C_SCL", "4": "I2C_SDA"}, sch=(360.68, 99.06), pcb=(17.69, 54.6, 0)),
    dict(ref="J6", val="Catalex microSD", sym="Tasiyici:microSD_Catalex", fp="Tasiyici:microSD_Catalex_Soket",
         pins={"1": "GND", "2": "+5V_MOD", "3": "SD_MISO_RAW", "4": "SPI_MOSI", "5": "SPI_SCK", "6": "SD_CS"},
         sch=(228.6, 198.12), pcb=(76.7, 105.15, 0)),
    dict(ref="J7", val="RDM6300 125kHz", sym="Tasiyici:RDM6300", fp="Tasiyici:RDM6300_Soket",
         pins={"1": "RFID_TX5V", "2": None, "3": None, "4": "GND", "5": "+5V_MOD", "6": "RFID_ANT1", "7": "RFID_ANT2"},
         sch=(360.68, 152.4), pcb=(37.6, 107.4, 0)),
    dict(ref="J8", val="125kHz bobin", sym="Connector_Generic:Conn_01x02",
         fp="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
         pins={"1": "RFID_ANT1", "2": "RFID_ANT2"}, sch=(406.4, 182.88), pcb=(4.0, 112.5, 90)),

    # --- Dekuplaj ---
    C("C1", "100nF", C0805, "+3V3_MOD", "GND", (271.78, 63.5), (17.0, 44.0, 0)),
    CP("C2", "100uF", CP63, "+3V3_MOD", "GND", (284.48, 63.5), (24.5, 48.0, 0)),
    C("C3", "100nF", C0805, "+3V3_MOD", "GND", (271.78, 106.68), (50.5, 44.0, 0)),
    CP("C4", "100uF", CP63, "+3V3_MOD", "GND", (284.48, 106.68), (57.0, 48.0, 0)),
    C("C5", "100nF", C0805, "+3V3_MOD", "GND", (271.78, 149.86), (78.5, 44.0, 0)),
    CP("C6", "100uF", CP63, "+3V3_MOD", "GND", (284.48, 149.86), (85.0, 48.0, 0)),
    C("C7", "100nF", C0805, "+3V3_MOD", "GND", (391.16, 63.5), (69.8, 72.5, 90)),
    C("C8", "100nF", C0805, "+3V3_MOD", "GND", (391.16, 99.06), (12.0, 50.9, 0)),
    C("C9", "100nF", C0805, "+5V_MOD", "GND", (271.78, 198.12), (72.9, 106.5, 90)),
    C("C10", "100nF", C0805, "+5V_MOD", "GND", (391.16, 152.4), (24.0, 111.5, 0)),
    C("C11", "100nF", C0805, "+3V3_MOD", "GND", (322.58, 251.46), (71.5, 10.0, 0)),

    # --- I2C pull-up ---
    R("R1", "4.7k", R0805, "+3V3_MOD", "I2C_SDA", (424.18, 63.5), (63.5, 64.5, 0)),
    R("R2", "4.7k", R0805, "+3V3_MOD", "I2C_SCL", (436.88, 63.5), (63.5, 67.5, 0)),

    # --- microSD MISO kesilebilir kopru ---
    dict(ref="JP1", val="SD_MISO", sym="Jumper:SolderJumper_2_Bridged",
         fp="Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm",
         pins={"1": "SD_MISO_RAW", "2": "SPI_MISO"}, sch=(279.4, 228.6), pcb=(73.0, 112.1, 90)),

    # --- RDM6300 TX 5V -> 3.3V bolucu ---
    R("R8", "4.7k", R0805, "RFID_TX5V", "RFID_TX", (406.4, 152.4), (41.5, 113.0, 0)),
    R("R9", "10k", R0805, "RFID_TX", "GND", (419.1, 152.4), (41.5, 116.2, 0)),

    # --- IR verici ---
    dict(ref="D1", val="IR LED 940nm", sym="Device:LED", fp="LED_THT:LED_D5.0mm_Horizontal_O1.27mm_Z3.0mm",
         pins={"1": "IR_LED_K", "2": "IR_LED_A"}, sch=(208.28, 251.46), pcb=(44.52, 10.6, 180)),
    dict(ref="Q1", val="PN2222A", sym="Tasiyici:PN2222A", fp=TO92,
         pins={"1": "GND", "2": "IR_BASE", "3": "IR_LED_K"}, sch=(208.28, 271.78), pcb=(40.71, 16.8, 0)),
    R("R3", "220", R0805, "IR_TX", "IR_BASE", (185.42, 274.32), (41.0, 23.0, 90)),
    R("R4", "10k", R0805, "IR_BASE", "GND", (195.58, 284.48), (45.5, 23.0, 90)),
    R("R5", "47", R1206, "+5V_MOD", "IR_LED_A", (223.52, 238.76), (43.25, 29.5, 0)),

    # --- IR alici ---
    dict(ref="U3", val="VS1838B", sym="Tasiyici:VS1838B", fp="OptoDevice:Vishay_MINICAST-3Pin",
         pins={"1": "IR_RX", "2": "GND", "3": "+3V3_MOD"}, sch=(304.8, 254.0), pcb=(68.96, 4.0, 0)),

    # --- Buzzer surucu ---
    dict(ref="BZ1", val="Pasif buzzer", sym="Device:Buzzer", fp="Buzzer_Beeper:Buzzer_12x9.5RM7.6",
         pins={"1": "+5V_MOD", "2": "BUZ_NEG"}, sch=(363.22, 248.92), pcb=(97.2, 22.0, 0)),
    dict(ref="D2", val="1N4148", sym="Device:D", fp="Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal",
         pins={"1": "+5V_MOD", "2": "BUZ_NEG"}, sch=(381.0, 248.92), pcb=(96.5, 37.4, 0)),
    dict(ref="Q2", val="PN2222A", sym="Tasiyici:PN2222A", fp=TO92,
         pins={"1": "GND", "2": "BUZ_BASE", "3": "BUZ_NEG"}, sch=(363.22, 271.78), pcb=(97.0, 32.0, 0)),
    R("R6", "1k", R0805, "BUZ", "BUZ_BASE", (340.36, 274.32), (98.5, 42.6, 0)),
    R("R7", "10k", R0805, "BUZ_BASE", "GND", (350.52, 284.48), (104.2, 42.6, 0)),

    # --- Modul guc anahtari (P-MOSFET) + 3V3 regulator ---
    dict(ref="SW7", val="MODUL GUC", sym="Switch:SW_SPDT", fp="Button_Switch_THT:SW_Slide_SPDT_Angled_CK_OS102011MA1Q",
         pins={"1": "GND", "2": "PWR_GATE", "3": None}, sch=(444.5, 228.6), pcb=(32.5, 152.4, 0)),
    R("R10", "100k", R0805, "+5V", "PWR_GATE", (469.9, 215.9), (40.6, 145.4, 90)),
    dict(ref="Q3", val="AO3401A", sym="Tasiyici:AO3401A", fp="Package_TO_SOT_SMD:SOT-23",
         pins={"1": "PWR_GATE", "2": "+5V", "3": "+5V_MOD"}, sch=(477.52, 233.68), pcb=(36.6, 145.4, 0)),
    dict(ref="U2", val="AMS1117-3.3", sym="Tasiyici:AMS1117-3.3", fp="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
         pins={"1": "GND", "2": "+3V3_MOD", "3": "+5V_MOD"}, sch=(533.4, 233.68), pcb=(55.0, 60.0, 0)),
    C("C12", "10uF", C1206, "+5V_MOD", "GND", (510.54, 238.76), (48.9, 62.5, 90)),
    CP("C13", "470uF", CP8, "+3V3_MOD", "GND", (558.8, 238.76), (52.0, 72.4, 0)),
    C("C14", "100nF", C0805, "+3V3_MOD", "GND", (571.5, 238.76), (60.7, 61.5, 90)),

    # --- Butonlar (GND'ye ceker) ---
    BTNC("SW1", "UP", "BTN_UP", (66.04, 254.0), (21.5, 119.0)),
    BTNC("SW2", "DOWN", "BTN_DOWN", (66.04, 271.78), (21.5, 141.0)),
    BTNC("SW3", "LEFT", "BTN_LEFT", (66.04, 289.56), (10.0, 130.0)),
    BTNC("SW4", "RIGHT", "BTN_RIGHT", (104.14, 254.0), (33.0, 130.0)),
    BTNC("SW5", "OK", "BTN_OK", (104.14, 271.78), (104.0, 132.0)),
    BTNC("SW6", "BACK", "BTN_BACK", (104.14, 289.56), (91.0, 141.0)),
]

# Montaj delikleri (sadece kart, semada yok)
MONTAJ = [("H1", 5.0, 5.0), ("H2", 111.0, 5.0), ("H3", 5.0, 150.0), ("H4", 111.0, 150.0)]

# PWR_FLAG gereken netler (ERC icin)
PWR_FLAG_NETLER = ["+5V", "+5V_MOD", "GND"]

# Serigrafi referans konumlari (kart koordinati, aci). Listede olmayan varsayilan kalir.
REF_YER = {
    "D1": (47.6, 6.5, 90), "Q1": (47.6, 16.8, 90), "C11": (75.0, 10.0, 0), "BZ1": (101.0, 14.6, 0),
    "C1": (14.2, 44.0, 0), "C3": (47.6, 44.0, 0), "C5": (75.6, 44.0, 0), "Q2": (95.0, 32.0, 90), "SW7": (42.3, 150.6, 0),
    "C2": (30.6, 48.0, 0), "C4": (63.1, 48.0, 0), "C6": (91.1, 48.0, 0),
    "C9": (73.0, 103.1, 90), "JP1": (73.0, 116.3, 90), "C14": (62.6, 61.5, 90),
    "R1": (66.5, 64.5, 0), "R2": (66.5, 67.5, 0), "C7": (69.8, 76.2, 0),
}
