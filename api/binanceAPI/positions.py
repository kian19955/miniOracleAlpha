from . import client

def get_open_positions():
    positions = client.futures_position_information()

    open_positions = [pos for pos in positions if float(pos['positionAmt']) != 0.0]

    return open_positions