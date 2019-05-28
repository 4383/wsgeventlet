import argparse
import contextlib
import socket
import time
import threading

import kombu
import kombu.connection
import kombu.entity
import kombu.messaging
from kombu import Producer
from kombu import Exchange

from oslo_utils import eventletutils


class DummyLock(object):
    def acquire(self):
        pass

    def release(self):
        pass

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()


class DummyConnectionLock(DummyLock):
    def heartbeat_acquire(self):
        pass


class ConnectionLock(DummyConnectionLock):
    """Lock object to protect access to the kombu connection

    This is a lock object to protect access to the kombu connection
    object between the heartbeat thread and the driver thread.

    They are two way to acquire this lock:
        * lock.acquire()
        * lock.heartbeat_acquire()

    In both case lock.release(), release the lock.

    The goal is that the heartbeat thread always have the priority
    for acquiring the lock. This ensures we have no heartbeat
    starvation when the driver sends a lot of messages.

    So when lock.heartbeat_acquire() is called next time the lock
    is released(), the caller unconditionally acquires
    the lock, even someone else have asked for the lock before it.
    """

    def __init__(self):
        self._workers_waiting = 0
        self._heartbeat_waiting = False
        self._lock_acquired = None
        self._monitor = threading.Lock()
        self._workers_locks = threading.Condition(self._monitor)
        self._heartbeat_lock = threading.Condition(self._monitor)
        self._get_thread_id = eventletutils.fetch_current_thread_functor()

    def acquire(self):
        with self._monitor:
            while self._lock_acquired:
                self._workers_waiting += 1
                self._workers_locks.wait()
                self._workers_waiting -= 1
            self._lock_acquired = self._get_thread_id()

    def heartbeat_acquire(self):
        # NOTE(sileht): must be called only one time
        with self._monitor:
            while self._lock_acquired is not None:
                self._heartbeat_waiting = True
                self._heartbeat_lock.wait()
                self._heartbeat_waiting = False
            self._lock_acquired = self._get_thread_id()

    def release(self):
        with self._monitor:
            if self._lock_acquired is None:
                raise RuntimeError("We can't release a not acquired lock")
            thread_id = self._get_thread_id()
            if self._lock_acquired != thread_id:
                raise RuntimeError("We can't release lock acquired by another "
                                   "thread/greenthread; %s vs %s" %
                                   (self._lock_acquired, thread_id))
            self._lock_acquired = None
            if self._heartbeat_waiting:
                self._heartbeat_lock.notify()
            elif self._workers_waiting > 0:
                self._workers_locks.notify()

    @contextlib.contextmanager
    def for_heartbeat(self):
        self.heartbeat_acquire()
        try:
            yield
        finally:
            self.release()


class Connection(object):
    """Connection object."""

    def __init__(self, heartbeat_timeout=60):
        print("Initialize the heartbeat")
        self._connection_lock = ConnectionLock()
        self._heartbeat_wait_timeout = heartbeat_timeout
        self._heartbeat_start()

    def _heartbeat_start(self):
        self._heartbeat_exit_event = eventletutils.Event()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_thread_job)
        self._heartbeat_thread.daemon = True
        self._heartbeat_thread.start()
        with self._connection_lock:
            print("heartbeat started")

    def _heartbeat_stop(self):
        self._heartbeat_exit_event.set()
        self._heartbeat_thread.join()
        self._heartbeat_thread = None
        print("heartbeat stoped")

    def _heartbeat_check(self):
        print("heartbeat check")
        time.sleep(10)

    def _heartbeat_thread_job(self):
        """Thread that maintains inactive connections
        """
        print("running heartbeat thread job")
        while not self._heartbeat_exit_event.is_set():
            with self._connection_lock.for_heartbeat():
                self._heartbeat_check()

        self._heartbeat_exit_event.clear()
        print("thread job done!")
