"""Pytest fixtures for ApiCompat.

The real GenLayer SDK is not required here. This file installs a small
stand-in ``genlayer`` module that implements exactly the surface the
contract uses (``gl.Contract``, ``gl.public``, ``gl.message``,
``gl.nondet.exec_prompt`` and ``gl.vm.run_nondet_unsafe``), then loads
``contracts/api_compat.py`` itself -- not a copy of its logic -- so the
tests exercise the deployable file.

The stand-in ``run_nondet_unsafe`` mimics the contract's consensus
shape: it runs the leader, hands the wrapped result to the validator,
and returns the leader result only when the validator accepts. If the
validator rejects, it raises, and no state is written, because the
contract writes state only after that call returns.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

CONTRACT_PATH = Path(__file__).parent.parent / "contracts" / "api_compat.py"


class _Return:
    def __init__(self, calldata):
        self.calldata = calldata


class _UserError(Exception):
    def __init__(self, message=""):
        super().__init__(message)
        self.message = message


class _VMError(Exception):
    def __init__(self, message=""):
        super().__init__(message)
        self.message = message


class _TreeMap(dict):
    def __class_getitem__(cls, item):
        return cls


class _DynArray(list):
    def __class_getitem__(cls, item):
        return cls


class _U32(int):
    pass


class _Address(str):
    pass


class _Public:
    @staticmethod
    def view(func):
        return func

    @staticmethod
    def write(func):
        return func


def _run_nondet_unsafe(leader_fn, validator_fn):
    try:
        leader_result = leader_fn()
    except Exception as exc:
        wrapped = exc
        try:
            accepted = validator_fn(wrapped)
        except Exception:
            accepted = False
        if accepted:
            raise
        raise RuntimeError("validator rejected leader result") from exc
    wrapped = _Return(leader_result)
    if validator_fn(wrapped):
        return leader_result
    raise RuntimeError("validator rejected leader result")


def _load_contract_module():
    stub = types.ModuleType("genlayer")
    gl = types.SimpleNamespace()
    gl.Contract = object
    gl.public = _Public()
    gl.message = types.SimpleNamespace(sender_address="0xOwner")
    gl.nondet = types.SimpleNamespace()
    gl.vm = types.SimpleNamespace(
        Return=_Return,
        UserError=_UserError,
        VMError=_VMError,
        run_nondet_unsafe=_run_nondet_unsafe,
    )
    stub.gl = gl
    stub.TreeMap = _TreeMap
    stub.DynArray = _DynArray
    stub.u32 = _U32
    stub.Address = _Address
    stub.__all__ = ["gl", "TreeMap", "DynArray", "u32", "Address"]

    state = {"queue": [], "last": {"findings": []}}

    def exec_prompt(prompt, response_format=None):
        if state["queue"]:
            response = state["queue"].pop(0)
            state["last"] = response
            return response
        return state["last"]

    gl.nondet.exec_prompt = exec_prompt
    sys.modules["genlayer"] = stub

    spec = importlib.util.spec_from_file_location("api_compat_contract", CONTRACT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, stub, state


_MODULE, _STUB, _STATE = _load_contract_module()


class Env:
    """Small helper to drive a fresh contract instance in each test."""

    def __init__(self, module, stub, state):
        self.module = module
        self.stub = stub
        self.state = state

    def new(self, sender="0xOwner"):
        self.stub.gl.message.sender_address = sender
        self.state["queue"] = []
        self.state["last"] = {"findings": []}
        return self.module.ApiCompat()

    def set_sender(self, sender):
        self.stub.gl.message.sender_address = sender

    def queue_llm(self, *responses):
        self.state["queue"] = list(responses)
        if responses:
            self.state["last"] = responses[-1]


@pytest.fixture
def env():
    return Env(_MODULE, _STUB, _STATE)


@pytest.fixture
def mod(env):
    return env.module
