from rafcon.mvc.mygaphas.items.connection import ConnectionView
from rafcon.utils import log
logger = log.get_logger(__name__)


def extend_extents(extents, factor=1.1):
    """Extend a given bounding box

    The bounding box (x1, y1, x2, y2) is centrally stretched by the given factor.

    :param extents: The bound box extents
    :param factor: The factor for stretching
    :return: (x1, y1, x2, y2) of the extended bounding box
    """
    width = extents[2] - extents[0]
    height = extents[3] - extents[1]
    add_width = (factor - 1) * width
    add_height = (factor - 1) * height
    x1 = extents[0] - add_width / 2
    x2 = extents[2] + add_width / 2
    y1 = extents[1] - add_height / 2
    y2 = extents[3] + add_height / 2
    return x1, y1, x2, y2


def calc_rel_pos_to_parent(canvas, item, handle):
    """This method calculates the relative position of the given item's handle to its parent

    :param canvas: Canvas to find relative position in
    :param item: Item to find relative position to parent
    :param handle: Handle of item to find relative position to
    :return: Relative position (x, y)
    """
    from gaphas.item import NW

    if isinstance(item, ConnectionView):
        return item.canvas.get_matrix_i2i(item, item.parent).transform_point(*handle.pos)

    parent = canvas.get_parent(item)
    if parent:
        return item.canvas.get_matrix_i2i(item, parent).transform_point(*handle.pos)
    else:
        return item.canvas.get_matrix_i2c(item).transform_point(*item.handles()[NW].pos)


def assert_exactly_one_true(bool_list):
    """This method asserts that only one value of the provided list is True.

    :param bool_list: List of booleans to check
    :return: True if only one value is True, False otherwise
    """
    assert isinstance(bool_list, list)
    counter = 0
    for item in bool_list:
        if item:
            counter += 1
    return counter == 1


def get_state_id_for_port(port):
    """This method returns the state ID of the state containing the given port

    :param port: Port to check for containing state ID
    :return: State ID of state containing port
    """
    parent = port.parent
    from rafcon.mvc.mygaphas.items.state import StateView
    if isinstance(parent, StateView):
        return parent.model.state.state_id


def get_port_for_handle(handle, state):
    """Looks for and returns the PortView to the given handle in the provided state

    :param handle: Handle to look for port
    :param state: State containing handle and port
    :returns: PortView for handle
    """
    from rafcon.mvc.mygaphas.items.state import StateView
    if isinstance(state, StateView):
        if state.income.handle == handle:
            return state.income
        else:
            for outcome in state.outcomes:
                if outcome.handle == handle:
                    return outcome
            for input in state.inputs:
                if input.handle == handle:
                    return input
            for output in state.outputs:
                if output.handle == handle:
                    return output
            for scoped in state.scoped_variables:
                if scoped.handle == handle:
                    return scoped


def create_new_connection(from_port, to_port):
    """Checks the type of connection and tries to create it

    If bot port are logical port,s a transition is created. If both ports are data ports (including scoped variable),
    then a data flow is added. An error log is created, when the types are not compatible.

    :param from_port: The starting port of the connection
    :param to_port: The end point of the connection
    :return: True if a new connection was added
    """
    from rafcon.mvc.mygaphas.items.ports import ScopedVariablePortView, LogicPortView, DataPortView

    if isinstance(from_port, LogicPortView) and isinstance(to_port, LogicPortView):
        return add_transition_to_state(from_port, to_port)
    elif isinstance(from_port, (DataPortView, ScopedVariablePortView)) and \
            isinstance(to_port, (DataPortView, ScopedVariablePortView)):
        return add_data_flow_to_state(from_port, to_port)
    # Both ports are not None
    elif from_port and to_port:
        logger.error("Connection of non-compatible ports: {0} and {1}".format(type(from_port), type(to_port)))

    return False


def add_data_flow_to_state(from_port, to_port):
    """Interface method between Gaphas and RAFCON core for adding data flows

    The method checks the types of the given ports and their relation. From this the necessary parameters for the
    add_dat_flow method of the RAFCON core are determined. Also the parent state is derived from the ports.

    :param from_port: Port from which the data flow starts
    :param to_port: Port to which the data flow goes to
    :return: True if a data flow was added, False if an error occurred
    """
    from rafcon.mvc.mygaphas.items.ports import InputPortView, OutputPortView, ScopedVariablePortView
    from rafcon.mvc.models.container_state import ContainerStateModel

    from_state_v = from_port.parent
    to_state_v = to_port.parent

    from_state_m = from_state_v.model
    to_state_m = to_state_v.model

    from_state_id = from_state_m.state.state_id
    to_state_id = to_state_m.state.state_id

    from_port_id = from_port.port_id
    to_port_id = to_port.port_id

    if not isinstance(from_port, (InputPortView, OutputPortView, ScopedVariablePortView)) or \
            not isinstance(from_port, (InputPortView, OutputPortView, ScopedVariablePortView)):
        logger.error("Data flows only exist between data ports (input, output, scope). Given: {0} and {1}".format(type(
            from_port), type(to_port)))
        return False

    responsible_parent_m = None

    # from parent to child
    if isinstance(from_state_m, ContainerStateModel) and to_state_m.state.state_id in from_state_m.state.states:
        responsible_parent_m = from_state_m
    # from child to parent
    elif isinstance(to_state_m, ContainerStateModel) and from_state_m.state.state_id in to_state_m.state.states:
        responsible_parent_m = to_state_m
    # from parent to parent
    elif isinstance(from_state_m, ContainerStateModel) and from_state_m.state.state_id == to_state_m.state.state_id:
        responsible_parent_m = from_state_m  # == to_state_m
    # from child to child
    elif (not from_state_m.state.is_root_state) and (not to_state_m.state.is_root_state) \
            and from_state_m.state.state_id != to_state_m.state.state_id \
            and from_state_m.parent.state.state_id and to_state_m.parent.state.state_id:
        responsible_parent_m = from_state_m.parent

    if not isinstance(responsible_parent_m, ContainerStateModel):
        logger.error("Data flows only exist in container states (e.g. hierarchy states)")
        return False

    try:
        responsible_parent_m.state.add_data_flow(from_state_id, from_port_id, to_state_id, to_port_id)
        return True
    except (ValueError, AttributeError, TypeError) as e:
        logger.error("Data flow couldn't be added: {0}".format(e))
        return False


def add_transition_to_state(from_port, to_port):
    """Interface method between Gaphas and RAFCON core for adding transitions

    The method checks the types of the given ports (IncomeView or OutcomeView) and from this determines the necessary
    parameters for the add_transition method of the RAFCON core. Also the parent state is derived from the ports.

    :param from_port: Port from which the transition starts
    :param to_port: Port to which the transition goes to
    :return: True if a transition was added, False if an error occurred
    """
    from rafcon.mvc.mygaphas.items.ports import IncomeView, OutcomeView

    from_state_v = from_port.parent
    to_state_v = to_port.parent

    from_state_m = from_state_v.model
    to_state_m = to_state_v.model

    # Gather necessary information to create transition
    from_state_id = from_state_m.state.state_id
    to_state_id = to_state_m.state.state_id

    responsible_parent_m = None

    # Start transition
    if isinstance(from_port, IncomeView):
        from_state_id = None
        from_outcome_id = None
        responsible_parent_m = from_state_m
        # Transition from parent income to child income
        if isinstance(to_port, IncomeView):
            to_outcome_id = None
        # Transition from parent income to parent outcome
        elif isinstance(to_port, OutcomeView):
            to_outcome_id = to_port.outcome_id
    elif isinstance(from_port, OutcomeView):
        from_outcome_id = from_port.outcome_id
        # Transition from child outcome to child income
        if isinstance(to_port, IncomeView):
            responsible_parent_m = from_state_m.parent
            to_outcome_id = None
        # Transition from child outcome to parent outcome
        elif isinstance(to_port, OutcomeView):
            responsible_parent_m = to_state_m
            to_outcome_id = to_port.outcome_id
    else:
        raise ValueError("Invalid port type")

    from rafcon.mvc.models.container_state import ContainerStateModel
    if not responsible_parent_m:
        logger.error("Transitions only exist between incomes and outcomes. Given: {0} and {1}".format(type(
            from_port), type(to_port)))
        return False
    elif not isinstance(responsible_parent_m, ContainerStateModel):
        logger.error("Transitions only exist in container states (e.g. hierarchy states)")
        return False

    try:
        responsible_parent_m.state.add_transition(from_state_id, from_outcome_id, to_state_id, to_outcome_id)
        return True
    except (ValueError, AttributeError, TypeError) as e:
        logger.error("Transition couldn't be added: {0}".format(e))
        return False


def get_relative_positions_of_waypoints(transition_v):
    """This method takes the waypoints of a connection and returns all relative positions of these waypoints.

    :param canvas: Canvas to check relative position in
    :param transition_v: Transition view to extract all relative waypoint positions
    :return: List with all relative positions of the given transition
    """
    handles_list = transition_v.handles()
    rel_pos_list = []
    for handle in handles_list:
        if handle in transition_v.end_handles(include_waypoints=True):
            continue
        rel_pos = transition_v.canvas.get_matrix_i2i(transition_v, transition_v.parent).transform_point(*handle.pos)
        rel_pos_list.append(rel_pos)
    return rel_pos_list


def update_meta_data_for_transition_waypoints(graphical_editor_view, transition_v, last_waypoint_list):
    """This method updates the relative position meta data of the transitions waypoints if they changed

    :param graphical_editor_view: Graphical Editor the change occurred in
    :param transition_v: Transition that changed
    :param last_waypoint_list: List of waypoints before change
    """

    from rafcon.mvc.mygaphas.items.connection import TransitionView
    assert isinstance(transition_v, TransitionView)

    transition_m = transition_v.model
    transition_meta_gaphas = transition_m.meta['gui']['editor_gaphas']
    waypoint_list = get_relative_positions_of_waypoints(transition_v)
    if waypoint_list != last_waypoint_list:
        transition_meta_gaphas['waypoints'] = waypoint_list
        graphical_editor_view.emit('meta_data_changed', transition_m, "Move waypoint", True)


def update_meta_data_for_port(graphical_editor_view, item, handle):
    """This method updates the meta data of the states ports if they changed.

    :param graphical_editor_view: Graphical Editor the change occurred in
    :param item: State the port was moved in
    :param handle: Handle of moved port or None if all ports are to be updated
    """
    from rafcon.mvc.mygaphas.items.ports import IncomeView, OutcomeView, InputPortView, OutputPortView, \
        ScopedVariablePortView
    for port in item.get_all_ports():
        if not handle or handle is port.handle:
            if isinstance(port, IncomeView):
                port_m = item.model
            elif isinstance(port, (OutcomeView, InputPortView, OutputPortView, ScopedVariablePortView)):
                port_m = port.model
            else:
                continue

            port_meta = port_m.meta['gui']['editor_gaphas']
            if isinstance(port, IncomeView):
                port_meta = port_meta['income']

            rel_pos = (port.handle.pos.x.value, port.handle.pos.y.value)
            if rel_pos != port_meta['rel_pos']:
                port_meta['rel_pos'] = rel_pos
                if handle:
                    if isinstance(port, IncomeView):
                        graphical_editor_view.emit('meta_data_changed', port_m, "income_position", True)
                    else:
                        graphical_editor_view.emit('meta_data_changed', port_m, "position", True)

            if handle:  # If we were supposed to update the meta data of a specific port, we can stop here
                break


def update_meta_data_for_name_view(graphical_editor_view, name_v, publish=True):
    """This method updates the meta data of a name view.

    :param graphical_editor_view: Graphical Editor view the change occurred in
    :param name_v: The name view which has been changed/moved
    :param publish: Whether to publish the changes of the meta data
    """
    from gaphas.item import NW

    rel_pos = calc_rel_pos_to_parent(graphical_editor_view.editor.canvas, name_v, name_v.handles()[NW])

    state_v = graphical_editor_view.editor.canvas.get_parent(name_v)
    meta_gaphas = state_v.model.meta['gui']['editor_gaphas']['name']
    meta_gaphas['size'] = (name_v.width, name_v.height)
    meta_gaphas['rel_pos'] = rel_pos

    if publish:
        graphical_editor_view.emit('meta_data_changed', state_v.model, "name_size", False)


def update_meta_data_for_state_view(graphical_editor_view, state_v, affects_children=False, publish=True):
    """This method updates the meta data of a state view

    :param graphical_editor_view: Graphical Editor view the change occurred in
    :param state_v: The state view which has been changed/moved
    :param affects_children: Whether the children of the state view have been resized or not
    :param publish: Whether to publish the changes of the meta data
    """
    from gaphas.item import NW

    # Update all port meta data to match with new position and size of parent
    update_meta_data_for_port(graphical_editor_view, state_v, None)

    if affects_children:
        update_meta_data_for_name_view(graphical_editor_view, state_v.name_view, publish=False)
        for transition_v in state_v.get_transitions():
            update_meta_data_for_transition_waypoints(graphical_editor_view, transition_v, None)
        for child_state_v in state_v.child_state_views():
            update_meta_data_for_state_view(graphical_editor_view, child_state_v, True, publish=False)

    rel_pos = calc_rel_pos_to_parent(graphical_editor_view.editor.canvas, state_v, state_v.handles()[NW])

    meta_gaphas = state_v.model.meta['gui']['editor_gaphas']
    meta_opengl = state_v.model.meta['gui']['editor_opengl']
    meta_gaphas['size'] = (state_v.width, state_v.height)
    meta_gaphas['rel_pos'] = rel_pos
    meta_opengl['size'] = (state_v.width, state_v.height)
    meta_opengl['rel_pos'] = (rel_pos[0], -rel_pos[1])

    if publish:
        graphical_editor_view.emit('meta_data_changed', state_v.model, "size", affects_children)
