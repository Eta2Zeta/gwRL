"""Source-validator and record-copy optimizations compose without rule changes."""
from unittest.mock import patch

from studies.campaign.backends.device_state import DeviceStateContext
import tests.test_campaign_parallel_editor_transactions as original


class ParallelContainerTransactionTests(original.ParallelEditorTransactionTests):
    def setup(self,module,helper,*args):
        def context(native,device):
            return DeviceStateContext(native,device,editor_implementation="parallel",container_implementation="parallel")
        with patch.object(module,"DeviceStateContext",side_effect=context):return helper.setup(*args)
