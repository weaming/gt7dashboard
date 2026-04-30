import os
import socket
import time
import unittest
from types import SimpleNamespace

from gt7dashboard import gt7communication
from gt7dashboard.gt7lap import Lap

PLAYSTATION_IP = 'ps5wifi'


class GT7CommunicationSocketTest(unittest.TestCase):
    def test_send_heartbeat_returns_false_when_restart_closed_socket(self):
        gt7comm = gt7communication.GT7Communication('127.0.0.1')
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        gt7comm._socket = udp_socket

        gt7comm.restart()

        self.assertFalse(gt7comm._send_hb(udp_socket))

    def test_first_observed_lap_does_not_finish_current_lap(self):
        gt7comm = gt7communication.GT7Communication('127.0.0.1')
        gt7comm.last_data = SimpleNamespace(current_fuel=90)
        gt7comm.current_lap.data_speed = [100]

        gt7comm._handle_lap_transition(current_lap_number=2, last_lap_time=60000, best_lap_time=60000)

        self.assertEqual(0, len(gt7comm.laps))
        self.assertEqual(2, gt7comm._previous_lap)
        self.assertEqual([100], gt7comm.current_lap.data_speed)

    def test_regular_lap_advance_finishes_current_lap(self):
        gt7comm = gt7communication.GT7Communication('127.0.0.1')
        gt7comm._previous_lap = 1
        gt7comm.current_lap.data_speed = [100]
        gt7comm.current_lap.lap_ticks = 60
        gt7comm.last_data = SimpleNamespace(
            current_fuel=90,
            last_lap=60000,
            total_laps=2,
            current_lap=2,
            car_id=1,
            estimated_top_speed=250,
        )

        gt7comm._handle_lap_transition(current_lap_number=2, last_lap_time=60000, best_lap_time=60000)

        self.assertEqual(1, len(gt7comm.laps))
        self.assertEqual(1, gt7comm.laps[0].number)
        self.assertEqual([], gt7comm.current_lap.data_speed)
        self.assertEqual(90, gt7comm.current_lap.fuel_at_start)

    def test_lap_number_reset_discards_unfinished_lap(self):
        gt7comm = gt7communication.GT7Communication('127.0.0.1')
        gt7comm._previous_lap = 2
        gt7comm.current_lap.data_speed = [100]
        gt7comm.last_data = SimpleNamespace(current_fuel=95)

        gt7comm._handle_lap_transition(current_lap_number=1, last_lap_time=60000, best_lap_time=60000)

        self.assertEqual(0, len(gt7comm.laps))
        self.assertEqual(1, gt7comm._previous_lap)
        self.assertEqual([], gt7comm.current_lap.data_speed)
        self.assertEqual(95, gt7comm.current_lap.fuel_at_start)

    def test_delete_laps_by_indices(self):
        gt7comm = gt7communication.GT7Communication('127.0.0.1')
        gt7comm.laps = [Lap(), Lap(), Lap()]
        gt7comm.laps[0].number = 0
        gt7comm.laps[1].number = 1
        gt7comm.laps[2].number = 2

        removed_laps = gt7comm.delete_laps_by_indices([1, 99, 1])

        self.assertEqual([1], [lap.number for lap in removed_laps])
        self.assertEqual([0, 2], [lap.number for lap in gt7comm.laps])


# check if host is up
def is_host_up(ip: str) -> bool:
    response = os.system('ping -c 1 ' + PLAYSTATION_IP)

    # and then check the response...
    if response == 0:
        return True
    else:
        return False


@unittest.skipIf(not is_host_up(PLAYSTATION_IP), 'Playstation host is not up on %s' % (PLAYSTATION_IP))
class GT7CommunicationTest(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.gt7comm = gt7communication.GT7Communication(PLAYSTATION_IP)
        # Do not quit with the main process
        self.gt7comm.daemon = False
        self.gt7comm.start()
        # Sleep until connection is setup
        # TODO Add timeout
        while not self.gt7comm.is_connected():
            time.sleep(0.1)

    @classmethod
    def tearDownClass(self) -> None:
        self.gt7comm.stop()

    def test_get_water_temp(self):
        car_data = self.gt7comm.get_last_data()
        self.assertTrue(self.gt7comm.is_connected())
        # is always 85
        self.assertEqual(85, car_data.water_temp)

    # def test_run_add_debug(self):
    #     while self.gt7comm.is_connected():
    #         car_data = self.gt7comm.get_last_data()
    #         # print(car_data.rpm, car_data.in_race)

    def test_load_laps(self):
        self.gt7comm.laps = [Lap()]
        self.gt7comm.laps[0].number = 0

        laps = [Lap(), Lap()]
        laps[0].number = 1
        laps[1].number = 2

        self.gt7comm.load_laps(laps, to_last_position=True)
        self.assertEqual(3, len(self.gt7comm.laps))
        self.assertEqual(1, self.gt7comm.laps[1].number)

        self.gt7comm.load_laps(laps, to_first_position=True)
        self.assertEqual(5, len(self.gt7comm.laps))
        self.assertEqual(1, self.gt7comm.laps[3].number)

        self.gt7comm.load_laps(laps, replace_other_laps=True)
        self.assertEqual(2, len(self.gt7comm.laps))
        self.assertEqual(1, self.gt7comm.laps[0].number)
