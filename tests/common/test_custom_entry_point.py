import os
# core elements
from rafcon.core.execution.execution_engine import ExecutionEngine
from rafcon.core.states.execution_state import ExecutionState
from rafcon.core.states.hierarchy_state import HierarchyState

# singleton elements
import rafcon.core.singleton

# test environment elements
import testing_utils
import pytest


def test_custom_entry_point(caplog):
    testing_utils.initialize_environment()

    start_state_id = "RWUZOP/ZDWBKU/HADSLI"
    sm = rafcon.core.singleton.state_machine_execution_engine.execute_state_machine_from_path(
        path=testing_utils.get_test_sm_path(os.path.join("unit_test_state_machines", "test_custom_entry_point")),
        start_state_path=start_state_id)
    rafcon.core.singleton.state_machine_manager.remove_state_machine(sm.state_machine_id)
    try:
        assert not rafcon.core.singleton.global_variable_manager.variable_exist("start_id21")
    finally:
        testing_utils.shutdown_environment(caplog=caplog)


if __name__ == '__main__':
    test_custom_entry_point(None)
    # pytest.main([__file__])
