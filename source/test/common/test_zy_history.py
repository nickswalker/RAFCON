import logging
import gtk
import threading
import time
import signal


# gui elements
from rafcon.gui.config import global_gui_config
import rafcon.gui.singleton
from rafcon.gui.controllers.main_window import MainWindowController
from rafcon.gui.views.main_window import MainWindowView

# core elements
import rafcon.core.singleton
from rafcon.core.config import global_config
from rafcon.core.state_machine import StateMachine
from rafcon.core.states.execution_state import ExecutionState
from rafcon.core.states.container_state import ContainerState
from rafcon.core.states.hierarchy_state import HierarchyState
from rafcon.core.states.preemptive_concurrency_state import PreemptiveConcurrencyState
from rafcon.core.states.barrier_concurrency_state import BarrierConcurrencyState
from rafcon.core.storage import storage

# general tool elements
from rafcon.utils import log

# test environment elements
import testing_utils
from testing_utils import test_multithreading_lock, call_gui_callback, get_unique_temp_path
from test_z_gui_state_type_change import store_state_elements, check_state_elements, \
     check_list_ES, check_list_HS, check_list_BCS, check_list_PCS, \
     check_list_root_ES, check_list_root_HS, check_list_root_BCS, check_list_root_PCS, \
     get_state_editor_ctrl_and_store_id_dict, check_elements_ignores
from test_z_gui_states_editor_widget import check_state_editor_models
import pytest

NO_SAVE = False
TEST_PATH = get_unique_temp_path()

with_prints = False


def on_save_activate(state_machine_m, logger):
    if state_machine_m is None or NO_SAVE:
        return
    save_path = state_machine_m.state_machine.file_system_path
    if save_path is None:
        return

    logger.debug("Saving state machine to {0}".format(save_path))
    storage.save_state_machine_to_path(state_machine_m.state_machine,
                                      state_machine_m.state_machine.file_system_path, delete_old_state_machine=True)

    state_machine_m.root_state.store_meta_data()
    logger.debug("Successfully saved graphics meta data.")


def save_state_machine(sm_model, path, logger, with_gui=False, menubar_ctrl=None):
    print "in Removal: \n", storage._paths_to_remove_before_sm_save.values()

    def print_states(state):
        if isinstance(state, ContainerState):
            for state_id, child_state in state.states.iteritems():
                print child_state.get_path()
                print_states(child_state)
    print_states(sm_model.state_machine.root_state)

    print "do SAVING OF STATEMACHINE"
    if with_gui:
        sm_model.state_machine.file_system_path = path
        print "by Menubar_ctrl"
        call_gui_callback(menubar_ctrl.on_save_activate, None)
    else:
        sm_model.state_machine.file_system_path = path
        print "by Function"
        on_save_activate(sm_model, logger)

    from test_z_storage import check_that_all_files_are_there

    check_that_all_files_are_there(sm_model, path, False, True)


def save_and_quit(sm_model, path, menubar_ctrl, with_gui):
    if with_gui:
        sm_model.state_machine.file_system_path = path
        call_gui_callback(menubar_ctrl.prepare_destruction)


def create_models(*args, **kargs):

    global_gui_config.set_config_value('HISTORY_ENABLED', True)
    logger = log.get_logger(__name__)
    logger.setLevel(logging.DEBUG)
    for handler in logging.getLogger('gtkmvc').handlers:
        logging.getLogger('gtkmvc').removeHandler(handler)

    state1 = ExecutionState('State1', state_id='STATE1')
    output_state1 = state1.add_output_data_port("output", "int")
    input_state1 = state1.add_input_data_port("input", "str", "zero")
    state2 = ExecutionState('State2', state_id='STATE2')
    input_par_state2 = state2.add_input_data_port("par", "int", 0)
    output_res_state2 = state2.add_output_data_port("res", "int")
    state4 = HierarchyState(name='Nested', state_id='NESTED')
    state4.add_outcome('GoGo')
    output_state4 = state4.add_output_data_port("out", "int")
    state5 = ExecutionState('Nested2', state_id='NESTED2')
    state5.add_outcome('HereWeGo')
    input_state5 = state5.add_input_data_port("in", "int", 0)
    state3 = HierarchyState(name='State3', state_id='STATE3')
    input_state3 = state3.add_input_data_port("input", "int", 0)
    output_state3 = state3.add_output_data_port("output", "int")
    state3.add_state(state4)
    state3.add_state(state5)
    state3.set_start_state(state4)
    state3.add_scoped_variable("share", "int", 3)
    state3.add_transition(state4.state_id, 0, state5.state_id, None)
    state3.add_transition(state5.state_id, 0, state3.state_id, 0)
    state3.add_data_flow(state4.state_id, output_state4, state5.state_id, input_state5)
    state3.add_outcome('Branch1')
    state3.add_outcome('Branch2')

    ctr_state = HierarchyState(name="Container", state_id='CONT2')
    ctr_state.add_state(state1)
    ctr_state.add_state(state2)
    ctr_state.add_state(state3)
    input_ctr_state = ctr_state.add_input_data_port("ctr_in", "str", "zero")
    output_ctr_state = ctr_state.add_output_data_port("ctr_out", "int")
    ctr_state.set_start_state(state1)
    ctr_state.add_transition(state1.state_id, 0, state2.state_id, None)
    ctr_state.add_transition(state2.state_id, 0, state3.state_id, None)
    ctr_state.add_transition(state3.state_id, 0, ctr_state.state_id, 0)
    ctr_state.add_data_flow(state1.state_id, output_state1, state2.state_id, input_par_state2)
    ctr_state.add_data_flow(state2.state_id, output_res_state2, state3.state_id, input_state3)
    ctr_state.add_data_flow(ctr_state.state_id, input_ctr_state, state1.state_id, input_state1)
    ctr_state.add_data_flow(state3.state_id, output_state3, ctr_state.state_id, output_ctr_state)
    ctr_state.name = "Container"

    ctr_state.add_input_data_port("input", "str", "default_value1")
    ctr_state.add_input_data_port("pos_x", "str", "default_value2")
    ctr_state.add_input_data_port("pos_y", "str", "default_value3")

    ctr_state.add_output_data_port("output", "str", "default_value1")
    ctr_state.add_output_data_port("result", "str", "default_value2")

    scoped_variable1_ctr_state = ctr_state.add_scoped_variable("scoped", "str", "default_value1")
    scoped_variable3_ctr_state = ctr_state.add_scoped_variable("ctr", "int", 42)

    ctr_state.add_data_flow(ctr_state.state_id, input_ctr_state, ctr_state.state_id, scoped_variable1_ctr_state)
    ctr_state.add_data_flow(state1.state_id, output_state1, ctr_state.state_id, scoped_variable3_ctr_state)

    state_dict = {'Container': ctr_state, 'State1': state1, 'State2': state2, 'State3': state3, 'Nested': state4,
                  'Nested2': state5}
    sm = StateMachine(ctr_state)
    rafcon.core.singleton.state_machine_manager.add_state_machine(sm)
    rafcon.gui.singleton.state_machine_manager_model.selected_state_machine_id = sm.state_machine_id

    sm_m = rafcon.gui.singleton.state_machine_manager_model.state_machines[sm.state_machine_id]
    sm_m.history.fake = False
    print "with_prints is: ", sm_m.history.with_prints
    sm_m.history.with_prints = False
    # return ctr_state, sm_m, state_dict
    return logger, sm_m, state_dict


def get_state_model_by_path(state_model, path):
    path_elems = path.split('/')
    path_elems.pop(0)
    current_state_model = state_model
    for element in path_elems:
        current_state_model = current_state_model.states[element]
    return current_state_model


def test_add_remove_history(caplog):
    ##################
    # Root_state elements

    # add state
    # - change state

    # remove state

    # add outcome
    # - change outcome

    # remove outcome

    # add transition
    # - change transition

    # remove transition

    # add input_data_port
    # - change input_data_port

    # remove input_data_port

    # add output_data_port
    # - change output_data_port

    # remove output_data_port

    # add scoped_variable
    # - change scoped_variable

    # remove scoped_variable

    # add data_flow
    # - change data_flow

    # remove data_flow

    # create testbed
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_model, state_dict] = create_models()

    state_machine_path = TEST_PATH + '_test_add_remove'
    save_state_machine(sm_model, state_machine_path + '_before', logger, with_gui=False, menubar_ctrl=None)

    sm_history = sm_model.history

    state1 = HierarchyState('state1', state_id='STATE1')
    state2 = ExecutionState('state2', state_id='STATE2')

    state_dict['Nested'].add_state(state1)
    state_dict['Nested'].add_state(state2)
    sm_history.modifications.reset()
    state_dict['state1'] = state1
    state_dict['state2'] = state2

    state_path_dict = {}
    for key in state_dict.keys():
        state_path_dict[key] = state_dict[key].get_path()

    def do_check_for_state(state_name):

        from test_models import check_state_for_all_models

        def check_models_for_state_with_name(state_name, state_path_dict, sm_model):
            state_m = sm_model.get_state_model_by_path(state_path_dict[state_name])
            state = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])
            check_state_for_all_models(state, state_m)

        #############
        # add outcome
        # print "\n\n###########1", state_dict[state_name].state_id, state_dict[state_name].input_data_ports.keys()
        outcome_super = sm_model.state_machine.get_state_by_path(state_path_dict[state_name]).add_outcome('super')
        assert len(sm_history.modifications.single_trail_history()) == 2
        # print "\n\n###########2", state_dict[state_name].state_id, state_dict[state_name].input_data_ports.keys()
        sm_history.undo()
        # print "\n\n###########3", state_dict[state_name].state_id, state_dict[state_name].input_data_ports.keys()
        sm_history.redo()
        # print "\n\n###########4", state_dict[state_name].state_id, state_dict[state_name].input_data_ports.keys()

        ################
        # remove outcome
        # def print_all(state_m):
        #     # state = state_m.state
        #     # print state_m
        #     print state_m.state.name  # , state_m.state.get_path()
        #     if isinstance(state_m.state, ContainerState):
        #         for state_m in state_m.states:
        #             print_all(state_m)

        print sm_model, "\n", sm_model.root_state
        save_state_machine(sm_model, state_machine_path + '_before', logger, with_gui=False, menubar_ctrl=None)
        # new outcome should be the third one
        sm_model.state_machine.get_state_by_path(state_path_dict[state_name]).remove_outcome(outcome_super)
        assert len(sm_history.modifications.single_trail_history()) == 3
        save_state_machine(sm_model, state_machine_path + '_after', logger, with_gui=False, menubar_ctrl=None)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.undo()
        save_state_machine(sm_model, state_machine_path + '_undo', logger, with_gui=False, menubar_ctrl=None)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        save_state_machine(sm_model, state_machine_path + '_redo', logger, with_gui=False, menubar_ctrl=None)

        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        state4 = ExecutionState('State4', state_id='STATE4')
        state5 = ExecutionState('State5', state_id='STATE5')

        #############
        # add state
        print "xyz", state_dict[state_name].states.keys(), state_name
        print "xyz", sm_model.state_machine.get_state_by_path(state_path_dict[state_name]).states.keys(), state_name
        sm_model.state_machine.get_state_by_path(state_path_dict[state_name]).add_state(state4)
        state_path_dict['state4'] = state4.get_path()
        print sm_model.state_machine.get_state_by_path(state_path_dict['state4']).get_path()
        assert len(sm_history.modifications.single_trail_history()) == 4
        sm_model.state_machine.get_state_by_path(state_path_dict[state_name]).add_state(state5)
        state_path_dict['state5'] = state5.get_path()
        print sm_model.state_machine.get_state_by_path(state_path_dict['state5']).get_path()
        assert len(sm_history.modifications.single_trail_history()) == 5
        print state_dict[state_name].states
        # store_state_machine(sm_model, test_history_path1)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        # store_state_machine(sm_model, test_history_path2)

        # resolve reference
        print state4.get_path()
        print "\n\n\n"
        print sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        print sm_model.state_machine.get_state_by_path(state_path_dict['Nested']).states
        print "\n\n\n"
        print sm_model.state_machine.get_state_by_path(state4.get_path()).get_path(), "\n", state4.get_path()
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state5 = sm_model.state_machine.get_state_by_path(state_path_dict['state5'])
        state_dict[state_name] = sm_model.get_state_model_by_path(state_dict[state_name].get_path()).state

        outcome_state4 = state4.add_outcome('UsedHere')
        assert len(sm_history.modifications.single_trail_history()) == 6
        outcome_state5 = state5.add_outcome('UsedHere')
        assert len(sm_history.modifications.single_trail_history()) == 7

        ################
        # add transition from_state_id, from_outcome, to_state_id=None, to_outcome=None, transition_id
        new_transition_id1 = state_dict[state_name].add_transition(from_state_id=state4.state_id, from_outcome=outcome_state4,
                                                                   to_state_id=state5.state_id, to_outcome=None)
        state_m = sm_model.get_state_model_by_path(state_path_dict[state_name])
        state = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])
        check_state_for_all_models(state, state_m)
        assert len(sm_history.modifications.single_trail_history()) == 8
        state_dict[state_name].add_transition(from_state_id=state5.state_id, from_outcome=outcome_state5,
                                              to_state_id=state.state_id, to_outcome=-1)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_history.modifications.single_trail_history()) == 9
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state5 = sm_model.state_machine.get_state_by_path(state_path_dict['state5'])
        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        ###################
        # remove transition
        state_dict[state_name].remove_transition(new_transition_id1)  # new outcome should be the third one
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_model.history.modifications.single_trail_history()) == 10
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state5 = sm_model.state_machine.get_state_by_path(state_path_dict['state5'])
        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        #############
        # remove state
        state_dict[state_name].remove_state(state5.state_id)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_history.modifications.single_trail_history()) == 11
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        #############
        # add input_data_port
        input_state4 = state4.add_input_data_port("input", "str", "zero")
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_history.modifications.single_trail_history()) == 12
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        #############
        # remove input_data_port
        state4.remove_input_data_port(input_state4)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_history.modifications.single_trail_history()) == 13
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        #############
        # add output_data_port
        output_state4 = state4.add_output_data_port("output_"+state4.state_id, "int")
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_history.modifications.single_trail_history()) == 14
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        #############
        # remove output_data_port
        state4.remove_output_data_port(output_state4)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_history.modifications.single_trail_history()) == 15
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        # prepare again state4
        output_state4 = state4.add_output_data_port("output", "int")
        input_state4 = state4.add_input_data_port("input_new", "str", "zero")
        assert len(sm_history.modifications.single_trail_history()) == 17
        output_state4 = state4.add_output_data_port("output_new", "int")
        assert len(sm_history.modifications.single_trail_history()) == 18

        state5 = ExecutionState('State5', 'STATE5')
        state_dict[state_name].add_state(state5)
        print state_path_dict['state5'] + "\n" + state5.get_path()
        assert state_path_dict['state5'] == state5.get_path()
        assert len(sm_history.modifications.single_trail_history()) == 19
        input_par_state5 = state5.add_input_data_port("par", "int", 0)
        assert len(sm_history.modifications.single_trail_history()) == 20
        output_res_state5 = state5.add_output_data_port("res", "int")
        assert len(sm_history.modifications.single_trail_history()) == 21


        #####################
        # add scoped_variable
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        scoped_buffer_nested = state_dict[state_name].add_scoped_variable("buffer", "int")
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_history.modifications.single_trail_history()) == 22
        sm_history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.state_machine.get_state_by_path(state_path_dict['state4'])
        state5 = sm_model.state_machine.get_state_by_path(state_path_dict['state5'])
        state_dict[state_name] = sm_model.state_machine.get_state_by_path(state_path_dict[state_name])

        #####################
        # remove scoped_variable
        state_dict[state_name].remove_scoped_variable(scoped_buffer_nested)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_model.history.modifications.single_trail_history()) == 23
        sm_model.history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_model.history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.get_state_model_by_path(state4.get_path()).state
        state5 = sm_model.get_state_model_by_path(state5.get_path()).state
        state_dict[state_name] = sm_model.get_state_model_by_path(state_dict[state_name].get_path()).state

        #############
        # add data_flow
        new_df_id = state_dict[state_name].add_data_flow(from_state_id=state4.state_id, from_data_port_id=output_state4,
                                                         to_state_id=state5.state_id, to_data_port_id=input_par_state5)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_model.history.modifications.single_trail_history()) == 24
        sm_model.history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_model.history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

        # resolve reference
        state4 = sm_model.get_state_model_by_path(state4.get_path()).state
        state5 = sm_model.get_state_model_by_path(state5.get_path()).state
        state_dict[state_name] = sm_model.get_state_model_by_path(state_dict[state_name].get_path()).state

        ################
        # remove data_flow
        state_dict[state_name].remove_data_flow(new_df_id)
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        assert len(sm_model.history.modifications.single_trail_history()) == 25
        sm_model.history.undo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)
        sm_model.history.redo()
        check_models_for_state_with_name(state_name, state_path_dict, sm_model)

    # state_check_dict1 = print_all_states_with_path_and_name(state_dict['Container'])
    # do_check_for_state(state_dict, state_name='state1')
    # do_check_for_state(state_dict, state_name='state2')
    do_check_for_state(state_name='Nested')
    sm_model.history.modifications.reset()
    save_state_machine(sm_model, TEST_PATH + "_add_remove_child_hierarchical_state", logger, with_gui=False)
    # assert check_if_all_states_there(state_dict['Container'], state_check_dict1)
    # state_check_dict2 = print_all_states_with_path_and_name(state_dict['Container'])
    do_check_for_state(state_name='Container')
    save_state_machine(sm_model, TEST_PATH + "_add_remove_root_state", logger, with_gui=False)
    # assert check_if_all_states_there(state_dict['Container'], state_check_dict1)
    # assert check_if_all_states_there(state_dict['Container'], state_check_dict2)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


def test_state_property_modifications_history(caplog):
    ##################
    # state properties
    # TODO LibraryState test for properties like mentioned in the notification-test but also general for add and remove

    # change name

    # change parent

    # change states

    # change outcomes

    # change transitions

    # change input_data_ports

    # change output_data_ports

    # change scoped_variables

    # change data_flows

    # change script

    # change script_text

    # change description

    # change active

    # set_start_state

    # change start_state_id

    # change child_execution

    # create testbed
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_model, state_dict] = create_models()

    state1 = ExecutionState('State1')
    input_state1 = state1.add_input_data_port("input", "str", "zero")
    output_state1 = state1.add_output_data_port("output", "int")
    output_count_state1 = state1.add_output_data_port("count", "int")

    state2 = ExecutionState('State2')
    input_par_state2 = state2.add_input_data_port("par", "int", 0)
    input_number_state2 = state2.add_input_data_port("number", "int", 5)
    output_res_state2 = state2.add_output_data_port("res", "int")

    nested_state_path = state_dict['Nested'].get_path()
    state_dict['Nested'].add_state(state1)
    assert len(sm_model.history.modifications.single_trail_history()) == 2
    state_dict['Nested'].add_state(state2)
    assert len(sm_model.history.modifications.single_trail_history()) == 3
    output_res_nested = state_dict['Nested'].add_output_data_port("res", "int")
    assert len(sm_model.history.modifications.single_trail_history()) == 4

    oc_again_state1 = state1.add_outcome("again")
    assert len(sm_model.history.modifications.single_trail_history()) == 5
    oc_counted_state1 = state1.add_outcome("counted")
    assert len(sm_model.history.modifications.single_trail_history()) == 6

    oc_done_state2 = state2.add_outcome("done")
    oc_best_state2 = state2.add_outcome("best")
    oc_full_state2 = state2.add_outcome("full")
    assert len(sm_model.history.modifications.single_trail_history()) == 9

    oc_great_nested = state_dict['Nested'].add_outcome("great")
    assert len(sm_model.history.modifications.single_trail_history()) == 10

    #######################################
    ######## Properties of State ##########

    # name(self, name)
    state_dict['Nested'].name = 'nested'
    sm_model.history.undo()
    sm_model.history.redo()

    # parent(self, parent) State
    # state_dict['Nested'].parent = state_dict['State3']
    # sm_model.history.undo()
    # sm_model.history.redo()

    # input_data_ports(self, input_data_ports) None or dict
    state_dict['Nested'].input_data_ports = {}
    sm_model.history.undo()
    sm_model.history.redo()

    # output_data_ports(self, output_data_ports) None or dict
    state_dict['Nested'].output_data_ports = {}
    sm_model.history.undo()
    sm_model.history.redo()

    # outcomes(self, outcomes) None or dict
    state_dict['Nested'].outcomes = state_dict['Nested'].outcomes
    sm_model.history.undo()
    sm_model.history.redo()
    state_dict['Nested'].outcomes = {}
    sm_model.history.undo()
    sm_model.history.redo()

    script_text = '\ndef execute(self, inputs, outputs, gvm):\n\tself.logger.debug("Hello World")\n\treturn 0\n'
    script_text1 = '\ndef execute(self, inputs, outputs, gvm):\n\tself.logger.debug("Hello NERD")\n\treturn 0\n'

    # script(self, script) Script -> no script setter any more only script_text !!!
    state_dict['Nested'].script_text = script_text
    sm_model.history.undo()
    sm_model.history.redo()

    # script_text(self, script_text)
    state_dict['Nested'].script_text = script_text1
    sm_model.history.undo()
    sm_model.history.redo()

    # description(self, description) str
    state_dict['Nested'].description = "awesome"
    sm_model.history.undo()
    sm_model.history.redo()

    # # active(self, active) bool
    # state_dict['Nested'].active = True
    # sm_model.history.undo()
    # sm_model.history.redo()
    #
    # # child_execution(self, child_execution) bool
    # state_dict['Nested'].child_execution = True
    # sm_model.history.undo()
    # sm_model.history.redo()

    ############################################
    ###### Properties of ContainerState ########

    # set_start_state(self, state) State or state_id
    state_dict['Nested'] = sm_model.state_machine.get_state_by_path(nested_state_path)
    state1_m = sm_model.get_state_model_by_path(state1.get_path())
    state_dict['Nested'].set_start_state(state1_m.state.state_id)
    sm_model.history.undo()
    sm_model.history.redo()
    # set_start_state(self, start_state)
    state2_m = sm_model.get_state_model_by_path(state2.get_path())
    state_dict['Nested'].set_start_state(state2_m.state)
    sm_model.history.undo()
    sm_model.history.redo()

    # transitions(self, transitions) None or dict
    state_dict['Nested'].transitions = {}
    sm_model.history.undo()
    sm_model.history.redo()

    # data_flows(self, data_flows) None or dict
    state_dict['Nested'].data_flows = {}
    sm_model.history.undo()
    sm_model.history.redo()

    # scoped_variables(self, scoped_variables) None or dict
    state_dict['Nested'].scoped_variables = {}
    sm_model.history.undo()
    sm_model.history.redo()

    # states(self, states) None or dict
    state_dict['Nested'].states = {}
    assert sm_model.history.modifications.single_trail_history()[-1].before_overview['method_name'][-1] == 'states'
    sm_model.history.undo()
    sm_model.history.redo()

    save_state_machine(sm_model, TEST_PATH + "_state_properties", logger, with_gui=False)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


def test_outcome_property_modifications_history(caplog):
    ##################
    # outcome properties

    # change name

    # create testbed
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_model, state_dict] = create_models()

    def do_check_for_state(state_dict, state_name='Nested'):
        ####################################################
        # modify outcome and generate in previous a observer
        for outcome_id, outcome in state_dict['Nested2'].outcomes.iteritems():
            if not outcome_id < 0:
                outcome.name = "new_name_" + str(outcome_id)
                sm_model.history.undo()
                sm_model.history.redo()
                # resolve reference
                state_dict['Nested2'] = sm_model.get_state_model_by_path(state_dict['Nested2'].get_path()).state

        ##########################
        # check for ContainerState -> should be unnecessary
        state_model = sm_model.get_state_model_by_path(state_dict['Nested'].get_path())

        ####################################################
        # modify outcome
        for outcome_id, outcome in state_dict['Nested'].outcomes.iteritems():
            outcome.name = "new_name_" + str(outcome_id)
            sm_model.history.undo()
            sm_model.history.redo()
            # resolve reference
            state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

        # outcome_id(self, outcome_id) -> no data_fow_id setter anymore
        # state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state
        # state_dict['Nested'].outcomes.values()[0].outcome_id += 10
        # sm_model.history.undo()
        # sm_model.history.redo()

    # do_check_for_state(state_dict, history_ctrl, state_name='Nested')
    do_check_for_state(state_dict, state_name='Container')
    save_state_machine(sm_model, TEST_PATH + "_outcome_properties", logger, with_gui=False)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


def wait_for_states_editor(main_window_controller, tab_key, max_time=5.0):
    assert tab_key in main_window_controller.get_controller('states_editor_ctrl').tabs
    time_waited = 0.0
    state_editor_ctrl = None
    while state_editor_ctrl is None:
        state_editor_ctrl = main_window_controller.get_controller('states_editor_ctrl').tabs[tab_key]['controller']
        time.sleep(0.1)
        time_waited += 0.1
        assert time_waited < max_time

    return state_editor_ctrl, time_waited


def test_transition_property_modifications_history(caplog):
    ##################
    # transition properties

    # change modify_origin

    # change from_outcome

    # change to_state

    # change to_outcome

    # modify_transition_from_state

    # modify_transition_from_outcome

    # modify_transition_to_outcome

    # modify_transition_to_state

    # create testbed
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_model, state_dict] = create_models()

    state1 = ExecutionState('State1')
    outcome_again_state1 = state1.add_outcome("again")
    state2 = ExecutionState('State2')
    oc_done_state2 = state2.add_outcome("done")
    oc_best_state2 = state2.add_outcome("best")
    state_dict['Nested'].add_state(state1)
    state_dict['Nested'].add_state(state2)
    oc_great_nested = state_dict['Nested'].add_outcome("great")
    outcome_counted_state1 = state1.add_outcome("counted")
    oc_full_state2 = state2.add_outcome("full")
    # assert False

    new_trans_id = state_dict['Nested'].add_transition(from_state_id=state1.state_id, from_outcome=outcome_again_state1,
                                                       to_state_id=state1.state_id, to_outcome=None)

    # modify_origin(self, from_state, from_outcome)
    state_dict['Nested'].transitions[new_trans_id].modify_origin(from_state=state2.state_id,
                                                                 from_outcome=oc_full_state2)
    sm_model.history.undo()
    sm_model.history.redo()

    # from_outcome(self, from_outcome)
    state_dict['Nested'].transitions[new_trans_id].from_outcome = oc_done_state2
    sm_model.history.undo()
    sm_model.history.redo()

    # to_state(self, to_state)
    state_dict['Nested'].transitions[new_trans_id].to_state = state2.state_id
    sm_model.history.undo()
    sm_model.history.redo()

    # to_outcome(self, to_outcome)
    # TODO do an example what does not violate the roles of transitions
    # TODO test the respective function in transition
    # state_dict['Nested'].transitions[new_trans_id].to_outcome = oc_great_nested
    # sm_model.history.undo()
    # sm_model.history.redo()

    # # transition_id(self, transition_id)  -> no transition_id setter anymore
    # state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state
    # state_dict['Nested'].transitions[new_trans_id].transition_id += 1
    # sm_model.history.undo()
    # sm_model.history.redo()

    # reset observer and testbed
    state_dict['Nested'].remove_transition(new_trans_id)
    new_df_id = state_dict['Nested'].add_transition(from_state_id=state1.state_id,
                                                    from_outcome=outcome_again_state1,
                                                    to_state_id=state1.state_id,
                                                    to_outcome=None)
    sm_model.history.undo()
    sm_model.history.redo()

    ##### modify from parent state #######
    # modify_transition_from_state(self, transition_id, from_state, from_outcome)
    # state_dict['Nested'].modify_transition_from_state(new_df_id, from_state=state2.state_id,
    #                                                   from_outcome=oc_full_state2)
    state_dict['Nested'].transitions[new_df_id].modify_origin(state2.state_id, oc_full_state2)
    sm_model.history.undo()
    sm_model.history.redo()

    # modify_transition_from_outcome(self, transition_id, from_outcome)
    # state_dict['Nested'].modify_transition_from_outcome(new_df_id, from_outcome=oc_done_state2)
    state_dict['Nested'].transitions[new_df_id].from_outcome = oc_done_state2
    sm_model.history.undo()
    sm_model.history.redo()

    # TODO test the respective function in transition
    # modify_transition_to_outcome(self, transition_id, to_outcome)
    # Invalid test: to_outcome must be None as transition goes to child state
    # state_dict['Nested'].modify_transition_to_outcome(new_df_id, to_outcome=oc_great_nested)
    # sm_model.history.undo()
    # sm_model.history.redo()

    # modify_transition_to_state(self, transition_id, to_state, to_outcome)
    # state_dict['Nested'].modify_transition_to_state(new_df_id, to_state=state1.state_id)
    state_dict['Nested'].transitions[new_df_id].to_state = state1.state_id
    sm_model.history.undo()
    sm_model.history.redo()
    save_state_machine(sm_model, TEST_PATH + "_transition_properties", logger, with_gui=False)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


def test_input_port_modify_notification(caplog):
    ##################
    # input_data_port properties

    # change name

    # change data_type

    # change default_value

    # change datatype

    # create testbed
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_model, state_dict] = create_models()
    new_input_data_port_id = state_dict['Nested2'].add_input_data_port(name='new_input', data_type='str')
    sm_model.history.undo()
    sm_model.history.redo()

    ################################
    # check for modification of name
    state_dict['Nested2'].input_data_ports[new_input_data_port_id].name = 'changed_new_input_name'
    sm_model.history.undo()
    sm_model.history.redo()

    #####################################
    # check for modification of data_type
    state_dict['Nested2'].input_data_ports[new_input_data_port_id].data_type = 'int'
    sm_model.history.undo()
    sm_model.history.redo()

    #########################################
    # check for modification of default_value
    state_dict['Nested2'].input_data_ports[new_input_data_port_id].default_value = 5
    sm_model.history.undo()
    sm_model.history.redo()

    ###########################################
    # check for modification of change_datatype
    state_dict['Nested2'].input_data_ports[new_input_data_port_id].change_data_type(data_type='str',
                                                                                    default_value='awesome_tool')
    sm_model.history.undo()
    sm_model.history.redo()
    save_state_machine(sm_model, TEST_PATH + "_input_port_properties", logger, with_gui=False)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


def test_output_port_modify_notification(caplog):

    ##################
    # output_data_port properties

    # change name

    # change data_type

    # change default_value

    # change datatype

    # create testbed
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_model, state_dict] = create_models()
    new_output_data_port_id = state_dict['Nested2'].add_output_data_port(name='new_output', data_type='str')

    ################################
    # check for modification of name
    state_dict['Nested2'].output_data_ports[new_output_data_port_id].name = 'changed_new_output_name'
    sm_model.history.undo()
    sm_model.history.redo()

    #####################################
    # check for modification of data_type
    state_dict['Nested2'].output_data_ports[new_output_data_port_id].data_type = 'int'
    sm_model.history.undo()
    sm_model.history.redo()

    #########################################
    # check for modification of default_value
    state_dict['Nested2'].output_data_ports[new_output_data_port_id].default_value = 5
    sm_model.history.undo()
    sm_model.history.redo()

    ###########################################
    # check for modification of change_datatype
    state_dict['Nested2'].output_data_ports[new_output_data_port_id].change_data_type(data_type='str',
                                                                                      default_value='awesome_tool')
    sm_model.history.undo()
    sm_model.history.redo()
    save_state_machine(sm_model, TEST_PATH + "_output_port_properties", logger, with_gui=False)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


def test_scoped_variable_modify_notification(caplog):
    ##################
    # scoped_variable properties

    # change name

    # change data_type

    # change default_value

    # change datatype

    # create testbed
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_model, state_dict] = create_models()
    new_scoped_variable_id = state_dict['Nested'].add_scoped_variable(name='new_output', data_type='str')

    ################################
    # check for modification of name
    # state_dict['Nested'].modify_scoped_variable_name('changed_new_scoped_var_name', new_scoped_variable_id)
    state_dict['Nested'].scoped_variables[new_scoped_variable_id].name = 'changed_new_scoped_var_name'
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    #####################################
    # check for modification of data_type
    state_dict['Nested'].scoped_variables[new_scoped_variable_id].data_type = 'int'
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    #########################################
    # check for modification of default_value
    state_dict['Nested'].scoped_variables[new_scoped_variable_id].default_value = 5
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    ###########################################
    # check for modification of change_datatype
    state_dict['Nested'].scoped_variables[new_scoped_variable_id].change_data_type(data_type='str',
                                                                                   default_value='awesome_tool')
    sm_model.history.undo()
    sm_model.history.redo()
    save_state_machine(sm_model, TEST_PATH + "_scoped_variable_properties", logger, with_gui=False)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


def test_data_flow_property_modifications_history(caplog):
    ##################
    # data_flow properties

    # change modify_origin

    # change from_key

    # change modify_target

    # change to_key

    # modify_transition_from_state

    # modify_transition_from_key

    # modify_transition_to_key

    # modify_transition_to_state

    # create testbed
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_model, state_dict] = create_models()

    state1 = ExecutionState('State1')
    output_state1 = state1.add_output_data_port("output", "int")
    input_state1 = state1.add_input_data_port("input", "str", "zero")
    state2 = ExecutionState('State2')
    input_par_state2 = state2.add_input_data_port("par", "int", 0)
    output_res_state2 = state2.add_output_data_port("res", "int")
    state_dict['Nested'].add_state(state1)
    state_dict['Nested'].add_state(state2)
    output_res_nested = state_dict['Nested'].add_output_data_port("res", "int")
    output_count_state1 = state1.add_output_data_port("count", "int")
    input_number_state2 = state2.add_input_data_port("number", "int", 5)

    new_df_id = state_dict['Nested'].add_data_flow(from_state_id=state2.state_id, from_data_port_id=output_res_state2,
                                                   to_state_id=state_dict['Nested'].state_id,
                                                   to_data_port_id=output_res_nested)

    ##### modify from data_flow #######
    # modify_origin(self, from_state, from_key)
    state_dict['Nested'].data_flows[new_df_id].modify_origin(from_state=state1.state_id, from_key=output_state1)
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    # from_key(self, from_key)
    state_dict['Nested'].data_flows[new_df_id].from_key = output_count_state1
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    # modify_target(self, to_state, to_key)
    state_dict['Nested'].data_flows[new_df_id].modify_target(to_state=state2.state_id, to_key=input_par_state2)
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    # to_key(self, to_key)
    state_dict['Nested'].data_flows[new_df_id].to_key = input_number_state2
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    # data_flow_id(self, data_flow_id) -> no data_fow_id setter anymore

    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state
    new_df_id = state_dict['Nested'].data_flows[new_df_id].data_flow_id  # only if history.redo was not run

    # reset observer and testbed
    state_dict['Nested'].remove_data_flow(new_df_id)
    sm_model.history.undo()
    sm_model.history.redo()
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state
    new_df_id = state_dict['Nested'].add_data_flow(from_state_id=state2.state_id, from_data_port_id=output_res_state2,
                                                   to_state_id=state_dict['Nested'].state_id,
                                                   to_data_port_id=output_res_nested)
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    ##### modify from parent state #######
    # modify_data_flow_from_state(self, data_flow_id, from_state, from_key)
    # state_dict['Nested'].modify_data_flow_from_state(new_df_id, from_state=state1.state_id, from_key=output_state1)
    state_dict['Nested'].data_flows[new_df_id].modify_origin(state1.state_id, output_state1)
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    # modify_data_flow_from_key(self, data_flow_id, from_key)
    # state_dict['Nested'].modify_data_flow_from_key(new_df_id, from_key=output_count_state1)
    state_dict['Nested'].data_flows[new_df_id].from_key = output_count_state1
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    # modify_data_flow_to_state(self, data_flow_id, to_state, to_key)
    # state_dict['Nested'].modify_data_flow_to_state(new_df_id, to_state=state2.state_id, to_key=input_par_state2)
    state_dict['Nested'].data_flows[new_df_id].modify_target(state2.state_id, input_par_state2)
    sm_model.history.undo()
    sm_model.history.redo()
    # resolve reference
    state_dict['Nested'] = sm_model.get_state_model_by_path(state_dict['Nested'].get_path()).state

    # modify_data_flow_to_key(self, data_flow_id, to_key)
    # state_dict['Nested'].modify_data_flow_to_key(new_df_id, to_key=input_number_state2)
    state_dict['Nested'].data_flows[new_df_id].to_key = input_number_state2
    sm_model.history.undo()
    sm_model.history.redo()

    save_state_machine(sm_model, TEST_PATH + "_data_flow_properties", logger, with_gui=False)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


def test_type_modifications_without_gui(caplog):
    import rafcon.core.start
    with_gui = False
    rafcon.core.singleton.state_machine_manager.delete_all_state_machines()
    signal.signal(signal.SIGINT, rafcon.core.start.signal_handler)
    global_config.load()  # load the default config
    global_gui_config.load()  # load the default config
    print "create model"
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_m, state_dict] = create_models()
    print "init libs"
    testing_utils.remove_all_libraries()
    rafcon.core.singleton.library_manager.initialize()
    sm_manager_model = rafcon.gui.singleton.state_machine_manager_model

    # load the meta data for the state machine
    sm_manager_model.get_selected_state_machine_model().root_state.load_meta_data()
    print "start thread"
    trigger_state_type_change_tests(sm_manager_model, None, sm_m, state_dict, with_gui, logger)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


@pytest.mark.parametrize("with_gui", [True])
def test_state_machine_modifications_with_gui(with_gui, caplog):
    testing_utils.start_rafcon()
    print "create model"
    [logger, sm_m, state_dict] = create_models()
    print "init libs"
    testing_utils.remove_all_libraries()
    if testing_utils.sm_manager_model is None:
        testing_utils.sm_manager_model = rafcon.gui.singleton.state_machine_manager_model

    print "initialize MainWindow"
    main_window_view = MainWindowView()
    main_window_controller = MainWindowController(testing_utils.sm_manager_model, main_window_view)
    while gtk.events_pending():
        # Wait for GUI to initialize
        gtk.main_iteration(False)
    print "start thread"
    thread = threading.Thread(target=trigger_state_type_change_tests,
                              args=[testing_utils.sm_manager_model, main_window_controller,
                                    sm_m, state_dict, with_gui, logger])
    thread.start()
    if with_gui:
        gtk.main()
        logger.debug("Gtk main loop exited!")
        test_multithreading_lock.release()

    thread.join()
    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)

# TODO introduce test_add_remove_history with_gui=True to have a more reliable unit-test

@pytest.mark.parametrize("with_gui", [True])
def test_state_type_change_bugs_with_gui(with_gui, caplog):
    print "NEW BUG TEST"
    testing_utils.start_rafcon()
    print "create model"
    global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    [logger, sm_m, state_dict] = create_models()
    print "init libs"
    testing_utils.remove_all_libraries()
    rafcon.core.singleton.library_manager.initialize()

    if testing_utils.sm_manager_model is None:
        testing_utils.sm_manager_model = rafcon.gui.singleton.state_machine_manager_model

    # load the meta data for the state machine
    if with_gui:
        print "initialize MainWindow"
        main_window_view = MainWindowView()
        main_window_controller = MainWindowController(testing_utils.sm_manager_model, main_window_view)
        if with_gui:
            # Wait for GUI to initialize
            while gtk.events_pending():
                gtk.main_iteration(False)
        print "start thread"
        thread = threading.Thread(target=trigger_state_type_change_typical_bug_tests,
                                  args=[testing_utils.sm_manager_model, main_window_controller, sm_m, state_dict,
                                        with_gui, logger])
        thread.start()

        if with_gui:
            gtk.main()
            logger.debug("Gtk main loop exited!")
            test_multithreading_lock.release()

        thread.join()
    else:
        testing_utils.sm_manager_model.get_selected_state_machine_model().root_state.load_meta_data()
        print "start thread"
        trigger_state_type_change_typical_bug_tests(testing_utils.sm_manager_model, None, sm_m, state_dict, with_gui, logger)

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog)


@log.log_exceptions(None, gtk_quit=True)
def trigger_state_type_change_tests(*args):
    with_gui = bool(args[4])
    # if with_gui:
    #     time.sleep(1.0)
    sm_manager_model = args[0]
    main_window_controller = args[1]
    sm_m = args[2]
    state_dict = args[3]
    logger = args[5]

    sleep_time_max = 5  # 0.5

    check_elements_ignores.append("internal_transitions")

    # General Type Change inside of a state machine (NO ROOT STATE) ############
    state_of_type_change = 'State3'
    parent_of_type_change = 'Container'

    # do state_type_change with gui
    # - find state machine id
    my_sm_id = None
    for sm_id, state_machine in sm_manager_model.state_machine_manager.state_machines.iteritems():
        if state_machine is sm_m.state_machine:
            my_sm_id = sm_id
    assert my_sm_id is not None

    sm_model = sm_m  # sm_manager_model.state_machines[my_sm_id]
    sm_model.history.modifications.reset()

    state_parent_m = sm_m.get_state_model_by_path(state_dict[parent_of_type_change].get_path())
    state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements, stored_state_m_elements] = store_state_elements(state_dict[state_of_type_change], state_m)
    print "\n\n %s \n\n" % state_m.state.name
    sm_m.selection.set([state_m])

    # adjust the transition test
    # TODO finish it

    list_store_id_from_state_type_dict = {}
    state_editor_ctrl = None
    state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements, stored_state_m_elements] = store_state_elements(state_dict[state_of_type_change], state_m)

    if with_gui:
        state_machine_path = TEST_PATH + '_state_type_change_with_gui'
        # TODO the next lines should not to be necessary to save the state machine at the end
        menubar_ctrl = main_window_controller.get_controller('menu_bar_controller')
        save_state_machine(sm_model, state_machine_path, logger, with_gui, menubar_ctrl)

        # do state_type_change with gui
        # - get state-editor controller and find right row in combo box
        [state_editor_ctrl, list_store_id_from_state_type_dict] = \
            get_state_editor_ctrl_and_store_id_dict(sm_m, state_m, main_window_controller, sleep_time_max, logger)
    else:
        menubar_ctrl = None
        state_machine_path = TEST_PATH + '_state_type_change_without_gui'
        save_state_machine(sm_model, state_machine_path, logger, bool(with_gui), menubar_ctrl)
        pass
    if with_gui:
        check_state_editor_models(sm_m, state_m, main_window_controller, logger)

    # HS -> BCS
    save_state_machine(sm_model, state_machine_path + '_before1', logger, with_gui, menubar_ctrl)
    # - do state type change
    logger.info("HS -> BCS")
    if with_gui:
        state_type_row_id = list_store_id_from_state_type_dict['BARRIER_CONCURRENCY']
        call_gui_callback(state_editor_ctrl.get_controller('properties_ctrl').view['type_combobox'].set_active, state_type_row_id)
    else:
        state_dict[parent_of_type_change].change_state_type(state_m.state, BarrierConcurrencyState)

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    new_state = sm_model.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_model.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements_after, stored_state_m_elements_after] = store_state_elements(new_state, new_state_m)

    save_state_machine(sm_model, state_machine_path + '_after1', logger, with_gui, menubar_ctrl)

    assert len(sm_model.history.modifications.single_trail_history()) == 2
    logger.info("BCS -> HS (undo)")
    if with_gui:
        call_gui_callback(sm_model.history.undo)
    else:
        sm_model.history.undo()

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    save_state_machine(sm_model, state_machine_path + '_undo1', logger, with_gui, menubar_ctrl)

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_HS, new_state, new_state_m, stored_state_elements, stored_state_m_elements)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    logger.info("HS -> BCS (redo)")
    if with_gui:
        call_gui_callback(sm_model.history.redo)
    else:
        sm_model.history.redo()

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    save_state_machine(sm_model, state_machine_path + '_redo1', logger, with_gui, menubar_ctrl)

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_BCS, new_state, new_state_m, stored_state_elements_after, stored_state_m_elements_after)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    # BCS -> HS
    save_state_machine(sm_model, state_machine_path + '_before2', logger, with_gui, menubar_ctrl)
    sm_model.state_machine.file_system_path = state_machine_path
    logger.info("BCS -> HS 2")
    if with_gui:
        # do state_type_change with gui
        # - get state-editor controller and find right row in combo box
        [state_editor_ctrl, list_store_id_from_state_type_dict] = \
            get_state_editor_ctrl_and_store_id_dict(sm_m, new_state_m, main_window_controller, sleep_time_max, logger)

    # - do state type change
        state_type_row_id = list_store_id_from_state_type_dict['HIERARCHY']
        call_gui_callback(state_editor_ctrl.get_controller('properties_ctrl').view['type_combobox'].set_active, state_type_row_id)
    else:
        state_dict[parent_of_type_change].change_state_type(new_state_m.state, HierarchyState)

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements_after, stored_state_m_elements_after] = store_state_elements(new_state, new_state_m)

    print "\n\n ###### State: %s" % state_dict[state_of_type_change]
    from test_z_storage import check_that_all_files_are_there
    check_that_all_files_are_there(sm_model, state_machine_path + '_before2', False, True)
    check_that_all_files_are_there(sm_model, state_machine_path + '_after2', False, True)

    save_state_machine(sm_model, state_machine_path + '_after2', logger, with_gui, menubar_ctrl)

    assert len(sm_model.history.modifications.single_trail_history()) == 3
    logger.info("HS -> BCS 2 (undo)")
    if with_gui:
        call_gui_callback(sm_model.history.undo)
    else:
        sm_model.history.undo()

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    save_state_machine(sm_model, state_machine_path + '_undo2', logger, with_gui, menubar_ctrl)

    logger.info("BCS -> HS 2 (redo)")
    if with_gui:
        call_gui_callback(sm_model.history.redo)
    else:
        sm_model.history.redo()

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    save_state_machine(sm_model, state_machine_path + '_redo2', logger, with_gui, menubar_ctrl)

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_HS, new_state, new_state_m, stored_state_elements_after, stored_state_m_elements_after)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    # HS -> PCS
    [stored_state_elements, stored_state_m_elements] = store_state_elements(new_state, new_state_m)
    save_state_machine(sm_model, state_machine_path + '_before3', logger, with_gui, menubar_ctrl)
    logger.info("HS -> PCS")
    if with_gui:
        # do state_type_change with gui
        # - get state-editor controller and find right row in combo box
        [state_editor_ctrl, list_store_id_from_state_type_dict] = \
            get_state_editor_ctrl_and_store_id_dict(sm_m, new_state_m, main_window_controller, sleep_time_max, logger)

    # - do state type change
        state_type_row_id = list_store_id_from_state_type_dict['PREEMPTION_CONCURRENCY']
        call_gui_callback(state_editor_ctrl.get_controller('properties_ctrl').view['type_combobox'].set_active, state_type_row_id)
    else:
        state_dict[parent_of_type_change].change_state_type(new_state_m.state, PreemptiveConcurrencyState)

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    new_state = sm_model.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_model.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements_after, stored_state_m_elements_after] = store_state_elements(new_state, new_state_m)

    save_state_machine(sm_model, state_machine_path + '_after3', logger, with_gui, menubar_ctrl)

    assert len(sm_model.history.modifications.single_trail_history()) == 4
    logger.info("PCS -> HS")
    if with_gui:
        call_gui_callback(sm_model.history.undo)
    else:
        sm_model.history.undo()

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    save_state_machine(sm_model, state_machine_path + '_undo3', logger, with_gui, menubar_ctrl)

    new_state = sm_model.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_model.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_HS, new_state, new_state_m, stored_state_elements, stored_state_m_elements)

    logger.info("HS -> PCS")
    if with_gui:
        call_gui_callback(sm_model.history.redo)
    else:
        sm_model.history.redo()

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    save_state_machine(sm_model, state_machine_path + '_redo3', logger, with_gui, menubar_ctrl)

    new_state = sm_model.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_model.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_PCS, new_state, new_state_m, stored_state_elements_after, stored_state_m_elements_after)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    # PCS -> ES
    [stored_state_elements, stored_state_m_elements] = store_state_elements(new_state, new_state_m)
    save_state_machine(sm_model, state_machine_path + '_before4', logger, with_gui, menubar_ctrl)
    logger.info("PCS -> ES")
    if with_gui:
        # do state_type_change with gui
        # - get state-editor controller and find right row in combo box
        [state_editor_ctrl, list_store_id_from_state_type_dict] = \
            get_state_editor_ctrl_and_store_id_dict(sm_m, new_state_m, main_window_controller, sleep_time_max, logger)

    # - do state type change
        state_type_row_id = list_store_id_from_state_type_dict['EXECUTION']
        call_gui_callback(state_editor_ctrl.get_controller('properties_ctrl').view['type_combobox'].set_active, state_type_row_id)
    else:
        state_dict[parent_of_type_change].change_state_type(new_state_m.state, ExecutionState)

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    new_state = sm_model.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_model.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements_after, stored_state_m_elements_after] = store_state_elements(new_state, new_state_m)

    save_state_machine(sm_model, state_machine_path + '_after4', logger, with_gui, menubar_ctrl)

    assert len(sm_model.history.modifications.single_trail_history()) == 5
    logger.info("ES -> PCS")
    if with_gui:
        call_gui_callback(sm_model.history.undo)
    else:
        sm_model.history.undo()

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    save_state_machine(sm_model, state_machine_path + '_undo4', logger, with_gui, menubar_ctrl)

    new_state = sm_model.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_model.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_PCS, new_state, new_state_m, stored_state_elements, stored_state_m_elements)

    logger.info("PCS -> ES")
    if with_gui:
        call_gui_callback(sm_model.history.redo)
    else:
        sm_model.history.redo()

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    state_dict[parent_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[parent_of_type_change].get_path())

    save_state_machine(sm_model, state_machine_path + '_redo4', logger, with_gui, menubar_ctrl)

    new_state = sm_model.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_model.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_ES, new_state, new_state_m, stored_state_elements_after, stored_state_m_elements_after)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    ####### General Type Change as ROOT STATE ############
    state_of_type_change = 'Container'
    state_m = sm_model.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements, stored_state_m_elements] = store_state_elements(state_dict[state_of_type_change], state_m)
    if with_gui:
        check_state_editor_models(sm_m, state_m, main_window_controller, logger)

    # HS -> BCS
    logger.info("HS -> BCS root")
    if with_gui:
        # do state_type_change with gui
        # - do state selection to generate state editor widget
        call_gui_callback(sm_m.selection.set, [state_m])
        call_gui_callback(sm_m.selection.clear)
        call_gui_callback(sm_m.selection.set, [state_m])

        # - get state-editor controller and find right row in combo box
        [state_editor_ctrl, list_store_id_from_state_type_dict] = \
            get_state_editor_ctrl_and_store_id_dict(sm_m, state_m, main_window_controller, sleep_time_max, logger)

    # - do state type change
        state_type_row_id = list_store_id_from_state_type_dict['BARRIER_CONCURRENCY']
        call_gui_callback(state_editor_ctrl.get_controller('properties_ctrl').view['type_combobox'].set_active, state_type_row_id)
    else:
        sm_m.state_machine.change_root_state_type(BarrierConcurrencyState)
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements_after, stored_state_m_elements_after] = store_state_elements(new_state, new_state_m)

    # import time
    # time.sleep(100)

    assert len(sm_model.history.modifications.single_trail_history()) == 6
    logger.info("BCS -> HS root (undo)")
    if with_gui:
        call_gui_callback(sm_model.history.undo)
    else:
        sm_model.history.undo()
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_root_HS, new_state, new_state_m, stored_state_elements, stored_state_m_elements)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    logger.info("HS -> BCS root (redo)")
    if with_gui:
        call_gui_callback(sm_model.history.redo)
    else:
        sm_model.history.redo()
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_root_BCS, new_state, new_state_m,
                         stored_state_elements_after, stored_state_m_elements_after)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    # BCS -> HS
    [stored_state_elements, stored_state_m_elements] = store_state_elements(new_state, new_state_m)
    logger.info("BCS -> HS root 2")
    if with_gui:
        # do state_type_change with gui
        # - do state selection to generate state editor widget
        call_gui_callback(sm_m.selection.set, [new_state_m])
        call_gui_callback(sm_m.selection.clear)
        call_gui_callback(sm_m.selection.set, [new_state_m])

        # - get state-editor controller and find right row in combo box
        [state_editor_ctrl, list_store_id_from_state_type_dict] = \
            get_state_editor_ctrl_and_store_id_dict(sm_m, new_state_m, main_window_controller, sleep_time_max, logger)

    # - do state type change
        state_type_row_id = list_store_id_from_state_type_dict['HIERARCHY']
        call_gui_callback(state_editor_ctrl.get_controller('properties_ctrl').view['type_combobox'].set_active, state_type_row_id)
    else:
        sm_m.state_machine.change_root_state_type(HierarchyState)

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    assert len(sm_model.history.modifications.single_trail_history()) == 7
    logger.info("HS -> BCS root 2 (undo)")
    if with_gui:
        call_gui_callback(sm_model.history.undo)
    else:
        sm_model.history.undo()
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_root_BCS, new_state, new_state_m, stored_state_elements, stored_state_m_elements)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    logger.info("BCS -> HS root 2 (redo)")
    if with_gui:
        call_gui_callback(sm_model.history.redo)
    else:
        sm_model.history.redo()
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_root_HS, new_state, new_state_m,
                         stored_state_elements_after, stored_state_m_elements_after)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    # HS -> PCS
    [stored_state_elements, stored_state_m_elements] = store_state_elements(new_state, new_state_m)
    logger.info("HS -> PCS")
    if with_gui:
        # do state_type_change with gui
        # - do state selection to generate state editor widget
        call_gui_callback(sm_m.selection.set, [new_state_m])
        call_gui_callback(sm_m.selection.clear)
        call_gui_callback(sm_m.selection.set, [new_state_m])

        # - get state-editor controller and find right row in combo box
        [state_editor_ctrl, list_store_id_from_state_type_dict] = \
            get_state_editor_ctrl_and_store_id_dict(sm_m, new_state_m, main_window_controller, sleep_time_max, logger)

    # - do state type change
        state_type_row_id = list_store_id_from_state_type_dict['PREEMPTION_CONCURRENCY']
        call_gui_callback(state_editor_ctrl.get_controller('properties_ctrl').view['type_combobox'].set_active, state_type_row_id)
    else:
        sm_m.state_machine.change_root_state_type(PreemptiveConcurrencyState)
        state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    assert len(sm_model.history.modifications.single_trail_history()) == 8
    logger.info("PCS -> HS")
    if with_gui:
        call_gui_callback(sm_model.history.undo)
    else:
        sm_model.history.undo()
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_root_PCS, new_state, new_state_m, stored_state_elements, stored_state_m_elements)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    logger.info("HS -> PCS")
    if with_gui:
        call_gui_callback(sm_model.history.redo)
    else:
        sm_model.history.redo()
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_root_HS, new_state, new_state_m,
                         stored_state_elements_after, stored_state_m_elements_after)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    # PCS -> ES
    [stored_state_elements, stored_state_m_elements] = store_state_elements(new_state, new_state_m)
    logger.info("PCS -> ES")
    if with_gui:
        # do state_type_change with gui
        # - do state selection to generate state editor widget
        call_gui_callback(sm_m.selection.set, [new_state_m])
        call_gui_callback(sm_m.selection.clear)
        call_gui_callback(sm_m.selection.set, [new_state_m])

        # - get state-editor controller and find right row in combo box
        [state_editor_ctrl, list_store_id_from_state_type_dict] = \
            get_state_editor_ctrl_and_store_id_dict(sm_m, new_state_m, main_window_controller, sleep_time_max, logger)

    # - do state type change
        state_type_row_id = list_store_id_from_state_type_dict['EXECUTION']
        call_gui_callback(state_editor_ctrl.get_controller('properties_ctrl').view['type_combobox'].set_active, state_type_row_id)
    else:
        sm_m.state_machine.change_root_state_type(ExecutionState)

    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements_after, stored_state_m_elements_after] = store_state_elements(new_state, new_state_m)

    assert len(sm_model.history.modifications.single_trail_history()) == 9
    logger.info("ES -> PCS")
    if with_gui:
        call_gui_callback(sm_model.history.undo)
    else:
        sm_model.history.undo()
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    # print "path: ", state_dict[state_of_type_change].get_path(), " state ", state_dict[state_of_type_change]
    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_root_PCS, new_state, new_state_m, stored_state_elements, stored_state_m_elements)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    logger.info("PCS -> ES")
    if with_gui:
        call_gui_callback(sm_model.history.redo)
    else:
        sm_model.history.redo()
    state_dict[state_of_type_change] = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())

    new_state = sm_m.state_machine.get_state_by_path(state_dict[state_of_type_change].get_path())
    new_state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    check_state_elements(check_list_root_ES, new_state, new_state_m,
                         stored_state_elements_after, stored_state_m_elements_after)
    if with_gui:
        check_state_editor_models(sm_m, new_state_m, main_window_controller, logger)

    save_and_quit(sm_model, TEST_PATH + '_state_type_change', menubar_ctrl, with_gui)

    check_elements_ignores.remove("internal_transitions")
    print check_elements_ignores


@log.log_exceptions(None, gtk_quit=True)
def trigger_state_type_change_typical_bug_tests(*args):
    with_gui = bool(args[4])
    sm_manager_model = args[0]
    main_window_controller = args[1]
    sm_m = args[2]
    state_dict = args[3]
    logger = args[5]

    check_elements_ignores.append("internal_transitions")

    # General Type Change inside of a state machine (NO ROOT STATE) ############
    state_of_type_change = 'State3'
    parent_of_type_change = 'Container'

    # do state_type_change with gui
    # - find state machine id
    my_sm_id = None
    for sm_id, state_machine in sm_manager_model.state_machine_manager.state_machines.iteritems():
        if state_machine is sm_m.state_machine:
            my_sm_id = sm_id
    assert my_sm_id is not None

    sm_model = sm_m  # sm_manager_model.state_machines[my_sm_id]
    sm_model.history.modifications.reset()

    state_parent_m = sm_m.get_state_model_by_path(state_dict[parent_of_type_change].get_path())
    state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements, stored_state_m_elements] = store_state_elements(state_dict[state_of_type_change], state_m)
    print "\n\n %s \n\n" % state_m.state.name
    # call_gui_callback(sm_m.selection.set, [state_m])
    sm_m.selection.set([state_m])

    state_m = sm_m.get_state_model_by_path(state_dict[state_of_type_change].get_path())
    [stored_state_elements, stored_state_m_elements] = store_state_elements(state_dict[state_of_type_change], state_m)

    current_sm_length = len(sm_manager_model.state_machines)
    # print "1:", sm_manager_model.state_machines.keys()
    logger.debug('number of sm is : {0}'.format(sm_manager_model.state_machines.keys()))
    root_state = HierarchyState("new root state", state_id="ROOT")
    state_machine = StateMachine(root_state)

    state_machine_path = TEST_PATH + '_state_type_change_bug_tests'
    if with_gui:
        menubar_ctrl = main_window_controller.get_controller('menu_bar_controller')
        # call_gui_callback(menubar_ctrl.on_new_activate, None)
        call_gui_callback(sm_manager_model.state_machine_manager.add_state_machine, state_machine)
        sm_manager_model.state_machine_manager.activate_state_machine_id = state_machine.state_machine_id
    else:
        menubar_ctrl = None
        logger.debug("Creating new state-machine...")
        sm_manager_model.state_machine_manager.add_state_machine(state_machine)
        sm_manager_model.state_machine_manager.activate_state_machine_id = state_machine.state_machine_id

    logger.debug('number of sm is : {0}'.format(sm_manager_model.state_machines.keys()))
    assert len(sm_manager_model.state_machines) == current_sm_length+1
    sm_m = sm_manager_model.state_machines[sm_manager_model.state_machines.keys()[-1]]
    save_state_machine(sm_m, state_machine_path + '_before1', logger, with_gui, menubar_ctrl)
    h_state1 = HierarchyState(state_id='HSTATE1')
    if with_gui:
        call_gui_callback(sm_m.state_machine.root_state.add_state, h_state1)
    else:
        sm_m.state_machine.root_state.add_state(h_state1)
    h_state2 = HierarchyState(state_id='HSTATE2')
    if with_gui:
        call_gui_callback(h_state1.add_state, h_state2)
    else:
        h_state1.add_state(h_state2)
    ex_state1 = ExecutionState(state_id='EXSTATE1')
    if with_gui:
        call_gui_callback(h_state1.add_state, ex_state1)
    else:
        h_state1.add_state(ex_state1)
    ex_state2 = ExecutionState(state_id='EXSTATE2')
    if with_gui:
        call_gui_callback(h_state2.add_state, ex_state2)
    else:
        h_state2.add_state(ex_state2)

    logger.info("DO_TYPE_CHANGE")
    if with_gui:
        call_gui_callback(sm_m.state_machine.root_state.change_state_type, h_state1, ExecutionState)
    else:
        sm_m.state_machine.root_state.change_state_type(h_state1, ExecutionState)

    logger.info("UNDO \n{0}".format(sm_m.history.modifications.single_trail_history()[-1].before_overview))
    if with_gui:
        call_gui_callback(sm_m.history.undo)
    else:
        sm_m.history.undo()
    save_state_machine(sm_m, state_machine_path + '_before1', logger, with_gui, menubar_ctrl)
    logger.info("UNDO finished")
    logger.info("REDO")
    if with_gui:
        call_gui_callback(sm_m.history.redo)
    else:
        sm_m.history.redo()
    logger.info("REDO finished")

    if with_gui:
        menubar_ctrl = main_window_controller.get_controller('menu_bar_controller')
        call_gui_callback(menubar_ctrl.prepare_destruction)

    check_elements_ignores.remove("internal_transitions")
    print check_elements_ignores

if __name__ == '__main__':
    # test_add_remove_history(None)
    # test_state_property_modifications_history(None)
    #
    # test_outcome_property_modifications_history(None)
    # test_input_port_modify_notification(None)
    # test_output_port_modify_notification(None)
    #
    # test_transition_property_modifications_history(None)
    # test_scoped_variable_modify_notification(None)
    # test_data_flow_property_modifications_history(None)
    #
    # test_type_modifications_without_gui(None)
    # test_state_machine_modifications_with_gui(True, None)
    # test_state_type_change_bugs_with_gui(False, None)
    # test_state_type_change_bugs_with_gui(True, None)
    pytest.main(['-s', __file__])