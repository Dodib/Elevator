import threading
from enum import Enum
import time


class ElevatorDirection(Enum):
    Stop = 0
    Down = 1
    Up = 2


class FloorPanelStates(Enum):
    Off = 0
    Down = 1
    Up = 2
    Both = 3


class EventType(Enum):
    FloorPanel = 0
    ElevatorPosition = 1
    ElevatorRestart = 2
    ElevatorButtonPress = 3


class Elevator:

    def __init__(self, elevator_id):
        self.elevator_id = elevator_id
        self.elevator_destinations = []
        self.direction = ElevatorDirection.Stop
        self.floor_position = 0
        self.door_open = False
        self.door_open_time_counter = 0

    def set_floor_position(self, position: int):
        self.floor_position = position
        print(f"cart {self.elevator_id} - new position : {self.floor_position}")

    def get_floor_position(self):
        return self.floor_position

    def add_new_destination(self, floor: int):
        self.elevator_destinations.append(floor)
        if self.direction == ElevatorDirection.Stop:
            if self.floor_position < floor:
                self.start_cabs_motor(ElevatorDirection.Up)
            else:
                self.start_cabs_motor(ElevatorDirection.Down)
        print(f"cart: {self.elevator_id} - new destinations {self.elevator_destinations}")

    def remove_destination(self, floor: int):
        self.elevator_destinations.remove(floor)
        print(f"cart {self.elevator_id} - removed destination {floor} -"
              f" current destinations: {self.elevator_destinations}")

    def get_elevator_destinations(self):
        return self.elevator_destinations

    def get_elevator_direction(self):
        return self.direction

    def stop_cabs_motor(self):
        # Send a signal to the motor controlling this specific cab
        # TODO: write code here
        print(f"stopping_cab : {self.elevator_id}")

    def start_cabs_motor(self, direction: ElevatorDirection):
        if self.direction == ElevatorDirection.Stop:
            self.direction = direction
        elif self.direction != ElevatorDirection.Stop and direction is None:
            # it has a direction, but might not have any destination ahead. i.e. it has already handled all floor
            # requests, it should now reverse direction and handle the internal requests
            # i.e. where people want to go out
            if self.direction == ElevatorDirection.Up and len(self.elevator_destinations) != 0:
                # check if any floors above the current position is present, if not, change direction
                has_unhandled_floors = False
                for floor_level in self.elevator_destinations:
                    if floor_level > self.floor_position:
                        has_unhandled_floors = True
                        break
                if not has_unhandled_floors:
                    self.direction = ElevatorDirection.Down
            elif self.direction == ElevatorDirection.Down and len(self.elevator_destinations) != 0:
                # check if any floors below the current position is present, if not, change direction
                has_unhandled_floors = False
                for floor_level in self.elevator_destinations:
                    if floor_level < self.floor_position:
                        has_unhandled_floors = True
                        break
                if not has_unhandled_floors:
                    self.direction = ElevatorDirection.Up
            else:
                # it has no destinations, thus stop and idle, until instructions are given
                self.direction = ElevatorDirection.Stop

        # Send a signal to the motor controlling this specific cab
        # TODO: write code here
        print(f"starting_cab: {self.elevator_id} - current destinations: {self.elevator_destinations}"
              f" - cart direction: {self.direction}")

    def open_cabs_door(self):
        # set the cabs door status to open, this is to that the timer can start
        self.door_open = True
        self.door_open_time_counter = time.process_time()
        # Send a signal to the cab to open this cabs door
        # TODO: write code here
        print(f"opening_cab : {self.elevator_id}")

    def close_cabs_door(self):
        # set the cabs door status to closed
        self.door_open = False
        # Send a signal to the cab to close this cabs door
        # TODO: write code here
        print(f"closing_cab : {self.elevator_id}")


class FloorPanel:

    def __init__(self, floor_level):
        self.floor_level = floor_level
        self.floor_state = FloorPanelStates.Off

    def get_floor_state(self):
        return self.floor_state

    def change_panel_state(self, state: FloorPanelStates):
        if state == 0:
            self.floor_state = FloorPanelStates.Off
        elif state == 1:
            self.floor_state = FloorPanelStates.Down
        elif state == 2:
            self.floor_state = FloorPanelStates.Up
        elif state == 3:
            self.floor_state = FloorPanelStates.Both


class EventMessage:
    # message: Tuple(Int, Int)
    # event_type: EventType (enum)
    def __init__(self, event_type, message):
        self.message = message
        self.event_type = event_type


class EventChannel:
    # hold all the events
    events: EventMessage = []

    def add_new_event(self, event: EventMessage):
        self.events.append(event)

    def clear_events(self):
        self.events.clear()


class ElevatorSystem:

    def __init__(self, floor_levels, elevator_size):
        self.event_channel = EventChannel()
        self.elevator_dict = {i: Elevator(i) for i in range(elevator_size)}
        self.floor_panel_dict = {j: FloorPanel(j) for j in range(floor_levels)}
        self.temporary_input_producer = None
        self.elevator_event_handler = ElevatorEventHandler(self.event_channel, self.floor_panel_dict,
                                                           self.elevator_dict)

    def start(self):
        while True:
            # poll all input sources and update the systems states
            self.update_system_state()
            if EventChannel.events:
                self.elevator_event_handler.handle_events(self.event_channel.events)
                self.event_channel.clear_events()
            time.sleep(0.5)

    def update_system_state(self):
        # update all floor panel states
        self.update_panel_states()
        # update all elevator states
        self.update_elevator_states()

    def update_panel_states(self):
        # TODO: FOR TESTING PURPOSE; in actuallity: Should fetch data from the input pins and create events accordingly
        # temporary way to obtain info:
        temporary_floor_panel_info = self.temporary_input_producer.floor_panel_info.copy()
        self.temporary_input_producer.floor_panel_info.clear()
        for i in range(len(temporary_floor_panel_info)):
            button_state = temporary_floor_panel_info.pop()
            if button_state[0] in self.floor_panel_dict:
                floor_panel = self.floor_panel_dict[button_state[0]]
                if floor_panel.get_floor_state() != button_state[1]:
                    floor_panel.change_panel_state(button_state[1])
                    # create a new event
                    event = EventMessage(EventType.FloorPanel, button_state)
                    self.event_channel.add_new_event(event)

    def update_elevator_states(self):
        # update all the elevators currently operating and handling requests (e.g. elevators with open doors)
        for i, elevator in self.elevator_dict.items():
            if elevator.door_open:
                if elevator.door_open_time_counter + 100000 >= time.process_time():
                    # create a new event, to close the cart and continue operating
                    self.event_channel.add_new_event(EventMessage(EventType.ElevatorRestart, tuple([i, None])))

        # TODO: FOR TESTING PURPOSE; in actuallity: Should fetch data from the input pins and create events accordingly
        # TODO: delete
        # temporary way of obtaining input
        temporary_elevator_position_info = self.temporary_input_producer.elevator_position_info.copy()
        self.temporary_input_producer.elevator_position_info.clear()
        for i in range(len(temporary_elevator_position_info)):
            elevator_state = temporary_elevator_position_info.pop()
            if elevator_state[0] in self.elevator_dict:
                # create a new event
                self.event_channel.add_new_event(EventMessage(EventType.ElevatorPosition, elevator_state))
        # temporary way of obtaining input
        temporary_elevator_button_info = self.temporary_input_producer.elevator_buttons_info.copy()
        self.temporary_input_producer.elevator_buttons_info.clear()
        for i in range(len(temporary_elevator_button_info)):
            elevator_state = temporary_elevator_button_info.pop()
            if elevator_state[0] in self.elevator_dict:
                # create a new event
                self.event_channel.add_new_event(EventMessage(EventType.ElevatorButtonPress, elevator_state))


class ElevatorEventHandler:

    def __init__(self, event_channel, floor_panels, elevators):
        self.event_channel = event_channel
        self.elevator_list = elevators
        self.floor_panels_list = floor_panels
        self.scheduler = Scheduler()

    def handle_events(self, events):
        for event in events:
            if event.event_type == EventType.FloorPanel:
                self.call_elevator(event.message)
            elif event.event_type == EventType.ElevatorPosition:
                self.update_elevator_position(event.message)
            elif event.event_type == EventType.ElevatorRestart:
                self.continue_cabs_operation(event.message)
            elif event.event_type == EventType.ElevatorButtonPress:
                self.update_elevator_destination(event.message)

    def call_elevator(self, floor_press: tuple):
        # obtain most suitable cab to handle the floor button request
        elevator = self.scheduler.get_most_suitable_elevator_for_reqeuest(floor_press, self.elevator_list)
        # add a new destination in the elevator cab
        elevator.add_new_destination(floor_press[0])

    def update_elevator_position(self, message: tuple):
        if message[0] in self.elevator_list:
            elevator = self.elevator_list[message[0]]
            elevator.set_floor_position(message[1])
            if message[1] in elevator.elevator_destinations:
                # this floor is part of this cab's destinations, thus reset this floors panel
                self.stop_and_open_elevator_cab(elevator)

    def stop_and_open_elevator_cab(self, elevator: Elevator):
        # remove the current floor from this elevator's destinations
        elevator.remove_destination(elevator.get_floor_position())
        elevator.stop_cabs_motor()
        elevator.open_cabs_door()
        # reset this floors panel button state
        if elevator.floor_position in self.floor_panels_list:
            self.floor_panels_list[elevator.floor_position].change_panel_state(FloorPanelStates.Off)

    def continue_cabs_operation(self, message: tuple):
        if message[0] in self.elevator_list:
            elevator = self.elevator_list[message[0]]
            elevator.close_cabs_door()
            elevator.start_cabs_motor(None)

    def update_elevator_destination(self, message: tuple):
        if message[0] in self.elevator_list:
            elevator = self.elevator_list[message[0]]
            elevator.add_new_destination(message[1])


class Scheduler:

    def get_most_suitable_elevator_for_reqeuest(self, event_message, elevators: dict):
        # Algorithm: if a cab is idle, send this cab to the request
        # if all cabs are busy, find the one closest to the request which is moving in the same direction, that has
        # yet to pass the requested floor. If not are found, find the cab with the least request and assign it this
        # new request
        for i, elevator in elevators.items():
            if elevator.direction == ElevatorDirection.Stop:
                return elevator
        # No elevators are idle, thus find the most fitting one
        elevators_going_same_direction = []
        # find all elevators going in the same direction
        for elevator in elevators.values():
            if elevator.get_elevator_direction().value == event_message[1] or\
                    event_message[1] == FloorPanelStates.Both.value:
                elevators_going_same_direction.append(elevator)
        # find the ones that have not passed this floor yet
        elevators_pre_requested_floor = []
        for elevator in elevators_going_same_direction:
            if elevator.get_elevator_direction() == ElevatorDirection.Up:
                if elevator.get_floor_position() < event_message[0]:
                    elevators_pre_requested_floor.append(elevator)
            else:
                if elevator.get_floor_position() > event_message[0]:
                    elevators_pre_requested_floor.append(elevator)
        # find the closest elevator
        index_of_closest_elevator = None
        for i, elevator in enumerate(elevators_pre_requested_floor):
            if index_of_closest_elevator is None:
                index_of_closest_elevator = i
                continue
            closest_floor_diff = abs(elevators_pre_requested_floor[index_of_closest_elevator].get_floor_position()
                                     - event_message[0])
            current_floor_diff = abs(elevator.get_floor_position() - event_message[0])
            if closest_floor_diff > current_floor_diff:
                index_of_closest_elevator = i
        if index_of_closest_elevator is not None:
            return elevators_pre_requested_floor[index_of_closest_elevator]
        # if this place is reached then all elevators are busy, thus find the one with the least requests
        # and assign it this request
        least_used_elevator = elevators[0]
        for i in range(1, len(elevators)):
            if len(elevator.get_elevator_destinations()) < len(least_used_elevator.get_elevator_destinations()):
                least_used_elevator = elevators[i]
        return least_used_elevator


# TODO: delete
# Temporary class used for testing functionality
class InputProducer(threading.Thread):
    floor_panel_info = []
    elevator_position_info = []
    elevator_buttons_info = []

    def run(self):
        # use this function to do manual tests

        # fb:0,2 --> command : floor, direction
        # i.e. floor button (fb) pressed at floor 0, wanting to go up (2)

        # pos:0,5 --> command : cartID, floor
        # i.e. means cart's position (pos). cart 0, arrived at floor 5. in real life it would go up incrementally
        # e.g. pos:0,5 -> pos:0,6 -> pos:0,7

        # eb:0,3 --> command : cartID, floor
        # eb == Elevator button. The example means elevator panel in cart 0, has been pressed to move towards floor 3
        # e.g. eb:1,5 --> means the people in cart 1 wants to go to floor 5

        while True:
            try:
                x = input("--input data:\n")
                if x.startswith("fb"):
                    floor_click = x.split(":")[1].split(",")
                    self.floor_panel_info.append(tuple([int(floor_click[0]), int(floor_click[1])]))
                elif x.startswith("pos"):
                    elevator_position = x.split(":")[1].split(",")
                    self.elevator_position_info.append(tuple([int(elevator_position[0]), int(elevator_position[1])]))
                elif x.startswith("eb"):
                    elevator_position = x.split(":")[1].split(",")
                    self.elevator_buttons_info.append(tuple([int(elevator_position[0]), int(elevator_position[1])]))
            except:
                pass
            time.sleep(0.1)

    def run_example(self):
        # should end with both elevators stopping, cab 0 at floor index 2 and cab 1 at floor index 1
        # i.e. ElevatorDirection.Stop with 0 destinations
        self.floor_panel_info.append(tuple([8, 1]))
        self.floor_panel_info.append(tuple([9, 1]))
        time.sleep(1)
        self.elevator_position_info.append(tuple([0, 5]))
        self.elevator_position_info.append(tuple([1, 3]))
        time.sleep(1)
        self.floor_panel_info.append(tuple([7, 2]))
        time.sleep(1)
        self.elevator_position_info.append(tuple([0, 7]))
        self.elevator_position_info.append(tuple([1, 8]))
        time.sleep(1)
        self.elevator_buttons_info.append(tuple([0, 2]))
        self.elevator_buttons_info.append(tuple([1, 1]))
        self.elevator_position_info.append(tuple([0, 9]))
        time.sleep(1)
        self.elevator_position_info.append(tuple([0, 2]))
        self.elevator_position_info.append(tuple([1, 1]))


if __name__ == '__main__':
    # init
    elevator_size_init = 2
    floor_levels_init = 10
    elevator_system = ElevatorSystem(floor_levels_init, elevator_size_init)
    #elevator_system.start()

    # TODO: This is for testing purposes
    input_producer = InputProducer()
    elevator_system.temporary_input_producer = input_producer
    # start threads
    main_thread = threading.Thread(target=elevator_system.start)
    # to run example
    input_thread = threading.Thread(target=input_producer.run_example)
    # to run manual test
    #input_thread = threading.Thread(target=input_producer.run)
    try:
        main_thread.start()
        input_thread.start()
        main_thread.join()
        input_thread.join()
    except:
        pass
