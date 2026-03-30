"""looplab debug logging setup."""

import logging

from looplab.debug_log import setup_looplab_logging


def test_setup_looplab_logging_levels():
    setup_looplab_logging(0)
    assert logging.getLogger("looplab").level == logging.WARNING
    setup_looplab_logging(1)
    assert logging.getLogger("looplab").level == logging.INFO
    setup_looplab_logging(2)
    assert logging.getLogger("looplab").level == logging.DEBUG
