import unittest

from transport import GoogleTransport, TransportError


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    """Отвечает по заданному статусу для каждого client; пишет историю запросов."""
    def __init__(self, statuses):
        self.statuses = statuses
        self.headers = {}
        self.clients_called = []

    def post(self, url, params, data, timeout):
        client = params["client"]
        self.clients_called.append(client)
        status = self.statuses[client]
        payload = [[["Привет", "Hello", None, None]]] if status == 200 else None
        return FakeResponse(status, payload)


def make(statuses, clients=("a", "b", "c")):
    session = FakeSession(statuses)
    sleeps = []
    transport = GoogleTransport(clients=clients, sleep=sleeps.append, session=session)
    return transport, session, sleeps


class GoogleTransportTests(unittest.TestCase):
    def test_falls_back_on_429_without_sleeping(self):
        transport, session, sleeps = make({"a": 429, "b": 429, "c": 200})
        self.assertEqual(transport.translate("Hello"), "Привет")
        self.assertEqual(session.clients_called, ["a", "b", "c"])
        self.assertEqual(sleeps, [])

    def test_remembers_working_client(self):
        transport, session, _ = make({"a": 429, "b": 200, "c": 200})
        transport.translate("x")
        session.clients_called.clear()
        transport.translate("y")
        self.assertEqual(session.clients_called, ["b"])

    def test_all_blocked_raises(self):
        transport, _, sleeps = make({"a": 429, "b": 429, "c": 429})
        with self.assertRaises(TransportError):
            transport.translate("x")
        self.assertEqual(sleeps, [])

    def test_client_error_not_retried(self):
        transport, session, _ = make({"a": 400, "b": 200, "c": 200})
        with self.assertRaises(TransportError):
            transport.translate("x")
        self.assertEqual(session.clients_called, ["a"])


if __name__ == "__main__":
    unittest.main()