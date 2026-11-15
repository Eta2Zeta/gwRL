"""Windows process control for the training supervisor.

POSIX supervision starts the trainer in its own session and signals and measures
that process group. Windows has no process groups of that kind, so a job object
holds the trainer and every process it starts. A graceful stop is a Ctrl+Break
console event to the trainer's console process group, which Python delivers as
SIGBREAK; a forced stop terminates the whole job.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import signal

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_VM_READ = 0x0010
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259
_BASIC_ACCOUNTING = 1  # JobObjectBasicAccountingInformation
_PROCESS_ID_LIST = 3   # JobObjectBasicProcessIdList
_ES_CONTINUOUS, _ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001


class _Accounting(ctypes.Structure):
    _fields_ = [("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64),
                ("ThisPeriodTotalUserTime", ctypes.c_int64), ("ThisPeriodTotalKernelTime", ctypes.c_int64),
                ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]


class _MemoryCounters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def _declare(name, result, *arguments):
    function = getattr(_kernel32, name)
    function.restype, function.argtypes = result, list(arguments)
    return function


_CreateJobObject = _declare("CreateJobObjectW", wintypes.HANDLE, ctypes.c_void_p, wintypes.LPCWSTR)
_AssignProcessToJobObject = _declare("AssignProcessToJobObject", wintypes.BOOL, wintypes.HANDLE, wintypes.HANDLE)
_QueryInformationJobObject = _declare("QueryInformationJobObject", wintypes.BOOL, wintypes.HANDLE, ctypes.c_int,
                                      ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p)
_TerminateJobObject = _declare("TerminateJobObject", wintypes.BOOL, wintypes.HANDLE, wintypes.UINT)
_OpenProcess = _declare("OpenProcess", wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
_GetExitCodeProcess = _declare("GetExitCodeProcess", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
_CloseHandle = _declare("CloseHandle", wintypes.BOOL, wintypes.HANDLE)
_GetProcessMemoryInfo = _declare("K32GetProcessMemoryInfo", wintypes.BOOL, wintypes.HANDLE,
                                 ctypes.POINTER(_MemoryCounters), wintypes.DWORD)
_SetThreadExecutionState = _declare("SetThreadExecutionState", wintypes.DWORD, wintypes.DWORD)


def _failure(operation: str) -> OSError:
    number = ctypes.get_last_error()
    return OSError(number, f"{operation} failed: {ctypes.FormatError(number).strip()}")


def process_alive(pid: int) -> bool:
    """Whether a process with this ID is still running."""
    handle = _OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False  # Gone, or never ours to inspect.
    try:
        code = wintypes.DWORD()
        return bool(_GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == _STILL_ACTIVE
    finally:
        _CloseHandle(handle)


def _memory_counters(pid: int) -> _MemoryCounters | None:
    """A process's memory counters, or None once it has exited."""
    handle = _OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION | _PROCESS_VM_READ, False, pid)
    if not handle:
        if not process_alive(pid):
            return None
        raise _failure(f"Opening process {pid} for memory sampling")
    try:
        counters = _MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not _GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            raise _failure(f"Reading memory of process {pid}")
        return counters
    finally:
        _CloseHandle(handle)


def working_set(pid: int) -> int:
    """A process's resident bytes, or 0 once it has exited."""
    counters = _memory_counters(pid)
    return counters.WorkingSetSize if counters else 0


def peak_working_set(pid: int) -> int:
    """The most resident bytes a process has had (its maximum RSS), or 0 once it has exited."""
    counters = _memory_counters(pid)
    return counters.PeakWorkingSetSize if counters else 0


class ProcessTree:
    """A started process and every process it starts later, held in one job."""

    def __init__(self, pid: int):
        self.pid = pid
        self._job = _CreateJobObject(None, None)
        if not self._job:
            raise _failure("Creating a job object")
        process = _OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE | _PROCESS_QUERY_LIMITED_INFORMATION,
                               False, pid)
        if not process:
            if not process_alive(pid):
                return  # It already finished: an empty job, which reports nothing alive.
            error = _failure(f"Opening process {pid} for its job")
            self.close()
            raise error
        try:
            # Children inherit the job, so only processes the trainer starts
            # before this call could escape it; it starts none that early.
            if not _AssignProcessToJobObject(self._job, process):
                code = wintypes.DWORD()
                if _GetExitCodeProcess(process, ctypes.byref(code)) and code.value != _STILL_ACTIVE:
                    return  # It finished before it could join.
                error = _failure(f"Adding process {pid} to its job")
                self.close()
                raise error
        finally:
            _CloseHandle(process)

    def pids(self) -> list[int]:
        capacity = 256
        while True:
            class _List(ctypes.Structure):
                _fields_ = [("NumberOfAssignedProcesses", wintypes.DWORD),
                            ("NumberOfProcessIdsInList", wintypes.DWORD),
                            ("ProcessIdList", ctypes.c_size_t * capacity)]
            listing = _List()
            if _QueryInformationJobObject(self._job, _PROCESS_ID_LIST, ctypes.byref(listing),
                                          ctypes.sizeof(listing), None):
                return [int(pid) for pid in listing.ProcessIdList[:listing.NumberOfProcessIdsInList]]
            if ctypes.get_last_error() != 234 or capacity >= 65536:  # ERROR_MORE_DATA
                raise _failure("Listing the job's processes")
            capacity *= 4

    def alive(self) -> bool:
        accounting = _Accounting()
        if not _QueryInformationJobObject(self._job, _BASIC_ACCOUNTING, ctypes.byref(accounting),
                                          ctypes.sizeof(accounting), None):
            raise _failure("Reading the job's process count")
        return accounting.ActiveProcesses > 0

    def working_set(self) -> int:
        return sum(working_set(pid) for pid in self.pids())

    def stop(self) -> None:
        """Ask for a safe stop: Ctrl+Break to the trainer's console process group."""
        try:
            os.kill(self.pid, signal.CTRL_BREAK_EVENT)
        except OSError:
            pass  # Already gone, or no shared console; the forced stop follows.

    def kill(self) -> None:
        if not _TerminateJobObject(self._job, 1) and self.alive():
            raise _failure("Terminating the job")

    def close(self) -> None:
        if self._job:
            _CloseHandle(self._job)
            self._job = None


class KeepAwake:
    """Hold off idle sleep while this process runs; terminate() releases it."""

    def __init__(self):
        _SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)

    def terminate(self) -> None:
        _SetThreadExecutionState(_ES_CONTINUOUS)
