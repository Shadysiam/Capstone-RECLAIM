#!/usr/bin/env python3
"""
RECLAIM Prototype KiCad 10 Schematic Generator
Generates root index + 3 sub-sheets for prototype as-built wiring.

Sheets:
1. Power_Distribution — Battery, DC disconnect, fuse block, buck, servo rail
2. Teensy_Motor_Control — Teensy 4.1, MD13C R3, BTS7960, encoders, servo signals
3. Peripherals_Sensors — MIC-711, USB hub, Mango router, OAK-D, RPLIDAR

Run: python3 generate_prototype.py
Then open RECLAIM_Prototype.kicad_sch in KiCad 10.
"""

import uuid
import os

PROJECT = "/Users/shadysiam/Documents/RECLAIM/docs/prototype_pcb_electrical/kicad_project/RECLAIM_Prototype"

# UUIDs
ROOT_UUID = str(uuid.uuid4())
POWER_FILE_UUID = str(uuid.uuid4())
TEENSY_FILE_UUID = str(uuid.uuid4())
PERIPH_FILE_UUID = str(uuid.uuid4())
POWER_INST_UUID = str(uuid.uuid4())
TEENSY_INST_UUID = str(uuid.uuid4())
PERIPH_INST_UUID = str(uuid.uuid4())

def uid():
    return str(uuid.uuid4())

# ═══════════════════════════════════════════════
# Common header/footer
# ═══════════════════════════════════════════════

def header(file_uuid, paper, title):
    return f'''(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{file_uuid}")
\t(paper "{paper}")
\t(title_block
\t\t(title "RECLAIM Prototype — {title}")
\t\t(date "2026-04-10")
\t\t(rev "01")
\t\t(company "Western University / MSE 4499")
\t)
\t(lib_symbols
\t)
'''

def symbol_block(lib_id, x, y, ref, value, desc, inst_path, angle=0):
    """Generate a symbol instance block."""
    u = uid()
    return f'''
\t\t(symbol
\t\t\t(lib_id "{lib_id}")
\t\t\t(at {x} {y} {angle})
\t\t\t(unit 1)
\t\t\t(body_style 1)
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom yes)
\t\t\t(on_board yes)
\t\t\t(in_pos_files yes)
\t\t\t(dnp no)
\t\t\t(fields_autoplaced yes)
\t\t\t(uuid "{u}")
\t\t\t(property "Reference" "{ref}"
\t\t\t\t(at {x+2.54} {y-1.27} 0)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t\t)
\t\t\t(property "Value" "{value}"
\t\t\t\t(at {x+2.54} {y+1.27} 0)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t\t)
\t\t\t(property "Footprint" ""
\t\t\t\t(at {x} {y} 0)
\t\t\t\t(hide yes)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(property "Datasheet" ""
\t\t\t\t(at {x} {y} 0)
\t\t\t\t(hide yes)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(property "Description" "{desc}"
\t\t\t\t(at {x} {y} 0)
\t\t\t\t(hide yes)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(pin "1" (uuid "{uid()}"))
\t\t\t(pin "2" (uuid "{uid()}"))
\t\t\t(pin "3" (uuid "{uid()}"))
\t\t\t(pin "4" (uuid "{uid()}"))
\t\t\t(pin "5" (uuid "{uid()}"))
\t\t\t(pin "6" (uuid "{uid()}"))
\t\t\t(pin "7" (uuid "{uid()}"))
\t\t\t(pin "8" (uuid "{uid()}"))
\t\t\t(instances
\t\t\t\t(project "RECLAIM_Prototype"
\t\t\t\t\t(path "{inst_path}"
\t\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t\t(unit 1)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t)
\t\t)
'''

def label_block(text, x, y, angle=0):
    return f'''
\t\t(label "{text}"
\t\t\t(at {x} {y} {angle})
\t\t\t(fields_autoplaced yes)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t\t(uuid "{uid()}")
\t\t)
'''

def pwr_symbol(lib_id, x, y, ref, value, inst_path):
    u = uid()
    return f'''
\t\t(symbol
\t\t\t(lib_id "{lib_id}")
\t\t\t(at {x} {y} 0)
\t\t\t(unit 1)
\t\t\t(body_style 1)
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom no)
\t\t\t(on_board no)
\t\t\t(in_pos_files no)
\t\t\t(dnp no)
\t\t\t(fields_autoplaced yes)
\t\t\t(uuid "{u}")
\t\t\t(property "Reference" "{ref}"
\t\t\t\t(at {x} {y-2} 0)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)) hide)
\t\t\t)
\t\t\t(property "Value" "{value}"
\t\t\t\t(at {x} {y+2} 0)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(property "Footprint" ""
\t\t\t\t(at {x} {y} 0)
\t\t\t\t(hide yes)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(property "Datasheet" ""
\t\t\t\t(at {x} {y} 0)
\t\t\t\t(hide yes)
\t\t\t\t(show_name no)
\t\t\t\t(do_not_autoplace no)
\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t)
\t\t\t(pin "1" (uuid "{uid()}"))
\t\t\t(instances
\t\t\t\t(project "RECLAIM_Prototype"
\t\t\t\t\t(path "{inst_path}"
\t\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t\t(unit 1)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t)
\t\t)
'''


# ═══════════════════════════════════════════════
# ROOT INDEX SHEET
# ═══════════════════════════════════════════════

def gen_root():
    root_path = f"/{ROOT_UUID}"
    content = f'''(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A3")
\t(title_block
\t\t(title "RECLAIM Prototype — Index")
\t\t(date "2026-04-10")
\t\t(rev "01")
\t\t(company "Western University / MSE 4499")
\t)
\t(lib_symbols
\t)
\t\t(sheet
\t\t\t(at 40 60)
\t\t\t(size 80 30)
\t\t\t(fields_autoplaced yes)
\t\t\t(stroke (width 0.2) (type solid) (color 0 0 0 1))
\t\t\t(fill (color 255 255 255 1))
\t\t\t(uuid "{POWER_INST_UUID}")
\t\t\t(property "Sheetname" "Power_Distribution"
\t\t\t\t(at 40 59 0)
\t\t\t\t(effects (font (size 1.524 1.524)) (justify left bottom))
\t\t\t)
\t\t\t(property "Sheetfile" "Power_Distribution.kicad_sch"
\t\t\t\t(at 40 91 0)
\t\t\t\t(effects (font (size 1.016 1.016)) (justify left top))
\t\t\t)
\t\t)
\t\t(sheet
\t\t\t(at 150 60)
\t\t\t(size 80 30)
\t\t\t(fields_autoplaced yes)
\t\t\t(stroke (width 0.2) (type solid) (color 0 0 0 1))
\t\t\t(fill (color 255 255 255 1))
\t\t\t(uuid "{TEENSY_INST_UUID}")
\t\t\t(property "Sheetname" "Teensy_Motor_Control"
\t\t\t\t(at 150 59 0)
\t\t\t\t(effects (font (size 1.524 1.524)) (justify left bottom))
\t\t\t)
\t\t\t(property "Sheetfile" "Teensy_Motor_Control.kicad_sch"
\t\t\t\t(at 150 91 0)
\t\t\t\t(effects (font (size 1.016 1.016)) (justify left top))
\t\t\t)
\t\t)
\t\t(sheet
\t\t\t(at 260 60)
\t\t\t(size 80 30)
\t\t\t(fields_autoplaced yes)
\t\t\t(stroke (width 0.2) (type solid) (color 0 0 0 1))
\t\t\t(fill (color 255 255 255 1))
\t\t\t(uuid "{PERIPH_INST_UUID}")
\t\t\t(property "Sheetname" "Peripherals_Sensors"
\t\t\t\t(at 260 59 0)
\t\t\t\t(effects (font (size 1.524 1.524)) (justify left bottom))
\t\t\t)
\t\t\t(property "Sheetfile" "Peripherals_Sensors.kicad_sch"
\t\t\t\t(at 260 91 0)
\t\t\t\t(effects (font (size 1.016 1.016)) (justify left top))
\t\t\t)
\t\t)
)
'''
    return content


# ═══════════════════════════════════════════════
# SHEET 1: POWER DISTRIBUTION
# ═══════════════════════════════════════════════

def gen_power():
    inst = f"/{ROOT_UUID}/{POWER_INST_UUID}"
    pwr_n = [0]
    def pwr_ref():
        pwr_n[0] += 1
        return f"#PWR0{pwr_n[0]:02d}"

    content = header(POWER_FILE_UUID, "A3", "Power Distribution")

    # Power symbols
    content += pwr_symbol("power:+12V", 40, 30, pwr_ref(), "+12V", inst)
    content += pwr_symbol("power:GND", 60, 30, pwr_ref(), "GND", inst)
    content += pwr_symbol("power:PWR_FLAG", 48, 30, pwr_ref(), "PWR_FLAG", inst)
    content += pwr_symbol("power:PWR_FLAG", 68, 30, pwr_ref(), "PWR_FLAG", inst)

    # Battery connector
    content += symbol_block("Connector_Generic:Conn_01x02", 35, 70, "J_BAT", "Battery 12.8V", "ZapLitho 12.8V 22Ah LiFePO4", inst)

    # DC Disconnect
    content += symbol_block("Switch:SW_DPST", 65, 70, "SW_DC", "DC Disconnect", "3-pin battery disconnect switch", inst)

    # Fuse block (represented as individual fuses)
    content += symbol_block("Device:Fuse", 105, 55, "F1", "5A", "XINGYHENG buck servo rail", inst)
    content += symbol_block("Device:Fuse", 105, 75, "F2", "10A", "Cytron MD13C R3 left motor", inst)
    content += symbol_block("Device:Fuse", 105, 95, "F3", "10A", "MIC-711 IPC", inst)
    content += symbol_block("Device:Fuse", 105, 115, "F4", "20A", "BTS7960 right motor", inst)

    # Buck converter
    content += symbol_block("Connector_Generic:Conn_01x04", 165, 65, "U_BUCK", "XINGYHENG 12V-6.8V", "20A 300W step-down buck converter", inst)

    # Bulk cap
    content += symbol_block("Device:CP", 195, 75, "C_BULK", "10000uF 16V", "Servo rail bulk capacitor", inst)

    # Wago distribution (shown as connectors)
    content += symbol_block("Connector_Generic:Conn_01x05", 230, 55, "WAGO_V1", "221-415 VCC", "Servo VCC rail Wago J1-J3", inst)
    content += symbol_block("Connector_Generic:Conn_01x05", 230, 80, "WAGO_V2", "221-415 VCC", "Servo VCC rail Wago J4-J6", inst)
    content += symbol_block("Connector_Generic:Conn_01x05", 265, 55, "WAGO_G1", "221-415 GND", "Servo GND rail Wago J1-J3", inst)
    content += symbol_block("Connector_Generic:Conn_01x05", 265, 80, "WAGO_G2", "221-415 GND", "Servo GND rail Wago J4-J6", inst)

    # Servo connectors (power only)
    for i, (name, servo) in enumerate([
        ("J1 Base", "DS3218"), ("J2 Shoulder", "DS3235"), ("J3 Elbow", "DS3218"),
        ("J4 WristP", "DS3218"), ("J5 WristR", "MG996R"), ("J6 Gripper", "DS3218")
    ]):
        x = 310 + (i % 3) * 30
        y = 55 + (i // 3) * 35
        content += symbol_block("Connector_Generic:Conn_01x03", x, y, f"J{i+1}_PWR", f"{name}", f"{servo} power", inst)

    # Labels
    content += label_block("VBAT", 50, 65)
    content += label_block("VBAT_SWITCHED", 80, 65)
    content += label_block("VBAT_FUSED_1", 120, 52)
    content += label_block("VBAT_FUSED_2", 120, 72)
    content += label_block("VBAT_FUSED_3", 120, 92)
    content += label_block("VBAT_FUSED_4", 120, 112)
    content += label_block("V_SERVO", 185, 60)
    content += label_block("GND", 185, 90)

    content += "\n)\n"
    return content


# ═══════════════════════════════════════════════
# SHEET 2: TEENSY + MOTOR CONTROL
# ═══════════════════════════════════════════════

def gen_teensy():
    inst = f"/{ROOT_UUID}/{TEENSY_INST_UUID}"
    pwr_n = [0]
    def pwr_ref():
        pwr_n[0] += 1
        return f"#PWR1{pwr_n[0]:02d}"

    content = header(TEENSY_FILE_UUID, "A3", "Teensy & Motor Control")

    # Power
    content += pwr_symbol("power:+12V", 40, 25, pwr_ref(), "+12V", inst)
    content += pwr_symbol("power:GND", 60, 25, pwr_ref(), "GND", inst)
    content += pwr_symbol("power:+3V3", 80, 25, pwr_ref(), "+3V3", inst)

    # Teensy 4.1 (use generic large connector to represent)
    content += symbol_block("Connector_Generic:Conn_02x24", 130, 90, "U_MCU", "Teensy 4.1", "ARM Cortex-M7 600MHz", inst)

    # Cytron MD13C R3 (left motor driver)
    content += symbol_block("Connector_Generic:Conn_01x06", 45, 70, "U_DRV_L", "MD13C R3", "Cytron 30A motor driver left", inst)

    # BTS7960 (right motor driver)
    content += symbol_block("Connector_Generic:Conn_01x08", 45, 130, "U_DRV_R", "BTS7960", "43A motor driver right (replaced fried MD13C)", inst)

    # Left motor + encoder
    content += symbol_block("Connector_Generic:Conn_01x06", 270, 65, "M_L", "JGB37-520 L", "12V 37RPM motor+encoder left", inst)

    # Right motor + encoder
    content += symbol_block("Connector_Generic:Conn_01x06", 270, 115, "M_R", "JGB37-520 R", "12V 37RPM motor+encoder right", inst)

    # Servo signal connectors
    for i, (name, pin) in enumerate([
        ("J1 Base P10", "DS3218"), ("J2 Shldr P11", "DS3235"), ("J3 Elbow P12", "DS3218"),
        ("J4 WrstP P13", "DS3218"), ("J5 WrstR P14", "MG996R"), ("J6 Grip P15", "DS3218")
    ]):
        x = 270 + (i % 3) * 35
        y = 170 + (i // 3) * 30
        content += symbol_block("Connector_Generic:Conn_01x01", x, y, f"SIG_J{i+1}", f"{name}", f"Servo signal to {pin}", inst)

    # Net labels — motor drivers
    content += label_block("VBAT_FUSED_2", 45, 60)
    content += label_block("PWM_L", 80, 68)
    content += label_block("DIR_L", 80, 73)
    content += label_block("MOTOR_L+", 65, 78)
    content += label_block("MOTOR_L-", 65, 83)
    content += label_block("GND", 45, 90)

    content += label_block("VBAT_FUSED_4", 45, 120)
    content += label_block("LPWM_R", 80, 128)
    content += label_block("RPWM_R", 80, 133)
    content += label_block("MOTOR_R+", 65, 140)
    content += label_block("MOTOR_R-", 65, 145)
    content += label_block("BTS_R_EN", 80, 150)
    content += label_block("BTS_L_EN", 80, 155)
    content += label_block("GND", 45, 160)

    # Teensy pin labels
    content += label_block("PWM_L", 110, 75)       # Pin 2
    content += label_block("DIR_L", 110, 78)        # Pin 3
    content += label_block("ENC_L_A", 110, 84)      # Pin 6
    content += label_block("ENC_L_B", 110, 87)      # Pin 7
    content += label_block("SERVO_J1", 155, 80)     # Pin 10
    content += label_block("SERVO_J2", 155, 83)     # Pin 11
    content += label_block("SERVO_J3", 155, 86)     # Pin 12
    content += label_block("SERVO_J4", 155, 89)     # Pin 13
    content += label_block("SERVO_J5", 155, 92)     # Pin 14
    content += label_block("SERVO_J6", 155, 95)     # Pin 15
    content += label_block("ENC_R_B", 155, 100)     # Pin 18
    content += label_block("ENC_R_A", 155, 103)     # Pin 19
    content += label_block("RPWM_R", 155, 108)      # Pin 22
    content += label_block("LPWM_R", 155, 111)      # Pin 23

    # Encoder labels
    content += label_block("ENC_L_A", 270, 75)
    content += label_block("ENC_L_B", 270, 78)
    content += label_block("ENC_R_A", 270, 125)
    content += label_block("ENC_R_B", 270, 128)

    content += "\n)\n"
    return content


# ═══════════════════════════════════════════════
# SHEET 3: PERIPHERALS & SENSORS
# ═══════════════════════════════════════════════

def gen_peripherals():
    inst = f"/{ROOT_UUID}/{PERIPH_INST_UUID}"
    pwr_n = [0]
    def pwr_ref():
        pwr_n[0] += 1
        return f"#PWR2{pwr_n[0]:02d}"

    content = header(PERIPH_FILE_UUID, "A3", "Peripherals & Sensors")

    # Power
    content += pwr_symbol("power:+12V", 40, 25, pwr_ref(), "+12V", inst)
    content += pwr_symbol("power:GND", 60, 25, pwr_ref(), "GND", inst)
    content += pwr_symbol("power:+5V", 80, 25, pwr_ref(), "+5V", inst)

    # MIC-711 IPC
    content += symbol_block("Connector_Generic:Conn_01x08", 60, 70, "U_IPC", "MIC-711", "Advantech IPC Jetson Orin NX", inst)

    # USB Hub
    content += symbol_block("Connector_Generic:Conn_01x04", 150, 65, "U_HUB", "USB Hub", "USB 2.0 hub", inst)

    # Teensy USB (from hub)
    content += symbol_block("Connector_Generic:Conn_01x01", 210, 60, "J_TEENSY_USB", "Teensy USB", "To Teensy 4.1 USB", inst)

    # Mango Router
    content += symbol_block("Connector_Generic:Conn_01x03", 210, 80, "U_ROUTER", "GL.iNet Mango", "Travel router ethernet+USB", inst)

    # OAK-D Lite
    content += symbol_block("Connector_Generic:Conn_01x01", 150, 120, "U_CAM", "OAK-D Lite", "Stereo depth camera USB 3.0", inst)

    # RPLIDAR
    content += symbol_block("Connector_Generic:Conn_01x01", 150, 145, "U_LIDAR", "RPLIDAR A1M8", "360deg laser scanner USB", inst)

    # Labels
    content += label_block("VBAT_FUSED_3", 45, 60)
    content += label_block("GND", 45, 90)
    content += label_block("USB_3.0", 100, 115)
    content += label_block("USB_2.0", 100, 80)
    content += label_block("ETHERNET", 100, 75)
    content += label_block("V_5V_USB", 140, 55)

    content += "\n)\n"
    return content


# ═══════════════════════════════════════════════
# KiCad project file
# ═══════════════════════════════════════════════

def gen_kicad_pro():
    return '''{
  "meta": {
    "filename": "RECLAIM_Prototype.kicad_pro",
    "version": 2
  },
  "schematic": {
    "drawing": {},
    "meta": {
      "version": 1
    }
  }
}
'''

def gen_sym_lib_table():
    return '''(sym_lib_table
  (version 7)
)
'''

def gen_fp_lib_table():
    return '''(fp_lib_table
  (version 7)
)
'''


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    os.makedirs(PROJECT, exist_ok=True)

    files = {
        "RECLAIM_Prototype.kicad_sch": gen_root(),
        "Power_Distribution.kicad_sch": gen_power(),
        "Teensy_Motor_Control.kicad_sch": gen_teensy(),
        "Peripherals_Sensors.kicad_sch": gen_peripherals(),
        "RECLAIM_Prototype.kicad_pro": gen_kicad_pro(),
        "sym-lib-table": gen_sym_lib_table(),
        "fp-lib-table": gen_fp_lib_table(),
    }

    for name, content in files.items():
        path = os.path.join(PROJECT, name)
        with open(path, 'w') as f:
            f.write(content)
        print(f"  Created: {name}")

    print(f"\nPrototype schematic generated at:\n  {PROJECT}/")
    print("Open RECLAIM_Prototype.kicad_sch in KiCad 10.")
