#!/usr/bin/env python3
"""
RECLAIM KiCad Schematic — Tighter layout pass v2
- Shrinks page sizes (A1/A2 → A3)
- Much tighter component spacing within groups
- Same logical grouping as v1
"""

import re
import shutil
from datetime import datetime

PROJECT = "/Users/shadysiam/Documents/RECLAIM/docs/product_pcb_electrical/kicad_project/RECLAIM_PCB"


def backup(filepath):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{filepath}.bak_{ts}"
    shutil.copy2(filepath, dst)
    print(f"  Backed up → {dst}")


def update_position(content, uuid, new_x, new_y, new_angle=0):
    """Find a symbol or label by UUID and update its (at X Y angle)."""
    uuid_str = f'(uuid "{uuid}")'
    uuid_idx = content.find(uuid_str)
    if uuid_idx == -1:
        print(f"  WARNING: UUID {uuid} not found!")
        return content

    # Find nearest (at ...) searching backwards from UUID
    # Look for the block start first
    block_start = max(
        content.rfind('(symbol\n', 0, uuid_idx),
        content.rfind('(symbol\r\n', 0, uuid_idx),
        content.rfind('(label ', 0, uuid_idx),
    )
    if block_start == -1:
        print(f"  WARNING: No block found for UUID {uuid}")
        return content

    block = content[block_start:uuid_idx]
    at_match = re.search(r'\(at\s+[\d.\-]+\s+[\d.\-]+\s+[\d.\-]+\)', block)
    if not at_match:
        print(f"  WARNING: No (at ...) for UUID {uuid}")
        return content

    new_at = f"(at {new_x} {new_y} {new_angle})"
    abs_start = block_start + at_match.start()
    abs_end = block_start + at_match.end()
    content = content[:abs_start] + new_at + content[abs_end:]
    return content


def change_paper_size(content, new_size):
    """Change paper size (e.g., A1 → A3)."""
    content = re.sub(r'\(paper "A\d"\)', f'(paper "{new_size}")', content)
    return content


# ═══════════════════════════════════════════════════════════
# POWER DISTRIBUTION — A3 (420×297mm), usable ~25-395 x 25-272
# Signal flow: Battery → Fuses → E-stop/Relay → Post-relay → Buck1 → Buck2 → LDO
# ═══════════════════════════════════════════════════════════

def rearrange_power():
    filepath = f"{PROJECT}/Power_Distribution.kicad_sch"
    print(f"\n{'='*50}\nPower Distribution\n{'='*50}")
    backup(filepath)
    with open(filepath, 'r') as f:
        content = f.read()

    content = change_paper_size(content, "A3")

    moves = {
        # ── Power symbols row (y=30) ──
        "218a529b-34f7-4746-8b82-bf87cc1e01b4": (40, 28, 0),     # +24V
        "6eacd9fd-c749-4363-a8eb-b9e62ce16d4c": (48, 28, 0),     # PWR_FLAG
        "1d0bce40-fbcc-49d5-9298-127123b4d567": (100, 28, 0),    # GND
        "2c30a088-85ee-48d1-9585-58d4187a6ac5": (108, 28, 0),    # PWR_FLAG
        "655a14b7-fe49-4d92-a944-d41ba70e8468": (230, 28, 0),    # +12V
        "d987bdfd-c770-4c13-ad9e-7205540a562f": (305, 28, 0),    # +5V
        "5ecdcca9-aa69-461a-bbb9-eceb22b520ea": (365, 28, 0),    # +3.3V

        # ── Battery Input (x:35-50) ──
        "0271a66d-03b9-4928-8516-3d7e6166d643": (35, 80, 0),     # J1 battery

        # ── Main Fuses (x:60-75, stacked vertically) ──
        "ec5c3c3e-645e-4fbc-b02c-0c1b3e601caf": (65, 60, 0),    # F1 30A motor
        "3b7224a9-434f-4b83-afb3-045eb7a01411": (65, 95, 0),     # F4 5A compute
        "1dba3700-6afc-4df6-a6a4-0b22ad0ab596": (65, 130, 0),    # F5 2A coil

        # ── E-Stop Circuit (x:85-145, y:110-170) ──
        "fe8d3759-b3bd-4f81-915c-95516a5e35b7": (90, 135, 0),    # SW1 mushroom
        "11ef1442-2092-4bf4-9088-dd026c0008ad": (110, 125, 0),   # R11 1k
        "5e1b5fcb-a597-4f9a-9046-43f7c76645cd": (110, 150, 0),   # R12 47k
        "e66bf026-06d2-4f0a-b267-44dd27e11f94": (125, 138, 0),   # Q1 IRLZ44N
        "15666073-f58f-40e6-9481-3b95865d87b2": (145, 85, 0),    # K1 relay
        "35e00f6c-959f-45a1-9510-d80b9f9f0315": (155, 108, 0),   # D2 flyback
        "73483bd4-b952-4fe5-a4de-2fcece5d2b6c": (155, 75, 0),    # D1
        "dbc40c46-e866-45b4-8db9-50778865d1f5": (140, 115, 0),   # R1
        "94d77f3c-7185-426c-9f94-ce243094991e": (140, 130, 0),   # R2

        # ── Post-Relay Fuses + Bulk Cap (x:175-195) ──
        "eb2e5b79-0031-4f38-80a0-e597daf139d3": (180, 55, 0),    # F2L 15A
        "5366a762-9cfb-414e-b662-c1f3c430d333": (180, 70, 0),    # F2R 15A
        "84bf3116-a6bf-4b28-8e9a-88f49b513132": (180, 85, 0),    # F3 10A
        "b8c1a8e7-871d-4bba-857e-d1967b119301": (185, 105, 0),   # C1 bulk 470uF

        # ── Buck 1: U1 LM5116 25V→12V (x:210-260) ──
        "57470893-2118-405b-960c-8b873285f41d": (225, 80, 0),    # U1 LM5116
        "065bb558-bf44-4d76-823d-7fd99495b9a0": (250, 65, 0),    # L_BUCK1
        "b5a3a363-4d7d-48cc-89c7-d3da8a45658b": (240, 100, 0),   # D_BUCK1
        "efa23de1-425e-463a-8f1c-412a2c069b6c": (255, 95, 0),    # R_FB1A
        "f1dc9d81-f969-4e8c-a34a-52b5de1cdb2c": (255, 108, 0),   # R_FB1B
        "ed5289dd-c5df-4e89-ad74-bb7cb3628d9c": (262, 72, 0),    # C2 470uF
        "d70ea75e-fa45-4c44-9347-e7c90a7f45e2": (262, 85, 0),    # C5 100nF

        # ── Buck 2: U2 TPS5430 12V→5V (x:280-330) ──
        "b86a1092-f70e-4dde-962f-2414e0ecc894": (295, 80, 0),    # U2 TPS5430
        "2ce5c534-3bec-4ebc-8a15-fd736e864abe": (320, 65, 0),    # L_BUCK2
        "97b87a5e-473b-4154-82d6-edee46345264": (310, 100, 0),   # D_BUCK2
        "2a3a4b3f-515d-4f52-b522-bea6fc5a9ad6": (325, 95, 0),    # R_FB2A
        "4401a498-0b5f-4a79-8382-ddc7151196f0": (325, 108, 0),   # R_FB2B
        "f11d634c-16dd-42cb-850b-6bf3ae32c3aa": (332, 72, 0),    # C3 470uF
        "b37172a6-3552-49dd-af44-62cd1bc25469": (332, 85, 0),    # C6 100nF

        # ── LDO: U3 AMS1117 5V→3.3V (x:350-390) ──
        "790dd384-11fb-4829-ae4e-7df92f52853f": (365, 80, 0),    # U3 AMS1117
        "09ec7415-7bbe-4f6e-a2d9-b73a7b2b338a": (385, 72, 0),    # C4
        "b3a10346-327c-4b38-aa87-00850fd68f0a": (385, 85, 0),    # C7
        "b358ba64-d90a-459c-a630-5ab711658a13": (385, 98, 0),    # C8
    }

    for uuid, (x, y, a) in moves.items():
        content = update_position(content, uuid, x, y, a)

    labels = {
        "be714c51-80b7-420e-b0f6-5252490baf3c": (50, 75, 0),     # VBAT
        "0eebd179-6592-4792-9f3a-b64d1d045a85": (65, 52, 0),     # VBAT_MOTOR
        "ba2c7890-24ae-4e19-ab03-8faa1fde1b9e": (65, 87, 0),     # VBAT_COMPUTE
        "5a838ac4-79ff-416b-9f98-ea0962f5eb00": (65, 122, 0),    # VBAT_COIL
        "d02561fc-289b-4455-a261-8882bfd0e6ae": (175, 48, 0),    # VCC_25V
        "7e6f4267-f041-4ec5-a6c0-142b9dcf5d92": (225, 55, 0),    # VCC_12V
        "04e69aa9-3dcd-403c-a834-b70648efada9": (295, 55, 0),    # VCC_5V
        "c3cc8659-83b8-462a-9c27-4fd78b802ce5": (365, 55, 0),    # VCC_3V3
        "480dd68f-610f-44f5-932d-261e91f431f7": (105, 135, 0),   # RELAY_COIL_IN
        "423a5216-c50e-4f9c-a290-b5acb14e8907": (125, 125, 0),   # ESTOP_RELAY_CTRL
        "e950e386-f5e5-4688-828b-15487ed29a7b": (130, 165, 0),   # GND (e-stop)
        "0829d84c-d495-4a1a-b4f9-b6ecbeba53b1": (185, 118, 0),  # GND (post-relay)
        "3716e67b-3375-4e57-96ce-5807ede29478": (245, 118, 0),   # GND (buck1)
        "0c7012bc-4a88-4663-80ae-40249bc8669c": (375, 108, 0),   # GND (LDO)
    }

    for uuid, (x, y, a) in labels.items():
        content = update_position(content, uuid, x, y, a)

    with open(filepath, 'w') as f:
        f.write(content)
    print("  ✓ Done")


# ═══════════════════════════════════════════════════════════
# STM32 MCU — A3 (420×297mm)
# Crystal left, STM32 center, pull-ups & USB right, caps below
# ═══════════════════════════════════════════════════════════

def rearrange_stm32():
    filepath = f"{PROJECT}/STM32_MCU.kicad_sch"
    print(f"\n{'='*50}\nSTM32 MCU\n{'='*50}")
    backup(filepath)
    with open(filepath, 'r') as f:
        content = f.read()

    content = change_paper_size(content, "A3")

    moves = {
        # Power (top)
        "7b192c73-e5aa-4bd6-b67a-c7aa299b5337": (120, 30, 0),   # +3.3V (STM32)
        "54f01a4a-afe2-4a35-837c-7e064f0dc235": (130, 30, 0),    # PWR_FLAG
        "1ca7b541-32c0-4531-b9f2-b4b9d08beac8": (290, 30, 0),   # +3.3V (USB)
        "980ceecd-a7ab-4b46-8067-9f94c1f8d6ec": (300, 30, 0),    # PWR_FLAG
        "d71d3f22-9db1-4dd8-ae55-8786c4d4859c": (120, 195, 0),   # GND (STM32)
        "21f87d65-6747-44ba-8353-6379f2ece9b9": (290, 155, 0),   # GND (USB)
        "aa0d8e79-1948-4df0-871d-3cf7baf715d0": (155, 230, 0),   # GND (caps)
        "643c516c-d7c2-4e97-8d89-17d7a8bd8a08": (365, 120, 0),   # GND (SWD)

        # Crystal (left of STM32)
        "8eb7d939-f3c7-4136-b46e-4c298a54eed4": (70, 85, 0),     # Y1 8MHz
        "397c1e64-a3fa-4452-addf-582582854301": (60, 98, 0),      # C9 22pF
        "023f9cf5-3f9f-4360-bbe5-3eb29d5a8a56": (80, 98, 0),      # C10 22pF

        # STM32 (center)
        "b720eef4-f0a3-490b-ad32-3a7236aeaa21": (150, 100, 0),   # U4 STM32F405

        # Decoupling caps (below STM32)
        "d86db769-995a-48d0-a290-6c8e8c902cb1": (120, 215, 0),   # C_VDD1
        "522dde4d-7645-4904-ad2f-37813222b5a5": (132, 215, 0),   # C_VDD_BULK
        "bb442db7-e177-4ead-a489-4f5e072ae040": (144, 215, 0),   # C_VCAP1
        "bb947850-89fa-4fd3-ad8a-60ec837838fe": (156, 215, 0),   # C_VCAP2
        "1ec1ab58-b2d9-44d8-8303-b29e4b766e66": (168, 215, 0),   # C_NRST

        # Pull-up resistors (right of STM32)
        "a21302b4-1fd6-484b-8c3e-f20fc0b6b78a": (230, 80, 0),    # R1 10k
        "48939cf1-8ecf-4982-b26b-5b4736f247c6": (230, 95, 0),    # R2 10k
        "41558208-b4c7-4021-95ce-6cf877b7bbee": (230, 115, 0),   # R_I2C_SCL
        "536f5b71-6b6c-40a3-a177-165fac4ef926": (230, 130, 0),   # R_I2C_SDA

        # CP2102N USB-UART (right)
        "3db9f912-f10f-4728-82f7-0a180f3d45e3": (295, 90, 0),    # U_USB

        # Connectors (far right)
        "7e7ac6e6-d996-4afc-9c1a-65a821ed6a69": (365, 70, 0),    # J_SWD
        "bd9e66d1-fdca-4b39-85ce-548a6893d34d": (365, 110, 0),   # J_USB
    }

    for uuid, (x, y, a) in moves.items():
        content = update_position(content, uuid, x, y, a)

    labels = {
        "bc957e23-ebd3-481a-a283-d8a44ea37c50": (120, 35, 0),    # VCC_3V3
        "b1e4a6ed-f43a-448e-973e-76cfc0b850ad": (120, 190, 0),   # GND
        # SPI (left of STM32)
        "7d642da8-d3d6-413c-8b86-c1bdac39f9f8": (100, 75, 180),  # SPI1_SCK
        "5332a8ac-0710-4b61-8a7f-fa038751febe": (100, 80, 180),  # SPI1_MOSI
        "b3f0872d-773a-4b75-9fe0-ec8d81c9711b": (100, 85, 180),  # SPI1_MISO
        "08332ece-d08d-4a57-990e-0e0ee95e8eef": (100, 95, 180),  # SPI1_CS_DRV_L
        "3ec6bd41-6aae-49c0-a378-e007ed049f8e": (100, 100, 180), # SPI1_CS_DRV_R
        "8d338aea-0275-437d-8c07-7d9e257eae3f": (100, 105, 180), # SPI1_CS_IMU
        # CAN
        "fa11ef71-1a93-4741-8939-487909130475": (100, 115, 180),  # CAN1_TX
        "4ec48f09-28bf-422f-a99d-3e49e49d1b70": (100, 120, 180), # CAN1_RX
        "4fed448e-dafc-49af-9ff7-b3bf5ce6f7a5": (100, 130, 180), # CAN2_TX
        "c4f1c6e7-72f9-49d8-8346-9bc56ea3ae0c": (100, 135, 180), # CAN2_RX
        # UART
        "0a93c48c-2f88-4267-91ae-c3b9d6285ea7": (100, 145, 180), # USART2_TX
        "8fc47f2c-39d1-44d5-8541-0051c6bdc02a": (100, 150, 180), # USART2_RX
        # I2C
        "6d000d64-d56f-4b45-ad87-31fe33b611c8": (100, 160, 180), # I2C1_SCL
        "6a9543d8-c06c-4c10-b84a-c5303337801d": (100, 165, 180), # I2C1_SDA
        # Right side of STM32
        "81c21b30-3a89-47ad-9c21-39008e81e682": (205, 90, 0),    # ENC_L_A
        "3f212a4f-c7a1-4c52-91f3-2ed92558b933": (205, 95, 0),    # ENC_L_B
        "2f4a20eb-54e1-4fc2-a13e-f4677bfedf3c": (205, 105, 0),   # ENC_R_A
        "08e42bb7-fd88-43a4-adc5-df750b42a3b8": (205, 110, 0),   # ENC_R_B
        "cc20016e-d455-4334-8c5c-c6c47fb82f23": (205, 125, 0),   # ESTOP_RELAY_CTRL
        # USB side
        "e0e891f3-0be8-49a7-8c2c-d586dd3b649f": (275, 85, 180),  # USART2_TX
        "fc8d0dc8-bf2a-4df0-b5ef-62a43661527b": (275, 95, 180),  # USART2_RX
    }

    for uuid, (x, y, a) in labels.items():
        content = update_position(content, uuid, x, y, a)

    with open(filepath, 'w') as f:
        f.write(content)
    print("  ✓ Done")


# ═══════════════════════════════════════════════════════════
# DRIVERS, CAN, IMU, POWER — A3 (420×297mm)
# Left DRV | Right DRV | CAN | IMU | INA226×3
# ═══════════════════════════════════════════════════════════

def rearrange_drivers():
    filepath = f"{PROJECT}/Drivers_CAN_IMU_Power.kicad_sch"
    print(f"\n{'='*50}\nDrivers CAN IMU Power\n{'='*50}")
    backup(filepath)
    with open(filepath, 'r') as f:
        content = f.read()

    content = change_paper_size(content, "A3")

    moves = {
        # Power symbols
        "f1207480-4af4-4074-b8ac-461a412f70c9": (40, 25, 0),     # +3.3V (L drv)
        "da7dead3-0c5a-4e9f-ba99-ae323893cce9": (48, 25, 0),     # FLG
        "b298b0b1-66d9-4d1c-91b0-af2cbd75bb27": (125, 25, 0),    # +3.3V (R drv)
        "b1202e5e-bdf5-4566-a134-c5194c992054": (133, 25, 0),    # FLG
        "a7f9eef9-5414-4fa9-82da-099a2455ffda": (210, 25, 0),    # +3.3V (CAN)
        "79cf47a2-4484-4a55-a20f-77d65dec5712": (290, 25, 0),    # +3.3V (IMU)
        "211d8c8b-1e0e-41f5-be21-59e3e226cf1e": (350, 25, 0),    # +3.3V (INA)
        "48bf34e1-a3f5-49e4-8c38-7e3a96132641": (40, 165, 0),    # GND (L)
        "31da5eec-3bf7-4fc2-8ba9-0a2a944bfb3f": (125, 165, 0),   # GND (R)
        "65279993-460d-42a8-be21-f34bc3b03e6b": (210, 135, 0),   # GND (CAN)
        "d16b7ac9-9038-4895-a003-4cafe44e634e": (290, 135, 0),   # GND (IMU)
        "c1d687dd-b3d7-4b40-8420-864b774f9bd0": (350, 165, 0),   # GND (INA)

        # ── Left Motor Driver (x:30-85) ──
        "5c519583-b8cf-4f5e-be6a-e08e4dcf413b": (50, 70, 0),     # U5L DRV8243
        "15c5936c-81e2-4eaf-80b3-f60e2e208c15": (30, 42, 0),     # C11L
        "0ad45836-86c7-4005-8dae-06b5d4a2d81e": (40, 42, 0),     # C12L bulk
        "acd7108b-b647-480c-9f94-2a932941cab7": (30, 55, 0),     # C13L
        "44b755b1-5374-41a7-8fec-ef125aeac696": (75, 42, 0),     # TVS1L
        "5d6dbea7-b36b-45f0-a226-cd2d1bdbe463": (75, 55, 0),     # R3L shunt
        "a73f508a-81f7-4249-a7e8-040de6a86d4e": (35, 140, 0),    # J_MOTOR_L
        "4a4e8798-a6b2-42f0-9d55-7ec7d7945839": (65, 140, 0),    # J_ENC_L

        # ── Right Motor Driver (x:110-170) ──
        "46c90747-4d76-4dfd-b17a-7298028fec3f": (135, 70, 0),    # U5R DRV8243
        "828cb43b-6523-4474-973b-f963dda03830": (115, 42, 0),    # C11R
        "eb590bcb-7f07-42a0-95c4-9de5754f157b": (125, 42, 0),    # C12R bulk
        "a12907b0-a955-4701-853e-d18304710c75": (115, 55, 0),    # C13R
        "3072db25-9e3e-4842-8f56-59f81466720b": (160, 42, 0),    # TVS1R
        "c6fc5ff3-d514-4341-81b9-428c51f79a70": (160, 55, 0),    # R3R shunt
        "a0da5d48-9d2d-4257-95a3-7c5db4ab9b9a": (120, 140, 0),   # J_MOTOR_R
        "bf638442-ca65-4f63-8648-cd51d95ae14d": (150, 140, 0),   # J_ENC_R

        # ── CAN Transceivers (x:195-255) ──
        "9eff1bc4-7af3-4eaa-b8eb-3c19c27fe967": (215, 55, 0),    # U6A (CAN1)
        "79be43bd-d90d-42fc-ba8d-b4de80b12839": (200, 42, 0),    # R4A term
        "bf18efb1-ecf1-49e2-8c1f-f20c269b21f0": (230, 42, 0),    # C14A
        "e61bd494-3132-4e44-9825-5ed1099de157": (248, 55, 0),    # J_CAN_ARM

        "6917175b-38eb-455e-abc7-85f4a10716ae": (215, 105, 0),   # U6S (CAN2)
        "8b831d09-daea-49f8-9554-01b952ad8d86": (200, 92, 0),    # R4S term
        "94cc26b7-8b42-4d5e-ae48-a7078b21bb3d": (230, 92, 0),    # C14S

        # ── IMU (x:275-315) ──
        "8a9e13d7-74e1-42a1-aed5-bcfdb85a6cd7": (295, 65, 0),   # U7 ICM-42688
        "478f9fa3-80e2-4e2e-b2d3-4f8f0b2864b6": (280, 42, 0),   # C15
        "b1c8f7fa-c875-4a65-af10-75cdc7fff39e": (290, 42, 0),    # C16
        "5c78aeaf-88ad-4b9f-8b80-c757b10e22e2": (310, 42, 0),    # R5

        # ── INA226 ×3 (x:335-395) ──
        "24ba34e2-eb70-4d79-8a49-2e68924684f9": (365, 48, 0),    # U8 (25V)
        "ea70401a-4718-4ffb-9964-0072361d512d": (350, 40, 0),    # R6 shunt
        "5cf75046-c147-47db-8eae-0dc7177a2225": (385, 40, 0),    # C17

        "f3dcd452-88c6-4d90-93f5-2372eb49c8d1": (365, 90, 0),    # U9 (12V)
        "b19fed25-a525-47e8-aa69-1090b5226c3b": (350, 82, 0),    # R7 shunt
        "a4076db8-2eaa-4b71-9bc5-42a54d99ec6e": (385, 82, 0),    # C18

        "a4f18f47-4222-4a21-8cd2-cf97b93ec122": (365, 132, 0),   # U10 (5V)
        "b6f47d12-d00b-4aca-859a-0026f52ef554": (350, 124, 0),   # R8 shunt
        "2ed794f8-6315-475d-9d30-d5fd714f4126": (385, 124, 0),   # C19
    }

    for uuid, (x, y, a) in moves.items():
        content = update_position(content, uuid, x, y, a)

    labels = {
        # Left driver SPI
        "997a5003-7492-4e11-93e5-be636fa9ee30": (30, 65, 180),   # SPI1_SCK
        "6da59958-1e82-4c30-b23f-36df169a8d0e": (30, 70, 180),   # CS_DRV_L
        "d1b5b627-093b-438c-80cf-be67da02864e": (30, 75, 180),   # MOSI
        "db365462-9ec2-4d96-8847-5c55d63e77ce": (30, 80, 180),   # MISO
        "ac73e2d9-e577-4b7c-8e4e-6424a615a7f3": (35, 35, 0),     # MOTOR_PWR_L
        # Right driver SPI
        "f3a9d9bb-2572-479b-8a21-286ba4da63a9": (115, 65, 180),  # SPI1_SCK
        "2a194e43-7118-4848-a074-a7a969f0ed1b": (115, 70, 180),  # CS_DRV_R
        "e1f74255-bad6-4d26-96f8-292780e6af13": (115, 75, 180),  # MOSI
        "0eb8a60c-1eeb-49a6-b093-3b76c4c2f928": (115, 80, 180),  # MISO
        "99bbecb4-3f41-46cf-b31d-18f50557b188": (120, 35, 0),    # MOTOR_PWR_R
        # Encoders
        "1ebf20a3-2c4b-4cb1-9297-c4c393b8c839": (65, 135, 0),    # ENC_L_A
        "d9ce2161-4015-4457-953b-e3bb4d35c3aa": (65, 140, 0),    # ENC_L_B
        "a3bd6c65-42be-4371-b4be-81ed3e73a4ad": (150, 135, 0),   # ENC_R_A
        "b5e14667-645c-4e8e-bda4-b1a8910f5ee0": (150, 140, 0),   # ENC_R_B
        # CAN
        "6d4329fd-6c25-4dc4-8f10-1db86403ccf2": (198, 52, 180),  # CAN1_TX
        "b2684d70-934c-48f4-b9b3-1457c7d63efe": (198, 57, 180),  # CAN1_RX
        "6c2567f1-3ed4-4ab0-a33c-ce267912d9a9": (198, 102, 180), # CAN2_TX
        "0752c200-fbb3-430c-b3a7-772d177fc12c": (198, 107, 180), # CAN2_RX
        "57f4f248-6a16-4eea-971b-f8f9771621c3": (252, 52, 0),    # CAN_H_ARM
        "cf6fb18c-b75b-4928-90a0-f4b19256b4ff": (252, 57, 0),    # CAN_L_ARM
        # IMU SPI
        "5a497256-78e4-4ba2-a589-adf511cfbfaf": (278, 62, 180),  # SPI1_SCK
        "1ba12c1d-667b-46fe-abd2-27816fb32b32": (278, 67, 180),  # CS_IMU
        "5ef6b147-beb6-4996-9fb0-17d724b1c044": (278, 72, 180),  # MOSI
        "1500a09d-34cc-47d7-8640-5872eee296fc": (278, 77, 180),  # MISO
        # INA I2C
        "0f85426d-4c53-4203-ae0a-d8010ddc2e04": (345, 60, 180),  # I2C1_SCL
        "73d3cf3d-0f4e-48e5-968d-3c361fe89d05": (345, 65, 180),  # I2C1_SDA
        # Power rail labels
        "4189467d-1cc6-43ff-872e-8e12e8f70df9": (345, 35, 0),    # VCC_25V
        "6031719b-f1c1-4e3a-92d1-72818d22b89d": (345, 77, 0),    # VCC_12V
        "124dd487-409a-4bdd-b824-ba7e46a8b73e": (345, 119, 0),   # VCC_5V
    }

    for uuid, (x, y, a) in labels.items():
        content = update_position(content, uuid, x, y, a)

    with open(filepath, 'w') as f:
        f.write(content)
    print("  ✓ Done")


# ═══════════════════════════════════════════════════════════
# CONNECTORS, LED, USB — A3 (420×297mm)
# LED driver | LED status | Jetson/LiDAR/Camera | Bumpers
# ═══════════════════════════════════════════════════════════

def rearrange_connectors():
    filepath = f"{PROJECT}/Connectors_LED_USB.kicad_sch"
    print(f"\n{'='*50}\nConnectors LED USB\n{'='*50}")
    backup(filepath)
    with open(filepath, 'r') as f:
        content = f.read()

    content = change_paper_size(content, "A3")

    moves = {
        # Power symbols
        "5864965a-95b0-4ac1-8b87-05c3703394a3": (50, 30, 0),     # +12V (LED)
        "77a19f2f-0cd1-49b9-8922-a24401d11eb4": (58, 30, 0),     # FLG
        "d2f10353-8c6a-4435-bf0e-95c2fcd80972": (130, 30, 0),    # +5V (status)
        "6da1754f-2a69-4f78-ace1-03b6f150e332": (138, 30, 0),    # FLG
        "b2fb20cc-ffcf-4f13-b011-b51b6f2c9dc9": (195, 30, 0),   # +5V (Jetson)
        "68e62778-ab68-4dcc-9747-9dd8387ffebc": (240, 30, 0),    # +12V (LiDAR)
        "d7ea2536-9521-45fb-95ca-7a0be2367258": (280, 30, 0),    # +5V (Camera)

        "0266f495-d391-4cc7-82ef-9d8be6e08985": (50, 130, 0),    # GND (LED)
        "c5f29a43-6da9-4d5a-a138-76ebcc9a370f": (130, 115, 0),   # GND (status)
        "362ce9d6-16d4-4ea5-a5b9-ab929cf49b5f": (195, 100, 0),   # GND (Jetson)
        "b2cd9098-a3d4-4725-a2ee-ebbf99409fca": (240, 100, 0),   # GND (LiDAR)
        "5e82d627-f034-4683-84d6-03138bc9e23c": (325, 95, 0),    # GND (FL)
        "108eefc0-35bc-48f2-b39a-f6f902958a56": (345, 95, 0),    # GND (FR)
        "8c2aaff8-4a6b-414e-b67b-e8d8c56ca606": (365, 95, 0),    # GND (RL)
        "bc213c6d-0726-47f4-bcb5-a764dae70558": (385, 95, 0),    # GND (RR)

        # ── LED Driver PT4115 (x:35-95) ──
        "9b3178ea-d73b-48a0-b6e0-20ab3ae6c31c": (60, 70, 0),     # U11 PT4115
        "26641ed9-0bb3-4202-a0ce-5601708a8e9d": (45, 52, 0),     # L_LED
        "9aeda2dc-84a8-48a3-aee1-2b7d597f7ac1": (45, 95, 0),     # D_LED
        "6b1da8c8-7e3d-43df-9c48-5d8aeddd166f": (78, 95, 0),     # R10 sense
        "55ae4fdd-dd1c-40aa-9115-17625eb6a57e": (92, 70, 0),     # J_LED_WORK

        # ── LED Status (x:120-155) ──
        "3e121387-ebf4-4876-8959-b6fd632de9f0": (130, 55, 0),    # R9 470
        "25955b21-e167-4077-809a-7300899feca4": (130, 85, 0),     # C20 100uF
        "fc0a5ea6-b05d-424a-81b4-f1ee4bcc0722": (150, 65, 0),    # J_LED_STATUS

        # ── Compute Connectors (x:185-290) ──
        "b4e3039b-d6f0-4931-851a-2d3e40dcf15c": (200, 60, 0),    # J_JETSON
        "161f9766-2945-4ce1-92b9-c156d9363654": (245, 60, 0),    # J_LIDAR
        "6a050601-d38a-47ef-a5a3-16c17ea22472": (285, 60, 0),    # J_CAMERA

        # ── Bumper Connectors (x:315-395) ──
        "0eebf142-3a7e-4287-ab2c-fb4543afec15": (325, 60, 0),    # BUMPER_FL
        "43cd79d8-6a08-46bc-87da-7c6f7b435625": (345, 60, 0),    # BUMPER_FR
        "28de20c6-0ec2-490a-91ad-38db5d7ef18e": (365, 60, 0),    # BUMPER_RL
        "75ef9a4a-4f7c-49dc-a612-6a36dd736660": (385, 60, 0),    # BUMPER_RR
    }

    for uuid, (x, y, a) in moves.items():
        content = update_position(content, uuid, x, y, a)

    labels = {
        "b734d3a3-0b82-45b0-859c-7278294b6dbf": (50, 38, 0),     # VCC_12V
        "94ff0123-e5a9-4a62-8326-bb016dc6b90a": (130, 38, 0),    # VCC_5V
        "663d798d-72ca-4381-979f-c8a0a3561652": (200, 52, 0),    # USART2_TX
        "08ebcfd7-9ea5-4d60-8596-ed78cac39225": (200, 57, 0),    # USART2_RX
        "cd9f0196-9a61-4d9c-8e26-8ef0b820655d": (240, 38, 0),   # VCC_12V
        "7921d8ba-f6b7-4363-a2c5-490668ea8710": (280, 38, 0),    # VCC_5V
        "26e943a2-e425-463d-b244-be511cb1f92e": (325, 52, 0),    # BUMPER_FL
        "64e454fc-3a90-44e0-956f-820a7c65e6fc": (345, 52, 0),    # BUMPER_FR
        "bac14b29-95f2-43bc-a837-aee8a894eb22": (365, 52, 0),    # BUMPER_RL
        "9940952c-3f68-47f3-ad6c-0500890415a0": (385, 52, 0),    # BUMPER_RR
    }

    for uuid, (x, y, a) in labels.items():
        content = update_position(content, uuid, x, y, a)

    with open(filepath, 'w') as f:
        f.write(content)
    print("  ✓ Done")


if __name__ == "__main__":
    print("RECLAIM Schematic — Tight Layout Pass v2")
    print("=" * 50)
    rearrange_power()
    rearrange_stm32()
    rearrange_drivers()
    rearrange_connectors()
    print(f"\n{'='*50}")
    print("All sheets: A3, tighter layout. Open KiCad to verify.")
    print("=" * 50)
