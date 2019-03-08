from __future__ import print_function
import threading

# test environment elements
from tests import utils as testing_utils
from tests.utils import call_gui_callback


def run_create():
    """ By searching for the WT thread number can been seen, that
    """
    from rafcon.core.states.hierarchy_state import HierarchyState
    from rafcon.core.state_machine import StateMachine
    import rafcon.core.singleton
    import rafcon.gui.singleton

    print("WT_ident: ", threading.currentThread().ident)
    print("CORE_singleton_init_thread_ident: ", rafcon.core.singleton.thread_identifier)
    print("GUI_singleton_init_thread_ident: ", rafcon.gui.singleton.thread_identifier)
    main_window_controller = rafcon.gui.singleton.main_window_controller
    menubar_ctrl = main_window_controller.get_controller('menu_bar_controller')
    call_gui_callback(menubar_ctrl.on_new_activate, None)
    # negative test
    # menubar_ctrl.on_new_activate(None)
    print("\n"*3, "WT generated object", "\n"*3)
    call_gui_callback(rafcon.core.singleton.state_machine_manager.add_state_machine,
                      StateMachine(HierarchyState("new root state")))


def test_thread_observer_creation_list(caplog):
    # The side bars have been hidden in the state_resize test; here we show them again
    testing_utils.run_gui(runtime_config={
                              'LEFT_BAR_HIDDEN': False,
                              'RIGHT_BAR_HIDDEN': False,
                              'CONSOLE_HIDDEN': False,
                          })

    try:
        run_create()
    except:
        raise
    finally:
        testing_utils.close_gui()
        testing_utils.shutdown_environment(caplog=caplog, expected_warnings=0, expected_errors=0)

if __name__ == '__main__':
    test_thread_observer_creation_list(None)
