#!/usr/bin/env python3
"""
Rearrange all 4 RECLAIM KiCad sub-sheets for professional layout.
- Removes duplicate K1 (G5LE-1) and Q1 (2N7002) from Power Distribution
- Repositions all symbols and labels into logical groups with proper spacing
- Signal flows left-to-right on each sheet

Run with: python3 rearrange_schematic.py
"""

import re
import shutil
from datetime import datetime

PROJECT = "/Users/shadysiam/Documents/RECLAIM/docs/product_pcb_electrical/kicad_project/RECLAIM_PCB"

# ─── Helpers ───

def backup(filepath):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{filepath}.bak_{ts}"
    shutil.copy2(filepath, dst)
    print(f"  Backed up → {dst}")

def update_symbol_position(content, uuid, new_x, new_y, new_angle=0):
    """Find a symbol block by its UUID and update its (at X Y angle) line."""
    uuid_idx = content.find(f'(uuid "{uuid}")')
    if uuid_idx == -1:
        print(f"  WARNING: UUID {uuid} not found!")
        return content

    # Search backwards from UUID for the nearest (at X Y ...) that belongs to this symbol
    # The symbol's (at ...) is the first one after the (symbol line
    # Find the start of this symbol block
    search_start = content.rfind('(symbol\n', 0, uuid_idx)
    if search_start == -1:
        search_start = content.rfind('(symbol\r\n', 0, uuid_idx)
    if search_start == -1:
        print(f"  WARNING: Could not find symbol block for UUID {uuid}")
        return content

    # Find the (at ...) line within this symbol block (between search_start and uuid_idx)
    block = content[search_start:uuid_idx]
    at_match = re.search(r'\(at\s+[\d.\-]+\s+[\d.\-]+\s+[\d.\-]+\)', block)
    if not at_match:
        print(f"  WARNING: No (at ...) found for UUID {uuid}")
        return content

    old_at = at_match.group()
    new_at = f"(at {new_x} {new_y} {new_angle})"

    # Replace only this specific occurrence
    abs_start = search_start + at_match.start()
    abs_end = search_start + at_match.end()
    content = content[:abs_start] + new_at + content[abs_end:]

    return content

def update_label_position(content, uuid, new_x, new_y, new_angle=0):
    """Find a label by its UUID and update its (at X Y angle)."""
    uuid_idx = content.find(f'(uuid "{uuid}")')
    if uuid_idx == -1:
        print(f"  WARNING: Label UUID {uuid} not found!")
        return content

    # Labels are simpler: (label "TEXT" (at X Y angle) ...)
    # Find the start of this label
    search_start = content.rfind('(label ', 0, uuid_idx)
    if search_start == -1:
        print(f"  WARNING: Could not find label block for UUID {uuid}")
        return content

    block = content[search_start:uuid_idx]
    at_match = re.search(r'\(at\s+[\d.\-]+\s+[\d.\-]+\s+[\d.\-]+\)', block)
    if not at_match:
        print(f"  WARNING: No (at ...) found for label UUID {uuid}")
        return content

    old_at = at_match.group()
    new_at = f"(at {new_x} {new_y} {new_angle})"

    abs_start = search_start + at_match.start()
    abs_end = search_start + at_match.end()
    content = content[:abs_start] + new_at + content[abs_end:]

    return content

def remove_symbol_block(content, uuid):
    """Remove an entire (symbol ...) block identified by UUID."""
    uuid_str = f'(uuid "{uuid}")'
    uuid_idx = content.find(uuid_str)
    if uuid_idx == -1:
        print(f"  WARNING: UUID {uuid} not found for removal!")
        return content

    # Find the start of this symbol block
    search_start = content.rfind('\t\t(symbol\n', 0, uuid_idx)
    if search_start == -1:
        search_start = content.rfind('\t\t(symbol\r\n', 0, uuid_idx)
    if search_start == -1:
        print(f"  WARNING: Could not find symbol block start for UUID {uuid}")
        return content

    # Find the end by counting parentheses from search_start
    # Skip the leading whitespace, start from (symbol
    paren_start = content.index('(symbol', search_start)
    depth = 0
    i = paren_start
    while i < len(content):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                # Found the closing paren
                # Include any trailing newline
                end = i + 1
                if end < len(content) and content[end] == '\n':
                    end += 1
                content = content[:search_start] + content[end:]
                print(f"  Removed symbol block with UUID {uuid}")
                return content
        i += 1

    print(f"  WARNING: Could not find end of symbol block for UUID {uuid}")
    return content

# ─── Power Distribution Layout ───
# A2 sheet (594 x 420mm). Signal flow: Battery → Fuses → E-stop → Post-relay → Bucks → LDO

def rearrange_power():
    filepath = f"{PROJECT}/Power_Distribution.kicad_sch"
    print(f"\n{'='*60}")
    print(f"Rearranging: Power Distribution")
    print(f"{'='*60}")
    backup(filepath)

    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Remove duplicates (old K1 G5LE-1 and old Q1 2N7002)
    content = remove_symbol_block(content, "60d3fb76-e03c-4d6a-8ad4-1c3d26f330fa")  # K1 G5LE-1
    content = remove_symbol_block(content, "8f546d50-7880-4346-975a-72524c0543d8")  # Q1 2N7002

    # 2. Reposition all symbols into logical groups
    positions = {
        # ── Power symbols & flags (top row, y=50) ──
        "218a529b-34f7-4746-8b82-bf87cc1e01b4": (55, 45, 0),     # #PWR01 +24V
        "1d0bce40-fbcc-49d5-9298-127123b4d567": (150, 45, 0),    # #PWR02 GND
        "655a14b7-fe49-4d92-a944-d41ba70e8468": (310, 45, 0),    # #PWR03 +12V
        "d987bdfd-c770-4c13-ad9e-7205540a562f": (410, 45, 0),    # #PWR04 +5V
        "5ecdcca9-aa69-461a-bbb9-eceb22b520ea": (490, 45, 0),    # #PWR05 +3.3V
        "6eacd9fd-c749-4363-a8eb-b9e62ce16d4c": (65, 45, 0),     # #FLG01 PWR_FLAG
        "2c30a088-85ee-48d1-9585-58d4187a6ac5": (160, 45, 0),    # #FLG02 PWR_FLAG

        # ── Zone 1: Battery Input (x: 50-80) ──
        "0271a66d-03b9-4928-8516-3d7e6166d643": (55, 120, 0),    # J1 battery connector

        # ── Zone 2: Main Fuses (x: 100-130) ──
        "ec5c3c3e-645e-4fbc-b02c-0c1b3e601caf": (110, 90, 0),   # F1 30A (motor path)
        "3b7224a9-434f-4b83-afb3-045eb7a01411": (110, 140, 0),   # F4 5A (compute path)
        "1dba3700-6afc-4df6-a6a4-0b22ad0ab596": (110, 195, 0),   # F5 2A (coil path)

        # ── Zone 3: E-Stop Circuit (x: 140-240, y: 160-240) ──
        "fe8d3759-b3bd-4f81-915c-95516a5e35b7": (150, 200, 0),   # SW1 mushroom switch
        "11ef1442-2092-4bf4-9088-dd026c0008ad": (185, 185, 0),   # R11 1k gate pulldown
        "5e1b5fcb-a597-4f9a-9046-43f7c76645cd": (185, 215, 0),   # R12 47k divider
        "e66bf026-06d2-4f0a-b267-44dd27e11f94": (210, 200, 0),   # Q1 IRLZ44N
        "15666073-f58f-40e6-9481-3b95865d87b2": (240, 130, 0),   # K1 G5LE-1A-DC24 relay
        "35e00f6c-959f-45a1-9510-d80b9f9f0315": (260, 155, 0),   # D2 1N4007 flyback
        "73483bd4-b952-4fe5-a4de-2fcece5d2b6c": (260, 120, 0),   # D1 1N4007
        "dbc40c46-e866-45b4-8db9-50778865d1f5": (230, 175, 0),   # R1 (relay related)
        "94d77f3c-7185-426c-9f94-ce243094991e": (230, 195, 0),   # R2 (relay related)

        # ── Zone 4: Post-Relay Fuses (x: 280-310) ──
        "eb2e5b79-0031-4f38-80a0-e597daf139d3": (290, 85, 0),    # F2L 15A left motor
        "5366a762-9cfb-414e-b662-c1f3c430d333": (290, 105, 0),   # F2R 15A right motor
        "84bf3116-a6bf-4b28-8e9a-88f49b513132": (290, 125, 0),   # F3 10A arm
        "b8c1a8e7-871d-4bba-857e-d1967b119301": (290, 155, 0),   # C1 470uF VCC_25V bulk

        # ── Zone 5: Buck 1 — U1 LM5116 25V→12V (x: 330-400) ──
        "57470893-2118-405b-960c-8b873285f41d": (350, 130, 0),   # U1 LM5116SD
        "065bb558-bf44-4d76-823d-7fd99495b9a0": (385, 105, 0),   # L_BUCK1 22uH
        "b5a3a363-4d7d-48cc-89c7-d3da8a45658b": (370, 160, 0),   # D_BUCK1 SS34
        "efa23de1-425e-463a-8f1c-412a2c069b6c": (390, 150, 0),   # R_FB1A 40.2k
        "f1dc9d81-f969-4e8c-a34a-52b5de1cdb2c": (390, 170, 0),   # R_FB1B 3.24k
        "ed5289dd-c5df-4e89-ad74-bb7cb3628d9c": (400, 115, 0),   # C2 470uF 25V
        "d70ea75e-fa45-4c44-9347-e7c90a7f45e2": (400, 135, 0),   # C5 100nF

        # ── Zone 6: Buck 2 — U2 TPS5430DDA 12V→5V (x: 420-480) ──
        "b86a1092-f70e-4dde-962f-2414e0ecc894": (440, 130, 0),   # U2 TPS5430DDA
        "2ce5c534-3bec-4ebc-8a15-fd736e864abe": (475, 105, 0),   # L_BUCK2 22uH
        "97b87a5e-473b-4154-82d6-edee46345264": (460, 160, 0),   # D_BUCK2 SS34
        "2a3a4b3f-515d-4f52-b522-bea6fc5a9ad6": (480, 150, 0),   # R_FB2A 53.6k
        "4401a498-0b5f-4a79-8382-ddc7151196f0": (480, 170, 0),   # R_FB2B 15k
        "f11d634c-16dd-42cb-850b-6bf3ae32c3aa": (490, 115, 0),   # C3 470uF 16V
        "b37172a6-3552-49dd-af44-62cd1bc25469": (490, 135, 0),   # C6 100nF

        # ── Zone 7: LDO — U3 AMS1117 5V→3.3V (x: 500-550) ──
        "790dd384-11fb-4829-ae4e-7df92f52853f": (520, 130, 0),   # U3 AMS1117-3.3
        "09ec7415-7bbe-4f6e-a2d9-b73a7b2b338a": (545, 115, 0),   # C4 470uF 10V
        "b3a10346-327c-4b38-aa87-00850fd68f0a": (545, 135, 0),   # C7 100nF
        "b358ba64-d90a-459c-a630-5ab711658a13": (545, 150, 0),   # C8 10uF
    }

    for uuid, (x, y, angle) in positions.items():
        content = update_symbol_position(content, uuid, x, y, angle)

    # 3. Reposition labels
    label_positions = {
        "be714c51-80b7-420e-b0f6-5252490baf3c": (75, 110, 0),    # VBAT
        "0eebd179-6592-4792-9f3a-b64d1d045a85": (110, 82, 0),    # VBAT_MOTOR
        "ba2c7890-24ae-4e19-ab03-8faa1fde1b9e": (110, 132, 0),   # VBAT_COMPUTE
        "5a838ac4-79ff-416b-9f98-ea0962f5eb00": (110, 187, 0),   # VBAT_COIL
        "d02561fc-289b-4455-a261-8882bfd0e6ae": (275, 80, 0),    # VCC_25V
        "7e6f4267-f041-4ec5-a6c0-142b9dcf5d92": (350, 95, 0),    # VCC_12V
        "04e69aa9-3dcd-403c-a834-b70648efada9": (440, 95, 0),    # VCC_5V
        "c3cc8659-83b8-462a-9c27-4fd78b802ce5": (520, 95, 0),    # VCC_3V3
        "480dd68f-610f-44f5-932d-261e91f431f7": (175, 200, 0),   # RELAY_COIL_IN
        "423a5216-c50e-4f9c-a290-b5acb14e8907": (210, 185, 0),   # ESTOP_RELAY_CTRL
        "e950e386-f5e5-4688-828b-15487ed29a7b": (225, 230, 0),   # GND (e-stop)
        "0829d84c-d495-4a1a-b4f9-b6ecbeba53b1": (290, 170, 0),   # GND (post-relay)
        "3716e67b-3375-4e57-96ce-5807ede29478": (370, 185, 0),   # GND (buck1)
        "0c7012bc-4a88-4663-80ae-40249bc8669c": (530, 165, 0),   # GND (LDO)
    }

    for uuid, (x, y, angle) in label_positions.items():
        content = update_label_position(content, uuid, x, y, angle)

    with open(filepath, 'w') as f:
        f.write(content)
    print("  ✓ Power Distribution rearranged")


# ─── STM32 MCU Layout ───
# A1 sheet (841 x 594mm). STM32 center, crystal left, USB-UART right, caps below

def rearrange_stm32():
    filepath = f"{PROJECT}/STM32_MCU.kicad_sch"
    print(f"\n{'='*60}")
    print(f"Rearranging: STM32 MCU")
    print(f"{'='*60}")
    backup(filepath)

    with open(filepath, 'r') as f:
        content = f.read()

    positions = {
        # ── Power symbols (top, y=50) ──
        "7b192c73-e5aa-4bd6-b67a-c7aa299b5337": (200, 50, 0),   # #PWR0201 +3.3V (STM32)
        "1ca7b541-32c0-4531-b9f2-b4b9d08beac8": (500, 50, 0),   # #PWR0202 +3.3V (USB)
        "d71d3f22-9db1-4dd8-ae55-8786c4d4859c": (200, 280, 0),  # #PWR0203 GND (STM32)
        "21f87d65-6747-44ba-8353-6379f2ece9b9": (500, 200, 0),   # #PWR0204 GND (USB)
        "aa0d8e79-1948-4df0-871d-3cf7baf715d0": (300, 310, 0),   # #PWR0205 GND (caps)
        "643c516c-d7c2-4e97-8d89-17d7a8bd8a08": (620, 180, 0),   # #PWR0206 GND (SWD)
        "54f01a4a-afe2-4a35-837c-7e064f0dc235": (215, 50, 0),    # #FLG0201 PWR_FLAG
        "980ceecd-a7ab-4b46-8067-9f94c1f8d6ec": (515, 50, 0),    # #FLG0202 PWR_FLAG

        # ── Zone 1: Crystal (x: 100-150, y: 100-160) ──
        "8eb7d939-f3c7-4136-b46e-4c298a54eed4": (120, 120, 0),   # Y1 8MHz crystal
        "397c1e64-a3fa-4452-addf-582582854301": (105, 135, 0),    # C9 22pF
        "023f9cf5-3f9f-4360-bbe5-3eb29d5a8a56": (135, 135, 0),    # C10 22pF

        # ── Zone 2: STM32F405 (center, x: 200, y: 130) ──
        "b720eef4-f0a3-490b-ad32-3a7236aeaa21": (250, 150, 0),   # U4 STM32F405RGT6

        # ── Zone 3: Decoupling & bypass caps (below STM32, y: 280-320) ──
        "d86db769-995a-48d0-a290-6c8e8c902cb1": (220, 300, 0),   # C_VDD1 100nF
        "522dde4d-7645-4904-ad2f-37813222b5a5": (240, 300, 0),   # C_VDD_BULK 4.7uF
        "bb442db7-e177-4ead-a489-4f5e072ae040": (260, 300, 0),   # C_VCAP1 1uF
        "bb947850-89fa-4fd3-ad8a-60ec837838fe": (280, 300, 0),   # C_VCAP2 1uF
        "1ec1ab58-b2d9-44d8-8303-b29e4b766e66": (300, 300, 0),   # C_NRST 100nF

        # ── Zone 4: Pull-ups (right of STM32, x: 380-420) ──
        "a21302b4-1fd6-484b-8c3e-f20fc0b6b78a": (390, 120, 0),   # R1 10k
        "48939cf1-8ecf-4982-b26b-5b4736f247c6": (390, 145, 0),   # R2 10k
        "41558208-b4c7-4021-95ce-6cf877b7bbee": (390, 175, 0),   # R_I2C_SCL 4.7k
        "536f5b71-6b6c-40a3-a177-165fac4ef926": (390, 200, 0),   # R_I2C_SDA 4.7k

        # ── Zone 5: USB-UART CP2102N (x: 480-560) ──
        "3db9f912-f10f-4728-82f7-0a180f3d45e3": (500, 130, 0),   # U_USB CP2102N

        # ── Zone 6: Connectors (far right, x: 600-650) ──
        "7e7ac6e6-d996-4afc-9c1a-65a821ed6a69": (620, 100, 0),   # J_SWD
        "bd9e66d1-fdca-4b39-85ce-548a6893d34d": (620, 150, 0),   # J_USB
    }

    for uuid, (x, y, angle) in positions.items():
        content = update_symbol_position(content, uuid, x, y, angle)

    label_positions = {
        "bc957e23-ebd3-481a-a283-d8a44ea37c50": (200, 55, 0),    # VCC_3V3
        "b1e4a6ed-f43a-448e-973e-76cfc0b850ad": (200, 275, 0),   # GND
        # SPI labels (left side of STM32)
        "7d642da8-d3d6-413c-8b86-c1bdac39f9f8": (170, 120, 180), # SPI1_SCK
        "5332a8ac-0710-4b61-8a7f-fa038751febe": (170, 125, 180), # SPI1_MOSI
        "b3f0872d-773a-4b75-9fe0-ec8d81c9711b": (170, 130, 180), # SPI1_MISO
        "08332ece-d08d-4a57-990e-0e0ee95e8eef": (170, 140, 180), # SPI1_CS_DRV_L
        "3ec6bd41-6aae-49c0-a378-e007ed049f8e": (170, 145, 180), # SPI1_CS_DRV_R
        "8d338aea-0275-437d-8c07-7d9e257eae3f": (170, 150, 180), # SPI1_CS_IMU
        # CAN labels
        "fa11ef71-1a93-4741-8939-487909130475": (170, 165, 180),  # CAN1_TX
        "4ec48f09-28bf-422f-a99d-3e49e49d1b70": (170, 170, 180), # CAN1_RX
        "4fed448e-dafc-49af-9ff7-b3bf5ce6f7a5": (170, 180, 180), # CAN2_TX
        "c4f1c6e7-72f9-49d8-8346-9bc56ea3ae0c": (170, 185, 180), # CAN2_RX
        # UART labels
        "0a93c48c-2f88-4267-91ae-c3b9d6285ea7": (170, 200, 180), # USART2_TX
        "8fc47f2c-39d1-44d5-8541-0051c6bdc02a": (170, 205, 180), # USART2_RX
        # I2C labels
        "6d000d64-d56f-4b45-ad87-31fe33b611c8": (170, 220, 180), # I2C1_SCL
        "6a9543d8-c06c-4c10-b84a-c5303337801d": (170, 225, 180), # I2C1_SDA
        # Encoder labels (right side of STM32)
        "81c21b30-3a89-47ad-9c21-39008e81e682": (340, 130, 0),   # ENC_L_A
        "3f212a4f-c7a1-4c52-91f3-2ed92558b933": (340, 135, 0),   # ENC_L_B
        "2f4a20eb-54e1-4fc2-a13e-f4677bfedf3c": (340, 145, 0),   # ENC_R_A
        "08e42bb7-fd88-43a4-adc5-df750b42a3b8": (340, 150, 0),   # ENC_R_B
        "cc20016e-d455-4334-8c5c-c6c47fb82f23": (340, 165, 0),   # ESTOP_RELAY_CTRL
        # USB UART labels
        "e0e891f3-0be8-49a7-8c2c-d586dd3b649f": (470, 125, 180), # USART2_TX (USB side)
        "fc8d0dc8-bf2a-4df0-b5ef-62a43661527b": (470, 135, 180), # USART2_RX (USB side)
    }

    for uuid, (x, y, angle) in label_positions.items():
        content = update_label_position(content, uuid, x, y, angle)

    with open(filepath, 'w') as f:
        f.write(content)
    print("  ✓ STM32 MCU rearranged")


# ─── Drivers, CAN, IMU, Power Monitoring Layout ───
# A2 sheet. Groups: Motor Drivers L/R | CAN transceivers | IMU | INA226 x3

def rearrange_drivers():
    filepath = f"{PROJECT}/Drivers_CAN_IMU_Power.kicad_sch"
    print(f"\n{'='*60}")
    print(f"Rearranging: Drivers, CAN, IMU, Power Monitoring")
    print(f"{'='*60}")
    backup(filepath)

    with open(filepath, 'r') as f:
        content = f.read()

    positions = {
        # ── Power symbols (top row) ──
        "f1207480-4af4-4074-b8ac-461a412f70c9": (60, 30, 0),     # #PWR0301 +3.3V
        "b298b0b1-66d9-4d1c-91b0-af2cbd75bb27": (180, 30, 0),    # #PWR0302 +3.3V
        "a7f9eef9-5414-4fa9-82da-099a2455ffda": (310, 30, 0),    # #PWR0303 +3.3V
        "79cf47a2-4484-4a55-a20f-77d65dec5712": (420, 30, 0),    # #PWR0304 +3.3V
        "211d8c8b-1e0e-41f5-be21-59e3e226cf1e": (510, 30, 0),    # #PWR0305 +3.3V
        "48bf34e1-a3f5-49e4-8c38-7e3a96132641": (60, 200, 0),    # #PWR0306 GND
        "31da5eec-3bf7-4fc2-8ba9-0a2a944bfb3f": (180, 200, 0),   # #PWR0307 GND
        "65279993-460d-42a8-be21-f34bc3b03e6b": (310, 165, 0),   # #PWR0308 GND
        "d16b7ac9-9038-4895-a003-4cafe44e634e": (420, 165, 0),   # #PWR0309 GND
        "c1d687dd-b3d7-4b40-8420-864b774f9bd0": (510, 200, 0),   # #PWR0310 GND
        "da7dead3-0c5a-4e9f-ba99-ae323893cce9": (70, 30, 0),     # #FLG0301
        "b1202e5e-bdf5-4566-a134-c5194c992054": (190, 30, 0),    # #FLG0302

        # ── Zone 1: Left Motor Driver DRV8243 (x: 40-110, y: 50-200) ──
        "5c519583-b8cf-4f5e-be6a-e08e4dcf413b": (70, 90, 0),     # U5L DRV8243
        "15c5936c-81e2-4eaf-80b3-f60e2e208c15": (40, 55, 0),     # C11L 100nF
        "0ad45836-86c7-4005-8dae-06b5d4a2d81e": (55, 55, 0),     # C12L 10uF bulk
        "acd7108b-b647-480c-9f94-2a932941cab7": (40, 70, 0),     # C13L 100nF
        "44b755b1-5374-41a7-8fec-ef125aeac696": (100, 55, 0),    # TVS1L
        "5d6dbea7-b36b-45f0-a226-cd2d1bdbe463": (100, 70, 0),    # R3L 10m shunt
        "a73f508a-81f7-4249-a7e8-040de6a86d4e": (45, 170, 0),    # J_MOTOR_L
        "4a4e8798-a6b2-42f0-9d55-7ec7d7945839": (90, 170, 0),    # J_ENC_L

        # ── Zone 2: Right Motor Driver DRV8243 (x: 150-230, y: 50-200) ──
        "46c90747-4d76-4dfd-b17a-7298028fec3f": (190, 90, 0),    # U5R DRV8243
        "828cb43b-6523-4474-973b-f963dda03830": (160, 55, 0),    # C11R 100nF
        "eb590bcb-7f07-42a0-95c4-9de5754f157b": (175, 55, 0),    # C12R 10uF bulk
        "a12907b0-a955-4701-853e-d18304710c75": (160, 70, 0),    # C13R 100nF
        "3072db25-9e3e-4842-8f56-59f81466720b": (220, 55, 0),    # TVS1R
        "c6fc5ff3-d514-4341-81b9-428c51f79a70": (220, 70, 0),    # R3R 10m shunt
        "a0da5d48-9d2d-4257-95a3-7c5db4ab9b9a": (165, 170, 0),   # J_MOTOR_R
        "bf638442-ca65-4f63-8648-cd51d95ae14d": (210, 170, 0),   # J_ENC_R

        # ── Zone 3: CAN Transceivers (x: 280-370, y: 50-170) ──
        "9eff1bc4-7af3-4eaa-b8eb-3c19c27fe967": (310, 75, 0),    # U6A SN65HVD230 (CAN1 arm)
        "79be43bd-d90d-42fc-ba8d-b4de80b12839": (295, 60, 0),    # R4A 120 termination
        "bf18efb1-ecf1-49e2-8c1f-f20c269b21f0": (330, 60, 0),    # C14A 100nF
        "e61bd494-3132-4e44-9825-5ed1099de157": (360, 75, 0),    # J_CAN_ARM connector

        "6917175b-38eb-455e-abc7-85f4a10716ae": (310, 135, 0),   # U6S SN65HVD230 (CAN2 sensor)
        "8b831d09-daea-49f8-9554-01b952ad8d86": (295, 120, 0),   # R4S 120 termination
        "94cc26b7-8b42-4d5e-ae48-a7078b21bb3d": (330, 120, 0),   # C14S 100nF

        # ── Zone 4: IMU ICM-42688-P (x: 400-460, y: 50-150) ──
        "8a9e13d7-74e1-42a1-aed5-bcfdb85a6cd7": (430, 90, 0),   # U7 ICM-42688-P
        "478f9fa3-80e2-4e2e-b2d3-4f8f0b2864b6": (410, 55, 0),   # C15 100nF
        "b1c8f7fa-c875-4a65-af10-75cdc7fff39e": (425, 55, 0),    # C16 1uF
        "5c78aeaf-88ad-4b9f-8b80-c757b10e22e2": (450, 55, 0),    # R5 4.7k

        # ── Zone 5: INA226 x3 Power Monitors (x: 490-570, y: 50-200) ──
        "24ba34e2-eb70-4d79-8a49-2e68924684f9": (530, 65, 0),    # U8 INA226 (25V rail)
        "ea70401a-4718-4ffb-9964-0072361d512d": (510, 55, 0),    # R6 10m shunt
        "5cf75046-c147-47db-8eae-0dc7177a2225": (555, 55, 0),    # C17 100nF

        "f3dcd452-88c6-4d90-93f5-2372eb49c8d1": (530, 120, 0),   # U9 INA226 (12V rail)
        "b19fed25-a525-47e8-aa69-1090b5226c3b": (510, 110, 0),   # R7 10m shunt
        "a4076db8-2eaa-4b71-9bc5-42a54d99ec6e": (555, 110, 0),   # C18 100nF

        "a4f18f47-4222-4a21-8cd2-cf97b93ec122": (530, 175, 0),   # U10 INA226 (5V rail)
        "b6f47d12-d00b-4aca-859a-0026f52ef554": (510, 165, 0),   # R8 10m shunt
        "2ed794f8-6315-475d-9d30-d5fd714f4126": (555, 165, 0),   # C19 100nF
    }

    for uuid, (x, y, angle) in positions.items():
        content = update_symbol_position(content, uuid, x, y, angle)

    label_positions = {
        # Motor driver L labels
        "997a5003-7492-4e11-93e5-be636fa9ee30": (45, 85, 180),   # SPI1_SCK (L)
        "6da59958-1e82-4c30-b23f-36df169a8d0e": (45, 92, 180),   # SPI1_CS_DRV_L
        "d1b5b627-093b-438c-80cf-be67da02864e": (45, 99, 180),   # SPI1_MOSI (L)
        "db365462-9ec2-4d96-8847-5c55d63e77ce": (45, 106, 180),  # SPI1_MISO (L)
        "ac73e2d9-e577-4b7c-8e4e-6424a615a7f3": (50, 45, 0),     # MOTOR_PWR_L

        # Motor driver R labels
        "f3a9d9bb-2572-479b-8a21-286ba4da63a9": (165, 85, 180),  # SPI1_SCK (R)
        "2a194e43-7118-4848-a074-a7a969f0ed1b": (165, 92, 180),  # SPI1_CS_DRV_R
        "e1f74255-bad6-4d26-96f8-292780e6af13": (165, 99, 180),  # SPI1_MOSI (R)
        "0eb8a60c-1eeb-49a6-b093-3b76c4c2f928": (165, 106, 180), # SPI1_MISO (R)
        "99bbecb4-3f41-46cf-b31d-18f50557b188": (170, 45, 0),    # MOTOR_PWR_R

        # Encoder labels
        "1ebf20a3-2c4b-4cb1-9297-c4c393b8c839": (90, 165, 0),    # ENC_L_A
        "d9ce2161-4015-4457-953b-e3bb4d35c3aa": (90, 172, 0),    # ENC_L_B
        "a3bd6c65-42be-4371-b4be-81ed3e73a4ad": (210, 165, 0),   # ENC_R_A
        "b5e14667-645c-4e8e-bda4-b1a8910f5ee0": (210, 172, 0),   # ENC_R_B

        # CAN labels
        "6d4329fd-6c25-4dc4-8f10-1db86403ccf2": (290, 72, 180),  # CAN1_TX
        "b2684d70-934c-48f4-b9b3-1457c7d63efe": (290, 79, 180),  # CAN1_RX
        "6c2567f1-3ed4-4ab0-a33c-ce267912d9a9": (290, 132, 180), # CAN2_TX
        "0752c200-fbb3-430c-b3a7-772d177fc12c": (290, 139, 180), # CAN2_RX
        "57f4f248-6a16-4eea-971b-f8f9771621c3": (365, 72, 0),    # CAN_H_ARM
        "cf6fb18c-b75b-4928-90a0-f4b19256b4ff": (365, 79, 0),    # CAN_L_ARM

        # IMU SPI labels
        "5a497256-78e4-4ba2-a589-adf511cfbfaf": (410, 85, 180),  # SPI1_SCK (IMU)
        "1ba12c1d-667b-46fe-abd2-27816fb32b32": (410, 92, 180),  # SPI1_CS_IMU
        "5ef6b147-beb6-4996-9fb0-17d724b1c044": (410, 99, 180),  # SPI1_MOSI (IMU)
        "1500a09d-34cc-47d7-8640-5872eee296fc": (410, 106, 180), # SPI1_MISO (IMU)

        # INA226 I2C labels
        "0f85426d-4c53-4203-ae0a-d8010ddc2e04": (510, 80, 180),  # I2C1_SCL
        "73d3cf3d-0f4e-48e5-968d-3c361fe89d05": (510, 87, 180),  # I2C1_SDA

        # Power rail labels for INA226
        "4189467d-1cc6-43ff-872e-8e12e8f70df9": (505, 50, 0),    # VCC_25V
        "6031719b-f1c1-4e3a-92d1-72818d22b89d": (505, 105, 0),   # VCC_12V
        "124dd487-409a-4bdd-b824-ba7e46a8b73e": (505, 160, 0),   # VCC_5V
    }

    for uuid, (x, y, angle) in label_positions.items():
        content = update_label_position(content, uuid, x, y, angle)

    with open(filepath, 'w') as f:
        f.write(content)
    print("  ✓ Drivers/CAN/IMU/Power rearranged")


# ─── Connectors, LED, USB Layout ───
# A2 sheet. Groups: LED driver | LED status | Jetson/LiDAR/Camera | Bumpers

def rearrange_connectors():
    filepath = f"{PROJECT}/Connectors_LED_USB.kicad_sch"
    print(f"\n{'='*60}")
    print(f"Rearranging: Connectors, LED, USB")
    print(f"{'='*60}")
    backup(filepath)

    with open(filepath, 'r') as f:
        content = f.read()

    positions = {
        # ── Power symbols ──
        "5864965a-95b0-4ac1-8b87-05c3703394a3": (70, 40, 0),     # #PWR0401 +12V (LED)
        "d2f10353-8c6a-4435-bf0e-95c2fcd80972": (200, 40, 0),    # #PWR0402 +5V (LED status)
        "b2fb20cc-ffcf-4f13-b011-b51b6f2c9dc9": (300, 40, 0),    # #PWR0403 +5V (Jetson)
        "68e62778-ab68-4dcc-9747-9dd8387ffebc": (360, 40, 0),    # #PWR0404 +12V (LiDAR)
        "d7ea2536-9521-45fb-95ca-7a0be2367258": (420, 40, 0),    # #PWR0405 +5V (Camera)
        "0266f495-d391-4cc7-82ef-9d8be6e08985": (70, 175, 0),    # #PWR0406 GND (LED)
        "c5f29a43-6da9-4d5a-a138-76ebcc9a370f": (200, 155, 0),   # #PWR0407 GND (status)
        "362ce9d6-16d4-4ea5-a5b9-ab929cf49b5f": (300, 130, 0),   # #PWR0408 GND (Jetson)
        "b2cd9098-a3d4-4725-a2ee-ebbf99409fca": (360, 130, 0),   # #PWR0409 GND (LiDAR)
        "5e82d627-f034-4683-84d6-03138bc9e23c": (470, 120, 0),   # #PWR0410 GND (bumper FL)
        "108eefc0-35bc-48f2-b39a-f6f902958a56": (500, 120, 0),   # #PWR0411 GND (bumper FR)
        "8c2aaff8-4a6b-414e-b67b-e8d8c56ca606": (530, 120, 0),   # #PWR0412 GND (bumper RL)
        "bc213c6d-0726-47f4-bcb5-a764dae70558": (560, 120, 0),   # #PWR0413 GND (bumper RR)
        "77a19f2f-0cd1-49b9-8922-a24401d11eb4": (80, 40, 0),     # #FLG0401
        "6da1754f-2a69-4f78-ace1-03b6f150e332": (210, 40, 0),    # #FLG0402

        # ── Zone 1: PT4115 LED Driver (x: 50-150, y: 60-175) ──
        "9b3178ea-d73b-48a0-b6e0-20ab3ae6c31c": (90, 100, 0),    # U11 PT4115
        "26641ed9-0bb3-4202-a0ce-5601708a8e9d": (65, 75, 0),     # L_LED 22uH
        "9aeda2dc-84a8-48a3-aee1-2b7d597f7ac1": (65, 130, 0),    # D_LED SS34
        "6b1da8c8-7e3d-43df-9c48-5d8aeddd166f": (115, 130, 0),   # R10 0.1 sense
        "55ae4fdd-dd1c-40aa-9115-17625eb6a57e": (135, 100, 0),   # J_LED_WORK connector

        # ── Zone 2: LED Status (x: 180-240, y: 60-155) ──
        "3e121387-ebf4-4876-8959-b6fd632de9f0": (200, 80, 0),    # R9 470
        "25955b21-e167-4077-809a-7300899feca4": (200, 115, 0),    # C20 100uF
        "fc0a5ea6-b05d-424a-81b4-f1ee4bcc0722": (225, 90, 0),    # J_LED_STATUS connector

        # ── Zone 3: Compute Connectors (x: 280-430, y: 60-130) ──
        "b4e3039b-d6f0-4931-851a-2d3e40dcf15c": (300, 80, 0),    # J_JETSON
        "161f9766-2945-4ce1-92b9-c156d9363654": (360, 80, 0),    # J_LIDAR
        "6a050601-d38a-47ef-a5a3-16c17ea22472": (420, 80, 0),    # J_CAMERA

        # ── Zone 4: Bumper Connectors (x: 460-570, y: 60-120) ──
        "0eebf142-3a7e-4287-ab2c-fb4543afec15": (470, 80, 0),    # J_BUMPER_FL
        "43cd79d8-6a08-46bc-87da-7c6f7b435625": (500, 80, 0),    # J_BUMPER_FR
        "28de20c6-0ec2-490a-91ad-38db5d7ef18e": (530, 80, 0),    # J_BUMPER_RL
        "75ef9a4a-4f7c-49dc-a612-6a36dd736660": (560, 80, 0),    # J_BUMPER_RR
    }

    for uuid, (x, y, angle) in positions.items():
        content = update_symbol_position(content, uuid, x, y, angle)

    label_positions = {
        "b734d3a3-0b82-45b0-859c-7278294b6dbf": (70, 50, 0),     # VCC_12V (LED)
        "94ff0123-e5a9-4a62-8326-bb016dc6b90a": (200, 50, 0),    # VCC_5V (status)
        "663d798d-72ca-4381-979f-c8a0a3561652": (300, 72, 0),    # USART2_TX
        "08ebcfd7-9ea5-4d60-8596-ed78cac39225": (300, 79, 0),    # USART2_RX
        "cd9f0196-9a61-4d9c-8e26-8ef0b820655d": (360, 50, 0),   # VCC_12V (LiDAR)
        "7921d8ba-f6b7-4363-a2c5-490668ea8710": (420, 50, 0),    # VCC_5V (camera)
        "26e943a2-e425-463d-b244-be511cb1f92e": (470, 72, 0),    # BUMPER_FL
        "64e454fc-3a90-44e0-956f-820a7c65e6fc": (500, 72, 0),    # BUMPER_FR
        "bac14b29-95f2-43bc-a837-aee8a894eb22": (530, 72, 0),    # BUMPER_RL
        "9940952c-3f68-47f3-ad6c-0500890415a0": (560, 72, 0),    # BUMPER_RR
    }

    for uuid, (x, y, angle) in label_positions.items():
        content = update_label_position(content, uuid, x, y, angle)

    with open(filepath, 'w') as f:
        f.write(content)
    print("  ✓ Connectors/LED/USB rearranged")


# ─── Main ───

if __name__ == "__main__":
    print("RECLAIM KiCad Schematic Rearrangement Script")
    print("=" * 60)
    print("Make sure KiCad is CLOSED before running!")
    print()

    rearrange_power()
    rearrange_stm32()
    rearrange_drivers()
    rearrange_connectors()

    print(f"\n{'='*60}")
    print("All 4 sheets rearranged!")
    print("Open KiCad and verify the layout.")
    print("Backups saved as .bak_TIMESTAMP files.")
    print(f"{'='*60}")
