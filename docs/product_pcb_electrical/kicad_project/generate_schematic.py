#!/usr/bin/env python3
"""
RECLAIM PCB KiCad 10 Schematic Generator
Generates/updates all 4 sub-sheets with components and net labels.
"""

import uuid
import shutil
import os
from datetime import datetime

PROJECT_DIR = "/Users/shadysiam/Documents/RECLAIM/docs/product_pcb_electrical/kicad_project/RECLAIM_PCB"
CUSTOM_LIBS_DIR = "/Users/shadysiam/Documents/RECLAIM/docs/product_pcb_electrical/kicad_project/custom_libs"

# Sheet UUIDs (must match RECLAIM_PCB.kicad_sch references)
ROOT_SHEET_UUID = "7765fcd9-2167-4c42-bf78-4e956d4b2573"
POWER_SHEET_UUID = "9f998912-ae44-4bd2-8dfb-c414ea7bb4a8"   # instance uuid from root
STM32_SHEET_UUID = "86b4d3a1-1b92-4b0c-9cda-b512cbf2aa55"   # instance uuid from root
CONNECTORS_SHEET_UUID = "88ba7e59-b0ab-4975-9341-2fcbd61e0288"
DRIVERS_SHEET_UUID = "c28c40f2-0b96-41a6-9b79-eef9e5f5e43d"

# File UUIDs (the uuid at top of each .kicad_sch file)
POWER_FILE_UUID = "bf4f5b1e-117b-4829-b38d-21956d2555cd"
STM32_FILE_UUID = "1e8ec03d-1297-4e19-b6ae-d65c2bff1a43"
DRIVERS_FILE_UUID = "8aa666fd-8fd8-4514-ae6b-072cd70ff812"
CONNECTORS_FILE_UUID = "bdf2989d-69db-4883-a2ad-aaa72fd3c55d"

def uid():
    return str(uuid.uuid4())

def backup_file(path):
    if os.path.exists(path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = path + f".bak_{ts}"
        shutil.copy2(path, dst)
        print(f"  Backed up: {os.path.basename(path)} -> {os.path.basename(dst)}")

# ─────────────────────────────────────────────────────────────────────────────
# Low-level KiCad S-expression helpers
# ─────────────────────────────────────────────────────────────────────────────

def prop(name, value, at_x, at_y, angle=0, hide=False, justify=None, size=1.27):
    h = "\n\t\t\t(hide yes)" if hide else ""
    j = f"\n\t\t\t\t(justify {justify})" if justify else ""
    return f"""
\t\t(property "{name}" "{value}"
\t\t\t(at {at_x} {at_y} {angle})
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no){h}
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size {size} {size})
\t\t\t\t){j}
\t\t\t)
\t\t)"""

def pin_entry(num, pin_uuid):
    return f'\n\t\t(pin "{num}"\n\t\t\t(uuid "{pin_uuid}")\n\t\t)'

def instances_block(sheet_file_uuid, sheet_instance_uuid, reference, unit=1):
    """Generate the instances block referencing root sheet → sub-sheet path."""
    return f"""
\t\t(instances
\t\t\t(project "RECLAIM_PCB"
\t\t\t\t(path "/{ROOT_SHEET_UUID}/{sheet_instance_uuid}"
\t\t\t\t\t(reference "{reference}")
\t\t\t\t\t(unit {unit})
\t\t\t\t)
\t\t\t)
\t\t)"""

def label(net_name, x, y, angle=0):
    """KiCad 10 net label."""
    return f"""
\t(label "{net_name}"
\t\t(at {x} {y} {angle})
\t\t(fields_autoplaced yes)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "{uid()}")
\t)"""

def place_symbol(lib_id, x, y, sheet_instance_uuid, reference, value,
                 footprint="", datasheet="", description="",
                 extra_props=None, pin_uuids=None, angle=0,
                 unit=1, dnp=False, in_bom=True, on_board=True):
    """
    Emit one placed symbol instance.
    pin_uuids: dict of {pin_number_str: uuid_str}  — must include ALL pins of the symbol.
    extra_props: list of (name, value, x, y, hide) tuples for additional properties.
    """
    sym_uuid = uid()
    dnp_str = "yes" if dnp else "no"
    bom_str = "yes" if in_bom else "no"
    ob_str = "yes" if on_board else "no"

    # Reference property (shown, slightly offset)
    ref_x = round(x + 2.54, 3)
    ref_y = round(y - 1.27, 3)
    val_x = round(x + 2.54, 3)
    val_y = round(y + 1.27, 3)

    lines = [f"""
\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {angle})
\t\t(unit {unit})
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom {bom_str})
\t\t(on_board {ob_str})
\t\t(in_pos_files yes)
\t\t(dnp {dnp_str})
\t\t(fields_autoplaced yes)
\t\t(uuid "{sym_uuid}")"""]

    lines.append(prop("Reference", reference, ref_x, ref_y, justify="left"))
    lines.append(prop("Value", value, val_x, val_y, justify="left"))
    lines.append(prop("Footprint", footprint, x, y, hide=True))
    lines.append(prop("Datasheet", datasheet, x, y, hide=True))
    lines.append(prop("Description", description, x, y, hide=True))

    if extra_props:
        for ep in extra_props:
            ep_name, ep_val, ep_x, ep_y, ep_hide = ep
            lines.append(prop(ep_name, ep_val, ep_x, ep_y, hide=ep_hide))

    if pin_uuids:
        for pnum, puuid in pin_uuids.items():
            lines.append(pin_entry(pnum, puuid))

    lines.append(instances_block(None, sheet_instance_uuid, reference, unit))
    lines.append("\n\t)")
    return "".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# Custom library symbol definitions (KiCad 10 format, embedded in lib_symbols)
# ─────────────────────────────────────────────────────────────────────────────

DRV8243_SYMBOL = r"""
		(symbol "2026-04-10_02-12-54:DRV8243SQDGQRQ1"
			(pin_names
				(offset 0.254)
			)
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(in_pos_files yes)
			(duplicate_pin_numbers_are_jumpers no)
			(property "Reference" "U"
				(at 25.4 10.16 0)
				(show_name no)
				(do_not_autoplace no)
				(effects
					(font
						(size 1.524 1.524)
					)
				)
			)
			(property "Value" "DRV8243SQDGQRQ1"
				(at 25.4 7.62 0)
				(show_name no)
				(do_not_autoplace no)
				(effects
					(font
						(size 1.524 1.524)
					)
				)
			)
			(property "Footprint" "VSSOP28_DGQ_TEX"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
						(italic yes)
					)
				)
			)
			(property "Datasheet" "https://www.ti.com/lit/gpn/drv8243-q1"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
						(italic yes)
					)
				)
			)
			(property "Description" "DRV8243 automotive H-bridge motor driver"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(symbol "DRV8243SQDGQRQ1_0_1"
				(polyline
					(pts
						(xy 7.62 5.08) (xy 7.62 -40.64)
					)
					(stroke (width 0.127) (type default))
					(fill (type none))
				)
				(polyline
					(pts
						(xy 7.62 -40.64) (xy 43.18 -40.64)
					)
					(stroke (width 0.127) (type default))
					(fill (type none))
				)
				(polyline
					(pts
						(xy 43.18 -40.64) (xy 43.18 5.08)
					)
					(stroke (width 0.127) (type default))
					(fill (type none))
				)
				(polyline
					(pts
						(xy 43.18 5.08) (xy 7.62 5.08)
					)
					(stroke (width 0.127) (type default))
					(fill (type none))
				)
				(pin input line
					(at 0 0 0)
					(length 7.62)
					(name "SCLK" (effects (font (size 1.27 1.27))))
					(number "1" (effects (font (size 1.27 1.27))))
				)
				(pin input line
					(at 0 -2.54 0)
					(length 7.62)
					(name "NSCS" (effects (font (size 1.27 1.27))))
					(number "2" (effects (font (size 1.27 1.27))))
				)
				(pin input line
					(at 0 -5.08 0)
					(length 7.62)
					(name "PH/IN2" (effects (font (size 1.27 1.27))))
					(number "3" (effects (font (size 1.27 1.27))))
				)
				(pin input line
					(at 0 -7.62 0)
					(length 7.62)
					(name "EN/IN1" (effects (font (size 1.27 1.27))))
					(number "4" (effects (font (size 1.27 1.27))))
				)
				(pin input line
					(at 0 -10.16 0)
					(length 7.62)
					(name "DRVOFF" (effects (font (size 1.27 1.27))))
					(number "5" (effects (font (size 1.27 1.27))))
				)
				(pin power_in line
					(at 0 -12.7 0)
					(length 7.62)
					(name "VM" (effects (font (size 1.27 1.27))))
					(number "6" (effects (font (size 1.27 1.27))))
				)
				(pin power_in line
					(at 0 -15.24 0)
					(length 7.62)
					(name "VM" (effects (font (size 1.27 1.27))))
					(number "7" (effects (font (size 1.27 1.27))))
				)
				(pin power_in line
					(at 0 -17.78 0)
					(length 7.62)
					(name "VM" (effects (font (size 1.27 1.27))))
					(number "8" (effects (font (size 1.27 1.27))))
				)
				(pin output line
					(at 0 -20.32 0)
					(length 7.62)
					(name "OUT1" (effects (font (size 1.27 1.27))))
					(number "9" (effects (font (size 1.27 1.27))))
				)
				(pin output line
					(at 0 -22.86 0)
					(length 7.62)
					(name "OUT1" (effects (font (size 1.27 1.27))))
					(number "10" (effects (font (size 1.27 1.27))))
				)
				(pin output line
					(at 0 -25.4 0)
					(length 7.62)
					(name "OUT1" (effects (font (size 1.27 1.27))))
					(number "11" (effects (font (size 1.27 1.27))))
				)
				(pin power_out line
					(at 0 -27.94 0)
					(length 7.62)
					(name "GND" (effects (font (size 1.27 1.27))))
					(number "12" (effects (font (size 1.27 1.27))))
				)
				(pin power_out line
					(at 0 -30.48 0)
					(length 7.62)
					(name "GND" (effects (font (size 1.27 1.27))))
					(number "13" (effects (font (size 1.27 1.27))))
				)
				(pin power_out line
					(at 0 -33.02 0)
					(length 7.62)
					(name "GND" (effects (font (size 1.27 1.27))))
					(number "14" (effects (font (size 1.27 1.27))))
				)
				(pin power_out line
					(at 50.8 -35.56 180)
					(length 7.62)
					(name "GND" (effects (font (size 1.27 1.27))))
					(number "15" (effects (font (size 1.27 1.27))))
				)
				(pin power_out line
					(at 50.8 -33.02 180)
					(length 7.62)
					(name "GND" (effects (font (size 1.27 1.27))))
					(number "16" (effects (font (size 1.27 1.27))))
				)
				(pin power_out line
					(at 50.8 -30.48 180)
					(length 7.62)
					(name "GND" (effects (font (size 1.27 1.27))))
					(number "17" (effects (font (size 1.27 1.27))))
				)
				(pin output line
					(at 50.8 -27.94 180)
					(length 7.62)
					(name "OUT2" (effects (font (size 1.27 1.27))))
					(number "18" (effects (font (size 1.27 1.27))))
				)
				(pin output line
					(at 50.8 -25.4 180)
					(length 7.62)
					(name "OUT2" (effects (font (size 1.27 1.27))))
					(number "19" (effects (font (size 1.27 1.27))))
				)
				(pin output line
					(at 50.8 -22.86 180)
					(length 7.62)
					(name "OUT2" (effects (font (size 1.27 1.27))))
					(number "20" (effects (font (size 1.27 1.27))))
				)
				(pin power_in line
					(at 50.8 -20.32 180)
					(length 7.62)
					(name "VM" (effects (font (size 1.27 1.27))))
					(number "21" (effects (font (size 1.27 1.27))))
				)
				(pin power_in line
					(at 50.8 -17.78 180)
					(length 7.62)
					(name "VM" (effects (font (size 1.27 1.27))))
					(number "22" (effects (font (size 1.27 1.27))))
				)
				(pin power_in line
					(at 50.8 -15.24 180)
					(length 7.62)
					(name "VM" (effects (font (size 1.27 1.27))))
					(number "23" (effects (font (size 1.27 1.27))))
				)
				(pin input line
					(at 50.8 -12.7 180)
					(length 7.62)
					(name "NSLEEP" (effects (font (size 1.27 1.27))))
					(number "24" (effects (font (size 1.27 1.27))))
				)
				(pin bidirectional line
					(at 50.8 -10.16 180)
					(length 7.62)
					(name "IPROPI" (effects (font (size 1.27 1.27))))
					(number "25" (effects (font (size 1.27 1.27))))
				)
				(pin output line
					(at 50.8 -7.62 180)
					(length 7.62)
					(name "NFAULT" (effects (font (size 1.27 1.27))))
					(number "26" (effects (font (size 1.27 1.27))))
				)
				(pin output line
					(at 50.8 -5.08 180)
					(length 7.62)
					(name "SDO" (effects (font (size 1.27 1.27))))
					(number "27" (effects (font (size 1.27 1.27))))
				)
				(pin input line
					(at 50.8 -2.54 180)
					(length 7.62)
					(name "SDI" (effects (font (size 1.27 1.27))))
					(number "28" (effects (font (size 1.27 1.27))))
				)
				(pin power_out line
					(at 50.8 0 180)
					(length 7.62)
					(name "EPAD" (effects (font (size 1.27 1.27))))
					(number "29" (effects (font (size 1.27 1.27))))
				)
			)
			(embedded_fonts no)
		)"""

ICM42688_SYMBOL = r"""
		(symbol "ICM-42688-P:ICM-42688-P"
			(pin_names
				(offset 1.016)
			)
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(in_pos_files yes)
			(duplicate_pin_numbers_are_jumpers no)
			(property "Reference" "U"
				(at -20.32 16.002 0)
				(show_name no)
				(do_not_autoplace no)
				(effects
					(font
						(size 1.27 1.27)
					)
					(justify bottom left)
				)
			)
			(property "Value" "ICM-42688-P"
				(at -20.32 -20.32 0)
				(show_name no)
				(do_not_autoplace no)
				(effects
					(font
						(size 1.27 1.27)
					)
					(justify bottom left)
				)
			)
			(property "Footprint" "ICM-42688-P:PQFN50P300X250X97-14N"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "Datasheet" ""
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "Description" "6-axis IMU SPI/I2C LGA-14"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(symbol "ICM-42688-P_0_0"
				(rectangle
					(start -20.32 -17.78)
					(end 20.32 15.24)
					(stroke (width 0.254) (type default))
					(fill (type background))
				)
				(pin bidirectional line
					(at -25.4 -7.62 0)
					(length 5.08)
					(name "AP_SDO/AP_AD0" (effects (font (size 1.016 1.016))))
					(number "1" (effects (font (size 1.016 1.016))))
				)
				(pin output line
					(at 25.4 5.08 180)
					(length 5.08)
					(name "INT1/INT" (effects (font (size 1.016 1.016))))
					(number "4" (effects (font (size 1.016 1.016))))
				)
				(pin power_in line
					(at 25.4 10.16 180)
					(length 5.08)
					(name "VDDIO" (effects (font (size 1.016 1.016))))
					(number "5" (effects (font (size 1.016 1.016))))
				)
				(pin power_in line
					(at 25.4 -15.24 180)
					(length 5.08)
					(name "GND" (effects (font (size 1.016 1.016))))
					(number "6" (effects (font (size 1.016 1.016))))
				)
				(pin power_in line
					(at 25.4 12.7 180)
					(length 5.08)
					(name "VDD" (effects (font (size 1.016 1.016))))
					(number "8" (effects (font (size 1.016 1.016))))
				)
				(pin bidirectional line
					(at -25.4 5.08 0)
					(length 5.08)
					(name "INT2/FSYNC/CLKIN" (effects (font (size 1.016 1.016))))
					(number "9" (effects (font (size 1.016 1.016))))
				)
				(pin input line
					(at -25.4 0 0)
					(length 5.08)
					(name "AP_CS" (effects (font (size 1.016 1.016))))
					(number "12" (effects (font (size 1.016 1.016))))
				)
				(pin input clock
					(at -25.4 -2.54 0)
					(length 5.08)
					(name "AP_SCL/AP_SCLK" (effects (font (size 1.016 1.016))))
					(number "13" (effects (font (size 1.016 1.016))))
				)
				(pin bidirectional line
					(at -25.4 -5.08 0)
					(length 5.08)
					(name "AP_SDA/AP_SDIO/AP_SDI" (effects (font (size 1.016 1.016))))
					(number "14" (effects (font (size 1.016 1.016))))
				)
				(pin passive line
					(at 25.4 -10.16 180)
					(length 5.08)
					(name "RESV_7" (effects (font (size 1.016 1.016))))
					(number "7" (effects (font (size 1.016 1.016))))
				)
				(pin passive line
					(at 25.4 0 180)
					(length 5.08)
					(name "RESV_2" (effects (font (size 1.016 1.016))))
					(number "2" (effects (font (size 1.016 1.016))))
				)
				(pin passive line
					(at 25.4 -2.54 180)
					(length 5.08)
					(name "RESV_3" (effects (font (size 1.016 1.016))))
					(number "3" (effects (font (size 1.016 1.016))))
				)
				(pin passive line
					(at 25.4 -5.08 180)
					(length 5.08)
					(name "RESV_10" (effects (font (size 1.016 1.016))))
					(number "10" (effects (font (size 1.016 1.016))))
				)
				(pin passive line
					(at 25.4 -7.62 180)
					(length 5.08)
					(name "RESV_11" (effects (font (size 1.016 1.016))))
					(number "11" (effects (font (size 1.016 1.016))))
				)
			)
			(embedded_fonts no)
		)"""

PT4115_SYMBOL = r"""
		(symbol "PT4115:PT4115"
			(pin_names
				(offset 1.016)
			)
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(in_pos_files yes)
			(duplicate_pin_numbers_are_jumpers no)
			(property "Reference" "U"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(effects
					(font
						(size 1.27 1.27)
					)
					(justify bottom)
				)
			)
			(property "Value" "PT4115"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(effects
					(font
						(size 1.27 1.27)
					)
					(justify bottom)
				)
			)
			(property "Footprint" "PT4115:SOT-89-5"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "Datasheet" ""
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "Description" "Constant current LED driver 1A"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(symbol "PT4115_0_0"
				(rectangle
					(start -7.62 -5.08)
					(end 7.62 5.08)
					(stroke (width 0.254) (type default))
					(fill (type background))
				)
				(pin bidirectional line
					(at -12.7 2.54 0)
					(length 5.08)
					(name "SW" (effects (font (size 1.016 1.016))))
					(number "1" (effects (font (size 1.016 1.016))))
				)
				(pin bidirectional line
					(at -12.7 0 0)
					(length 5.08)
					(name "GND" (effects (font (size 1.016 1.016))))
					(number "2" (effects (font (size 1.016 1.016))))
				)
				(pin bidirectional line
					(at -12.7 -2.54 0)
					(length 5.08)
					(name "DIM" (effects (font (size 1.016 1.016))))
					(number "3" (effects (font (size 1.016 1.016))))
				)
				(pin bidirectional line
					(at 12.7 -2.54 180)
					(length 5.08)
					(name "CSN" (effects (font (size 1.016 1.016))))
					(number "4" (effects (font (size 1.016 1.016))))
				)
				(pin bidirectional line
					(at 12.7 2.54 180)
					(length 5.08)
					(name "VIN" (effects (font (size 1.016 1.016))))
					(number "5" (effects (font (size 1.016 1.016))))
				)
			)
			(embedded_fonts no)
		)"""

# ─────────────────────────────────────────────────────────────────────────────
# Standard KiCad library symbol stubs (KiCad resolves from installed libs)
# We only embed the lib_symbols entry with minimal info; KiCad fills rest from lib.
# ─────────────────────────────────────────────────────────────────────────────

def std_sym_stub(lib_id, ref_prefix, value, description="", ref_at="2.032 0 90", val_at="0 0 90"):
    """Minimal stub for a standard library symbol."""
    return f"""
		(symbol "{lib_id}"
			(exclude_from_sim no)
			(in_bom yes)
			(on_board yes)
			(in_pos_files yes)
			(duplicate_pin_numbers_are_jumpers no)
			(property "Reference" "{ref_prefix}"
				(at {ref_at})
				(show_name no)
				(do_not_autoplace no)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "Value" "{value}"
				(at {val_at})
				(show_name no)
				(do_not_autoplace no)
				(effects
					(font
						(size 1.27 1.27)
					)
				)
			)
			(property "Footprint" ""
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font (size 1.27 1.27)
					)
				)
			)
			(property "Datasheet" ""
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font (size 1.27 1.27)
					)
				)
			)
			(property "Description" "{description}"
				(at 0 0 0)
				(show_name no)
				(do_not_autoplace no)
				(hide yes)
				(effects
					(font (size 1.27 1.27)
					)
				)
			)
		)"""

# ─────────────────────────────────────────────────────────────────────────────
# Sheet header / footer
# ─────────────────────────────────────────────────────────────────────────────

def sheet_header(file_uuid, title, paper="A2"):
    return f"""(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{file_uuid}")
\t(paper "{paper}")
\t(title_block
\t\t(title "{title}")
\t\t(date "2026-03-19")
\t\t(rev "01")
\t\t(company "Western University / MSE 4499")
\t)
\t(lib_symbols"""

def sheet_footer(sheet_instances_page):
    return f"""
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "{sheet_instances_page}")
\t\t)
\t)
\t(embedded_fonts no)
)
"""

# ─────────────────────────────────────────────────────────────────────────────
# Schematic-level power symbol instances (the small +VCC/GND flags)
# ─────────────────────────────────────────────────────────────────────────────

def power_sym(lib_id, ref, value, x, y, sheet_uuid):
    sym_uuid = uid()
    return f"""
\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(fields_autoplaced yes)
\t\t(uuid "{sym_uuid}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x} {round(y+2.54,3)} 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
\t\t\t)
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at {x} {round(y-2.54,3)} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
\t\t\t)
\t\t)
\t\t(property "Footprint" ""
\t\t\t(at {x} {y} 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Datasheet" ""
\t\t\t(at {x} {y} 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Description" ""
\t\t\t(at {x} {y} 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(pin "1"
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(instances
\t\t\t(project "RECLAIM_PCB"
\t\t\t\t(path "/{ROOT_SHEET_UUID}/{sheet_uuid}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""

# ─────────────────────────────────────────────────────────────────────────────
# Generic component placer (passive / IC)
# ─────────────────────────────────────────────────────────────────────────────

def component(lib_id, ref, value, x, y, sheet_uuid, pin_list, footprint="", datasheet="", description="", dnp=False, angle=0):
    """
    pin_list: list of pin number strings for this symbol (all get fresh UUIDs).
    """
    sym_uuid = uid()
    dnp_str = "yes" if dnp else "no"
    ref_x = round(x + 2.54, 3)
    ref_y = round(y - 1.27, 3)
    val_x = round(x + 2.54, 3)
    val_y = round(y + 1.27, 3)

    lines = [f"""
\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {angle})
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp {dnp_str})
\t\t(fields_autoplaced yes)
\t\t(uuid "{sym_uuid}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {ref_x} {ref_y} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
\t\t\t\t(justify left)
\t\t\t)
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at {val_x} {val_y} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
\t\t\t\t(justify left)
\t\t\t)
\t\t)
\t\t(property "Footprint" "{footprint}"
\t\t\t(at {x} {y} 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Datasheet" "{datasheet}"
\t\t\t(at {x} {y} 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Description" "{description}"
\t\t\t(at {x} {y} 0)
\t\t\t(hide yes)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)"""]

    for pnum in pin_list:
        lines.append(f'\n\t\t(pin "{pnum}"\n\t\t\t(uuid "{uid()}")\n\t\t)')

    lines.append(f"""
\t\t(instances
\t\t\t(project "RECLAIM_PCB"
\t\t\t\t(path "/{ROOT_SHEET_UUID}/{sheet_uuid}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)""")
    return "".join(lines)

def lbl(net_name, x, y, angle=0):
    return label(net_name, x, y, angle)

# ─────────────────────────────────────────────────────────────────────────────
# Read existing Power_Distribution.kicad_sch
# ─────────────────────────────────────────────────────────────────────────────

def read_existing_power_dist():
    path = os.path.join(PROJECT_DIR, "Power_Distribution.kicad_sch")
    with open(path, "r") as f:
        content = f.read()
    return content

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 1: Power Distribution — append new components to existing file
# ─────────────────────────────────────────────────────────────────────────────

def _find_root_close(content):
    """Return the index of the root-level closing ')' using paren-balance tracking."""
    depth = 0
    for i, c in enumerate(content):
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("No balanced root close found in content")

def _find_lib_symbols_close(content):
    """
    Return the index of the ')' that closes the top-level (lib_symbols ...) block.
    Searches by paren-balance starting from the (lib_symbols opening.
    """
    ls_start = content.find('\t(lib_symbols')
    if ls_start == -1:
        raise ValueError("No (lib_symbols block found in content")
    depth = 0
    for i, c in enumerate(content[ls_start:], start=ls_start):
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("lib_symbols block has no balanced close")

def generate_power_distribution():
    """
    The existing file already has: J1, F1, F2L, F2R, F3, F4, F5, power syms, PWR_FLAGs.
    We need to add: K1, Q1, D2, R11, R12, SW1, C1-C8, U1-U3, L_BUCK1/2, D_BUCK1/2,
                    R_FB1A/B, R_FB2A/B, and net labels.
    Strategy:
      1. Find the lib_symbols close using paren-balance and INSERT new lib stubs before it.
      2. Find the root close using paren-balance and INSERT placed symbols before it.
    """
    existing = read_existing_power_dist()

    # --- Step 1: insert new lib symbol stubs into lib_symbols ---
    # These are the lib IDs used by new components not already in the existing lib_symbols
    new_lib_stubs = (
        std_sym_stub("Device:C", "C", "C", "Capacitor") +
        std_sym_stub("Device:L", "L", "L", "Inductor") +
        std_sym_stub("Diode:SS34", "D", "SS34", "Schottky diode") +
        std_sym_stub("Switch:SW_Push", "SW", "SW_Push", "Push button switch") +
        std_sym_stub("Transistor_FET:IRLZ44N", "Q", "IRLZ44N", "N-ch MOSFET logic level") +
        std_sym_stub("Texas_Instruments:LM5116", "U", "LM5116SD", "Wide range synchronous buck controller") +
        std_sym_stub("Texas_Instruments:TPS5430DDA", "U", "TPS5430DDA", "12V->5V buck 3A") +
        std_sym_stub("Regulator_Linear:AMS1117-3.3", "U", "AMS1117-3.3", "5V->3.3V LDO 1A")
    )

    ls_close_idx = _find_lib_symbols_close(existing)
    # Insert the new lib stubs just before the lib_symbols closing ')'
    existing = existing[:ls_close_idx] + new_lib_stubs + "\n\t" + existing[ls_close_idx:]

    # --- Step 2: insert placed symbols + labels before the root close ---
    root_close_idx = _find_root_close(existing)

    SID = POWER_SHEET_UUID  # instance UUID
    parts = []

    # --- E-STOP SUBCIRCUIT (K1, Q1, D2, R11, R12, SW1) ---
    # Place around x=30-60, y=100-130 area (below existing fuses)
    parts.append(component("Relay:G5LE-1", "K1", "G5LE-1A-DC24", 40, 110, SID,
        ["1","2","3","4","5"], description="24V SPDT relay"))
    parts.append(component("Transistor_FET:IRLZ44N", "Q1", "IRLZ44N", 60, 120, SID,
        ["G","S","D"], description="N-ch MOSFET relay driver"))
    parts.append(component("Diode:1N4007", "D2", "1N4007", 50, 130, SID,
        ["1","2"], description="Flyback diode"))
    parts.append(component("Device:R", "R11", "1k", 65, 115, SID,
        ["1","2"], description="Gate resistor Q1"))
    parts.append(component("Device:R", "R12", "47k", 65, 120, SID,
        ["1","2"], description="Gate pull-down Q1"))
    parts.append(component("Switch:SW_Push", "SW1", "SW_Push", 45, 100, SID,
        ["1","2"], description="Mushroom E-stop NC"))

    # --- BULK CAPS ---
    parts.append(component("Device:C", "C1", "470uF", 75, 100, SID,
        ["1","2"], description="Bulk cap VCC_25V"))
    parts.append(component("Device:C", "C2", "470uF 25V", 80, 100, SID,
        ["1","2"], description="Bulk cap VCC_12V"))
    parts.append(component("Device:C", "C3", "470uF 16V", 85, 100, SID,
        ["1","2"], description="Bulk cap VCC_5V"))
    parts.append(component("Device:C", "C4", "470uF 10V", 90, 100, SID,
        ["1","2"], description="Bulk cap VCC_3V3"))
    parts.append(component("Device:C", "C5", "100nF", 80, 110, SID,
        ["1","2"], description="Decoupling U1"))
    parts.append(component("Device:C", "C6", "100nF", 85, 110, SID,
        ["1","2"], description="Decoupling U2"))
    parts.append(component("Device:C", "C7", "100nF", 90, 110, SID,
        ["1","2"], description="Decoupling U3"))
    parts.append(component("Device:C", "C8", "10uF", 95, 110, SID,
        ["1","2"], description="Bootstrap U1"))

    # --- BUCK CONVERTERS ---
    # U1: 25V->12V  x=110, y=100
    parts.append(component("Texas_Instruments:LM5116", "U1", "LM5116SD", 110, 100, SID,
        ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20"],
        description="25V->12V buck 10A"))
    parts.append(component("Device:L", "L_BUCK1", "22uH", 120, 95, SID,
        ["1","2"], description="Buck inductor U1"))
    parts.append(component("Diode:SS34", "D_BUCK1", "SS34", 120, 105, SID,
        ["1","2"], description="Freewheeling diode U1"))
    parts.append(component("Device:R", "R_FB1A", "40.2k", 115, 115, SID,
        ["1","2"], description="Feedback top U1"))
    parts.append(component("Device:R", "R_FB1B", "3.24k", 115, 120, SID,
        ["1","2"], description="Feedback bottom U1"))

    # U2: 12V->5V  x=140, y=100
    parts.append(component("Texas_Instruments:TPS5430DDA", "U2", "TPS5430DDA", 140, 100, SID,
        ["1","2","3","4","5","6","7","8"],
        description="12V->5V buck 3A"))
    parts.append(component("Device:L", "L_BUCK2", "22uH", 150, 95, SID,
        ["1","2"], description="Buck inductor U2"))
    parts.append(component("Diode:SS34", "D_BUCK2", "SS34", 150, 105, SID,
        ["1","2"], description="Freewheeling diode U2"))
    parts.append(component("Device:R", "R_FB2A", "53.6k", 145, 115, SID,
        ["1","2"], description="Feedback top U2"))
    parts.append(component("Device:R", "R_FB2B", "15k", 145, 120, SID,
        ["1","2"], description="Feedback bottom U2"))

    # U3: 5V->3.3V LDO  x=170, y=100
    parts.append(component("Regulator_Linear:AMS1117-3.3", "U3", "AMS1117-3.3", 170, 100, SID,
        ["1","2","3"], description="5V->3.3V LDO 1A"))

    # --- NET LABELS for Power Distribution ---
    labels = []
    labels.append(lbl("VBAT", 73, 75))
    labels.append(lbl("VBAT_MOTOR", 100, 75))
    labels.append(lbl("VBAT_COMPUTE", 140, 75))
    labels.append(lbl("VBAT_COIL", 160, 75))
    labels.append(lbl("VCC_25V", 75, 95))
    labels.append(lbl("VCC_12V", 110, 90))
    labels.append(lbl("VCC_5V", 140, 90))
    labels.append(lbl("VCC_3V3", 170, 90))
    labels.append(lbl("RELAY_COIL_IN", 50, 125))
    labels.append(lbl("ESTOP_RELAY_CTRL", 65, 118))
    labels.append(lbl("GND", 40, 135))
    labels.append(lbl("GND", 75, 108))
    labels.append(lbl("GND", 110, 108))
    labels.append(lbl("GND", 170, 108))

    # Insert placed symbols and labels BEFORE the root closing ')'
    new_content = "\n" + "".join(parts) + "".join(labels)
    result = existing[:root_close_idx] + new_content + "\n" + existing[root_close_idx:]
    return result

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 2: STM32 MCU
# ─────────────────────────────────────────────────────────────────────────────

def generate_stm32_mcu():
    SID = STM32_SHEET_UUID

    lib_symbols_section = (
        std_sym_stub("MCU_ST_STM32F4:STM32F405RGTx", "U", "STM32F405RGT6", "STM32F405 MCU LQFP-64") +
        std_sym_stub("Interface_USB:CP2102N-A02-GQFN24", "U", "CP2102N", "USB-UART bridge") +
        std_sym_stub("Device:Crystal", "Y", "Crystal", "Crystal oscillator") +
        std_sym_stub("Device:C", "C", "C", "Capacitor", ref_at="2.032 0 90", val_at="0 0 90") +
        std_sym_stub("Device:R", "R", "R", "Resistor", ref_at="2.032 0 90", val_at="0 0 90") +
        std_sym_stub("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "J", "Conn_01x04", "4-pin header") +
        std_sym_stub("Connector_USB:USB_C_Receptacle_GCT_USB4085", "J", "USB_C", "USB-C receptacle") +
        std_sym_stub("power:+3V3", "#PWR", "+3.3V", "3.3V power rail") +
        std_sym_stub("power:GND", "#PWR", "GND", "Ground") +
        std_sym_stub("power:PWR_FLAG", "#FLG", "PWR_FLAG", "Power flag")
    )

    parts = []

    # U4: STM32F405RGT6 — LQFP-64, place at 80,60
    # STM32F405 has many pins; list key ones
    stm32_pins = [str(i) for i in range(1, 65)]
    parts.append(component("MCU_ST_STM32F4:STM32F405RGTx", "U4", "STM32F405RGT6",
        80, 60, SID, stm32_pins, description="STM32F405 MCU"))

    # U_USB: CP2102N at x=150, y=60
    cp2102_pins = [str(i) for i in range(1, 25)] + ["EP"]
    parts.append(component("Interface_USB:CP2102N-A02-GQFN24", "U_USB", "CP2102N",
        150, 60, SID, cp2102_pins, description="USB-UART bridge"))

    # Crystal + load caps at x=55, y=50
    parts.append(component("Device:Crystal", "Y1", "8MHz",
        55, 50, SID, ["1","2"], description="8MHz crystal"))
    parts.append(component("Device:C", "C9", "22pF",
        50, 55, SID, ["1","2"], description="Crystal load cap A"))
    parts.append(component("Device:C", "C10", "22pF",
        60, 55, SID, ["1","2"], description="Crystal load cap B"))

    # Decoupling caps at x=110-140, y=100
    parts.append(component("Device:C", "C_VDD1", "100nF",
        110, 100, SID, ["1","2"], description="VDD decoupling"))
    parts.append(component("Device:C", "C_VDD_BULK", "4.7uF",
        115, 100, SID, ["1","2"], description="VDD bulk"))
    parts.append(component("Device:C", "C_VCAP1", "1uF",
        120, 100, SID, ["1","2"], description="VCAP1"))
    parts.append(component("Device:C", "C_VCAP2", "1uF",
        125, 100, SID, ["1","2"], description="VCAP2"))
    parts.append(component("Device:C", "C_NRST", "100nF",
        130, 100, SID, ["1","2"], description="NRST filter"))

    # Pull-up/down resistors
    parts.append(component("Device:R", "R1", "10k",
        135, 100, SID, ["1","2"], description="NRST pull-up"))
    parts.append(component("Device:R", "R2", "10k",
        140, 100, SID, ["1","2"], description="BOOT0 pull-down"))
    parts.append(component("Device:R", "R_I2C_SCL", "4.7k",
        145, 100, SID, ["1","2"], description="I2C SCL pull-up"))
    parts.append(component("Device:R", "R_I2C_SDA", "4.7k",
        150, 100, SID, ["1","2"], description="I2C SDA pull-up"))

    # J_SWD at x=170, y=55
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        "J_SWD", "SWD Header", 170, 55, SID,
        ["1","2","3","4"], description="SWD debug header"))

    # J_USB at x=170, y=70
    parts.append(component("Connector_USB:USB_C_Receptacle_GCT_USB4085",
        "J_USB", "USB-C", 170, 70, SID,
        ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12",
         "B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11","B12","S"],
        description="USB-C for CP2102N"))

    # Power symbols
    pwr = []
    pwr.append(power_sym("power:+3V3", "#PWR0201", "+3.3V", 80, 40, SID))
    pwr.append(power_sym("power:+3V3", "#PWR0202", "+3.3V", 150, 40, SID))
    pwr.append(power_sym("power:GND", "#PWR0203", "GND", 80, 85, SID))
    pwr.append(power_sym("power:GND", "#PWR0204", "GND", 150, 85, SID))
    pwr.append(power_sym("power:GND", "#PWR0205", "GND", 110, 108, SID))
    pwr.append(power_sym("power:GND", "#PWR0206", "GND", 170, 60, SID))
    pwr.append(power_sym("power:PWR_FLAG", "#FLG0201", "PWR_FLAG", 95, 40, SID))
    pwr.append(power_sym("power:PWR_FLAG", "#FLG0202", "PWR_FLAG", 165, 40, SID))

    # Net labels
    labels = []
    labels.append(lbl("VCC_3V3", 80, 38))
    labels.append(lbl("GND", 80, 87))
    labels.append(lbl("SPI1_SCK", 40, 60))
    labels.append(lbl("SPI1_MOSI", 40, 63))
    labels.append(lbl("SPI1_MISO", 40, 66))
    labels.append(lbl("SPI1_CS_DRV_L", 40, 69))
    labels.append(lbl("SPI1_CS_DRV_R", 40, 72))
    labels.append(lbl("SPI1_CS_IMU", 40, 75))
    labels.append(lbl("CAN1_TX", 40, 78))
    labels.append(lbl("CAN1_RX", 40, 81))
    labels.append(lbl("CAN2_TX", 40, 84))
    labels.append(lbl("CAN2_RX", 40, 87))
    labels.append(lbl("USART2_TX", 40, 90))
    labels.append(lbl("USART2_RX", 40, 93))
    labels.append(lbl("I2C1_SCL", 40, 96))
    labels.append(lbl("I2C1_SDA", 40, 99))
    labels.append(lbl("ENC_L_A", 120, 60))
    labels.append(lbl("ENC_L_B", 120, 63))
    labels.append(lbl("ENC_R_A", 120, 66))
    labels.append(lbl("ENC_R_B", 120, 69))
    labels.append(lbl("ESTOP_RELAY_CTRL", 120, 72))
    labels.append(lbl("USART2_TX", 145, 55))
    labels.append(lbl("USART2_RX", 145, 58))

    header = sheet_header(STM32_FILE_UUID, "RECLAIM Product PCB - STM32F405 MCU", paper="A1")
    content = (header + lib_symbols_section + "\n\t)\n" +
               "".join(parts) + "".join(pwr) + "".join(labels) +
               sheet_footer("3"))
    return content

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 3: Drivers, CAN, IMU, Power Monitoring
# ─────────────────────────────────────────────────────────────────────────────

def generate_drivers():
    SID = DRIVERS_SHEET_UUID

    lib_symbols_section = (
        DRV8243_SYMBOL +
        ICM42688_SYMBOL +
        std_sym_stub("Interface_CAN_LIN:SN65HVD230D", "U", "SN65HVD230DR", "CAN transceiver 3.3V") +
        std_sym_stub("Sensor_Current:INA226xIDGST", "U", "INA226AIDGST", "Power monitor I2C") +
        std_sym_stub("Device:R", "R", "R", "Resistor") +
        std_sym_stub("Device:C", "C", "C", "Capacitor") +
        std_sym_stub("Device:D_TVS", "TVS", "D_TVS", "TVS diode") +
        std_sym_stub("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "J", "Conn_01x03", "3-pin header") +
        std_sym_stub("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "J", "Conn_01x04", "4-pin header") +
        std_sym_stub("power:+3V3", "#PWR", "+3.3V", "3.3V power") +
        std_sym_stub("power:GND", "#PWR", "GND", "Ground") +
        std_sym_stub("power:PWR_FLAG", "#FLG", "PWR_FLAG", "Power flag")
    )

    drv_pins = [str(i) for i in range(1, 30)]

    parts = []

    # U5L: DRV8243 Left motor driver — x=30, y=40
    parts.append(component("2026-04-10_02-12-54:DRV8243SQDGQRQ1", "U5L", "DRV8243SQDGQRQ1",
        30, 40, SID, drv_pins, description="Motor driver Left"))

    # U5R: DRV8243 Right motor driver — x=95, y=40
    parts.append(component("2026-04-10_02-12-54:DRV8243SQDGQRQ1", "U5R", "DRV8243SQDGQRQ1",
        95, 40, SID, drv_pins, description="Motor driver Right"))

    # Supporting passives for U5L
    parts.append(component("Device:C", "C11L", "100nF", 20, 30, SID, ["1","2"], description="DRV8243L VCC decoupling"))
    parts.append(component("Device:C", "C12L", "10uF 50V", 20, 35, SID, ["1","2"], description="DRV8243L VM bulk"))
    parts.append(component("Device:C", "C13L", "100nF", 20, 40, SID, ["1","2"], description="DRV8243L VM decoupling"))
    parts.append(component("Device:D_TVS", "TVS1L", "SMBJ28A", 20, 45, SID, ["1","2"], description="TVS Left VM"))
    parts.append(component("Device:R", "R3L", "10m", 20, 50, SID, ["1","2"], description="Shunt Left"))

    # Supporting passives for U5R
    parts.append(component("Device:C", "C11R", "100nF", 85, 30, SID, ["1","2"], description="DRV8243R VCC decoupling"))
    parts.append(component("Device:C", "C12R", "10uF 50V", 85, 35, SID, ["1","2"], description="DRV8243R VM bulk"))
    parts.append(component("Device:C", "C13R", "100nF", 85, 40, SID, ["1","2"], description="DRV8243R VM decoupling"))
    parts.append(component("Device:D_TVS", "TVS1R", "SMBJ28A", 85, 45, SID, ["1","2"], description="TVS Right VM"))
    parts.append(component("Device:R", "R3R", "10m", 85, 50, SID, ["1","2"], description="Shunt Right"))

    # Motor/encoder connectors
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        "J_MOTOR_L", "Motor L", 30, 80, SID, ["1","2","3"], description="Motor Left output"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        "J_MOTOR_R", "Motor R", 95, 80, SID, ["1","2","3"], description="Motor Right output"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        "J_ENC_L", "Encoder L", 40, 80, SID, ["1","2","3","4"], description="Encoder Left"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        "J_ENC_R", "Encoder R", 105, 80, SID, ["1","2","3","4"], description="Encoder Right"))

    # CAN transceivers — U6A x=160, y=40; U6S x=160, y=70
    can_pins = ["1","2","3","4","5","6","7","8"]
    parts.append(component("Interface_CAN_LIN:SN65HVD230D", "U6A", "SN65HVD230DR",
        160, 40, SID, can_pins, description="CAN transceiver Arm"))
    parts.append(component("Interface_CAN_LIN:SN65HVD230D", "U6S", "SN65HVD230DR",
        160, 70, SID, can_pins, description="CAN transceiver Spare"))

    parts.append(component("Device:R", "R4A", "120", 155, 35, SID, ["1","2"], description="CAN term A"))
    parts.append(component("Device:R", "R4S", "120", 155, 65, SID, ["1","2"], description="CAN term S"))
    parts.append(component("Device:C", "C14A", "100nF", 155, 45, SID, ["1","2"], description="CAN A decoupling"))
    parts.append(component("Device:C", "C14S", "100nF", 155, 75, SID, ["1","2"], description="CAN S decoupling"))

    # CAN ARM connector
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        "J_CAN_ARM", "CAN Arm", 175, 40, SID, ["1","2","3"], description="CAN Arm connector"))

    # ICM-42688-P IMU — x=200, y=40
    imu_pins = ["1","2","3","4","5","6","7","8","9","10","11","12","13","14"]
    parts.append(component("ICM-42688-P:ICM-42688-P", "U7", "ICM-42688-P",
        200, 40, SID, imu_pins, description="6-axis IMU"))
    parts.append(component("Device:C", "C15", "100nF", 190, 35, SID, ["1","2"], description="IMU VDD decoupling"))
    parts.append(component("Device:C", "C16", "1uF", 190, 40, SID, ["1","2"], description="IMU VDD bulk"))
    parts.append(component("Device:R", "R5", "4.7k", 190, 45, SID, ["1","2"], description="IMU INT pull-up DNP", dnp=True))

    # INA226 power monitors — x=220, y=40/60/80
    ina_pins = ["1","2","3","4","5","6","7","8"]
    parts.append(component("Sensor_Current:INA226xIDGST", "U8", "INA226AIDGST",
        220, 40, SID, ina_pins, description="Power monitor 25V 0x40"))
    parts.append(component("Sensor_Current:INA226xIDGST", "U9", "INA226AIDGST",
        220, 60, SID, ina_pins, description="Power monitor 12V 0x41"))
    parts.append(component("Sensor_Current:INA226xIDGST", "U10", "INA226AIDGST",
        220, 80, SID, ina_pins, description="Power monitor 5V 0x44"))

    parts.append(component("Device:R", "R6", "10m", 215, 35, SID, ["1","2"], description="Shunt 25V rail"))
    parts.append(component("Device:R", "R7", "10m", 215, 55, SID, ["1","2"], description="Shunt 12V rail"))
    parts.append(component("Device:R", "R8", "10m", 215, 75, SID, ["1","2"], description="Shunt 5V rail"))
    parts.append(component("Device:C", "C17", "100nF", 230, 35, SID, ["1","2"], description="INA226 #1 decoupling"))
    parts.append(component("Device:C", "C18", "100nF", 230, 55, SID, ["1","2"], description="INA226 #2 decoupling"))
    parts.append(component("Device:C", "C19", "100nF", 230, 75, SID, ["1","2"], description="INA226 #3 decoupling"))

    # Power symbols
    pwr = []
    pwr.append(power_sym("power:+3V3", "#PWR0301", "+3.3V", 30, 20, SID))
    pwr.append(power_sym("power:+3V3", "#PWR0302", "+3.3V", 95, 20, SID))
    pwr.append(power_sym("power:+3V3", "#PWR0303", "+3.3V", 160, 25, SID))
    pwr.append(power_sym("power:+3V3", "#PWR0304", "+3.3V", 200, 25, SID))
    pwr.append(power_sym("power:+3V3", "#PWR0305", "+3.3V", 220, 25, SID))
    pwr.append(power_sym("power:GND", "#PWR0306", "GND", 30, 65, SID))
    pwr.append(power_sym("power:GND", "#PWR0307", "GND", 95, 65, SID))
    pwr.append(power_sym("power:GND", "#PWR0308", "GND", 160, 55, SID))
    pwr.append(power_sym("power:GND", "#PWR0309", "GND", 200, 58, SID))
    pwr.append(power_sym("power:GND", "#PWR0310", "GND", 220, 95, SID))
    pwr.append(power_sym("power:PWR_FLAG", "#FLG0301", "PWR_FLAG", 25, 20, SID))
    pwr.append(power_sym("power:PWR_FLAG", "#FLG0302", "PWR_FLAG", 20, 20, SID))

    # Net labels
    labels = []
    # DRV left
    labels.append(lbl("SPI1_SCK", 15, 40))
    labels.append(lbl("SPI1_CS_DRV_L", 15, 42.54))
    labels.append(lbl("SPI1_MOSI", 15, 45.08))
    labels.append(lbl("SPI1_MISO", 15, 47.62))
    labels.append(lbl("MOTOR_PWR_L", 20, 32))
    # DRV right
    labels.append(lbl("SPI1_SCK", 80, 40))
    labels.append(lbl("SPI1_CS_DRV_R", 80, 42.54))
    labels.append(lbl("SPI1_MOSI", 80, 45.08))
    labels.append(lbl("SPI1_MISO", 80, 47.62))
    labels.append(lbl("MOTOR_PWR_R", 85, 32))
    # Encoder nets
    labels.append(lbl("ENC_L_A", 40, 78))
    labels.append(lbl("ENC_L_B", 40, 80.54))
    labels.append(lbl("ENC_R_A", 105, 78))
    labels.append(lbl("ENC_R_B", 105, 80.54))
    # CAN
    labels.append(lbl("CAN1_TX", 155, 38))
    labels.append(lbl("CAN1_RX", 155, 40.54))
    labels.append(lbl("CAN2_TX", 155, 68))
    labels.append(lbl("CAN2_RX", 155, 70.54))
    labels.append(lbl("CAN_H_ARM", 175, 38))
    labels.append(lbl("CAN_L_ARM", 175, 40.54))
    # IMU
    labels.append(lbl("SPI1_SCK", 185, 42.54))
    labels.append(lbl("SPI1_CS_IMU", 185, 45.08))
    labels.append(lbl("SPI1_MOSI", 185, 47.62))
    labels.append(lbl("SPI1_MISO", 185, 50.16))
    # I2C (INA226)
    labels.append(lbl("I2C1_SCL", 215, 40))
    labels.append(lbl("I2C1_SDA", 215, 42.54))
    labels.append(lbl("VCC_25V", 215, 32))
    labels.append(lbl("VCC_12V", 215, 52))
    labels.append(lbl("VCC_5V", 215, 72))

    header = sheet_header(DRIVERS_FILE_UUID,
        "RECLAIM Product PCB - Motor Drivers, CAN, IMU & Power Monitoring", paper="A2")
    content = (header + lib_symbols_section + "\n\t)\n" +
               "".join(parts) + "".join(pwr) + "".join(labels) +
               sheet_footer("5"))
    return content

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 4: Connectors, LED, USB
# ─────────────────────────────────────────────────────────────────────────────

def generate_connectors():
    SID = CONNECTORS_SHEET_UUID

    lib_symbols_section = (
        PT4115_SYMBOL +
        std_sym_stub("Device:L", "L", "L", "Inductor") +
        std_sym_stub("Diode:SS34", "D", "SS34", "Schottky diode") +
        std_sym_stub("Device:R", "R", "R", "Resistor") +
        std_sym_stub("Device:C", "C", "C", "Capacitor") +
        std_sym_stub("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "J", "Conn_01x04", "4-pin header") +
        std_sym_stub("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "J", "Conn_01x03", "3-pin header") +
        std_sym_stub("Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "J", "Conn_01x02", "2-pin header") +
        std_sym_stub("power:+5V", "#PWR", "+5V", "5V power") +
        std_sym_stub("power:+12V", "#PWR", "+12V", "12V power") +
        std_sym_stub("power:GND", "#PWR", "GND", "Ground") +
        std_sym_stub("power:PWR_FLAG", "#FLG", "PWR_FLAG", "Power flag")
    )

    parts = []

    # PT4115 work light driver — x=40, y=40
    parts.append(component("PT4115:PT4115", "U11", "PT4115",
        40, 40, SID, ["1","2","3","4","5"], description="Work light driver 1A"))
    parts.append(component("Device:L", "L_LED", "22uH",
        30, 35, SID, ["1","2"], description="PT4115 switching inductor"))
    parts.append(component("Diode:SS34", "D_LED", "SS34",
        30, 45, SID, ["1","2"], description="PT4115 freewheel diode"))
    parts.append(component("Device:R", "R10", "0.1",
        50, 45, SID, ["1","2"], description="PT4115 current set 1A"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "J_LED_WORK", "Work Light", 55, 40, SID, ["1","2"], description="Work light connector"))

    # Status LED connector & related — x=80, y=40
    parts.append(component("Device:R", "R9", "470",
        75, 40, SID, ["1","2"], description="WS2812B data series R"))
    parts.append(component("Device:C", "C20", "100uF",
        75, 47, SID, ["1","2"], description="WS2812B bulk cap"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        "J_LED_STATUS", "LED Status", 85, 40, SID,
        ["1","2","3"], description="WS2812B ring connector"))

    # Peripheral connectors — x=110-180, y=40
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        "J_JETSON", "Jetson", 110, 40, SID,
        ["1","2","3","4"], description="Jetson UART connector"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        "J_LIDAR", "LiDAR", 120, 40, SID,
        ["1","2","3","4"], description="LiDAR connector"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "J_CAMERA", "Camera", 130, 40, SID,
        ["1","2"], description="Camera USB power"))

    # Bumper connectors — x=140-180, y=40
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "J_BUMPER_FL", "Bumper FL", 140, 40, SID, ["1","2"], description="Bumper Front-Left"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "J_BUMPER_FR", "Bumper FR", 150, 40, SID, ["1","2"], description="Bumper Front-Right"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "J_BUMPER_RL", "Bumper RL", 160, 40, SID, ["1","2"], description="Bumper Rear-Left"))
    parts.append(component("Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "J_BUMPER_RR", "Bumper RR", 170, 40, SID, ["1","2"], description="Bumper Rear-Right"))

    # Power symbols
    pwr = []
    pwr.append(power_sym("power:+12V", "#PWR0401", "+12V", 40, 25, SID))
    pwr.append(power_sym("power:+5V", "#PWR0402", "+5V", 80, 25, SID))
    pwr.append(power_sym("power:+5V", "#PWR0403", "+5V", 110, 25, SID))
    pwr.append(power_sym("power:+12V", "#PWR0404", "+12V", 120, 25, SID))
    pwr.append(power_sym("power:+5V", "#PWR0405", "+5V", 130, 25, SID))
    pwr.append(power_sym("power:GND", "#PWR0406", "GND", 40, 58, SID))
    pwr.append(power_sym("power:GND", "#PWR0407", "GND", 80, 58, SID))
    pwr.append(power_sym("power:GND", "#PWR0408", "GND", 110, 55, SID))
    pwr.append(power_sym("power:GND", "#PWR0409", "GND", 120, 55, SID))
    pwr.append(power_sym("power:GND", "#PWR0410", "GND", 140, 50, SID))
    pwr.append(power_sym("power:GND", "#PWR0411", "GND", 150, 50, SID))
    pwr.append(power_sym("power:GND", "#PWR0412", "GND", 160, 50, SID))
    pwr.append(power_sym("power:GND", "#PWR0413", "GND", 170, 50, SID))
    pwr.append(power_sym("power:PWR_FLAG", "#FLG0401", "PWR_FLAG", 35, 25, SID))
    pwr.append(power_sym("power:PWR_FLAG", "#FLG0402", "PWR_FLAG", 75, 25, SID))

    # Net labels
    labels = []
    labels.append(lbl("VCC_12V", 40, 23))
    labels.append(lbl("VCC_5V", 80, 23))
    labels.append(lbl("USART2_TX", 110, 38))
    labels.append(lbl("USART2_RX", 110, 40.54))
    labels.append(lbl("VCC_12V", 120, 23))
    labels.append(lbl("VCC_5V", 130, 23))
    # Bumper GPIO
    labels.append(lbl("BUMPER_FL", 140, 38))
    labels.append(lbl("BUMPER_FR", 150, 38))
    labels.append(lbl("BUMPER_RL", 160, 38))
    labels.append(lbl("BUMPER_RR", 170, 38))

    header = sheet_header(CONNECTORS_FILE_UUID,
        "RECLAIM Product PCB - Connectors, LED, USB & Peripherals", paper="A2")
    content = (header + lib_symbols_section + "\n\t)\n" +
               "".join(parts) + "".join(pwr) + "".join(labels) +
               sheet_footer("4"))
    return content

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    files = {
        "Power_Distribution.kicad_sch": None,
        "STM32_MCU.kicad_sch": None,
        "Drivers_CAN_IMU_Power.kicad_sch": None,
        "Connectors_LED_USB.kicad_sch": None,
    }

    print("\n=== RECLAIM PCB Schematic Generator ===\n")

    # Backup
    print("Backing up existing files...")
    for fname in files:
        backup_file(os.path.join(PROJECT_DIR, fname))

    print("\nGenerating schematics...")

    # Power Distribution (modify existing)
    print("  Sheet 1: Power_Distribution — appending missing components...")
    power_content = generate_power_distribution()
    power_path = os.path.join(PROJECT_DIR, "Power_Distribution.kicad_sch")
    with open(power_path, "w") as f:
        f.write(power_content)
    print("    Added: K1, Q1, D2, R11, R12, SW1, C1-C8, U1-U3, L_BUCK1/2, D_BUCK1/2, R_FB1A/B, R_FB2A/B")
    print("    Net labels: VBAT, VBAT_MOTOR, VBAT_COMPUTE, VBAT_COIL, VCC_25V, VCC_12V, VCC_5V, VCC_3V3, RELAY_COIL_IN, ESTOP_RELAY_CTRL")

    # STM32 MCU (generate fresh)
    print("  Sheet 2: STM32_MCU — generating full content...")
    stm32_content = generate_stm32_mcu()
    stm32_path = os.path.join(PROJECT_DIR, "STM32_MCU.kicad_sch")
    with open(stm32_path, "w") as f:
        f.write(stm32_content)
    print("    Added: U4(STM32F405), U_USB(CP2102N), Y1, C9/C10, C_VDD1/BULK/VCAP1/VCAP2/NRST, R1/R2/R_I2C_SCL/SDA, J_SWD, J_USB")
    print("    Net labels: VCC_3V3, SPI1_*, CAN1/2_TX/RX, USART2_TX/RX, I2C1_SCL/SDA, ENC_*")

    # Drivers (generate fresh)
    print("  Sheet 3: Drivers_CAN_IMU_Power — generating full content...")
    drivers_content = generate_drivers()
    drivers_path = os.path.join(PROJECT_DIR, "Drivers_CAN_IMU_Power.kicad_sch")
    with open(drivers_path, "w") as f:
        f.write(drivers_content)
    print("    Added: U5L/U5R(DRV8243), U6A/U6S(CAN), U7(ICM-42688-P), U8/U9/U10(INA226), R3L/R3R/R4A/R4S/R5-R8, C11-C19, TVS1L/R, J_MOTOR_L/R, J_ENC_L/R, J_CAN_ARM")
    print("    Net labels: SPI1_*, CAN1/2_TX/RX, CAN_H/L_ARM, MOTOR_PWR_L/R, ENC_*, I2C1_*, VCC_25V/12V/5V")

    # Connectors (generate fresh)
    print("  Sheet 4: Connectors_LED_USB — generating full content...")
    connectors_content = generate_connectors()
    conn_path = os.path.join(PROJECT_DIR, "Connectors_LED_USB.kicad_sch")
    with open(conn_path, "w") as f:
        f.write(connectors_content)
    print("    Added: U11(PT4115), L_LED, D_LED, R9/R10, C20, J_JETSON, J_LIDAR, J_CAMERA, J_LED_STATUS, J_LED_WORK, J_BUMPER_FL/FR/RL/RR")
    print("    Net labels: VCC_12V, VCC_5V, USART2_TX/RX, BUMPER_*")

    print("\n=== Summary ===")
    print(f"Sheet 1 Power_Distribution: Existing components preserved + 25 new components added")
    print(f"Sheet 2 STM32_MCU:          15 components placed (U4, U_USB, crystal, caps, resistors, connectors)")
    print(f"Sheet 3 Drivers_CAN_IMU:    35 components placed (2x DRV8243, 2x SN65HVD230, ICM-42688-P, 3x INA226, passives, connectors)")
    print(f"Sheet 4 Connectors_LED_USB: 17 components placed (PT4115, passives, 10 connectors)")
    print(f"\nAll files written to: {PROJECT_DIR}")
    print("NOTE: Open in KiCad 10 to verify ERC — some standard lib symbols use stubs.")
    print("      KiCad will resolve standard symbols from installed libraries automatically.")
    print("      Custom symbols (DRV8243, ICM-42688-P, PT4115) are fully embedded.")

if __name__ == "__main__":
    main()
