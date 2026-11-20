import random
import time
from locust import HttpUser, task, constant, events

state = {
    "count": 0,
    "target": 100,
    "start_time": 0.0,
    "latencies": [],
    "stopped": False,
}


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Mengatur target otomatis (50 untuk Write, 100 untuk Read) saat test dimulai."""
    active_classes = [cls.__name__ for cls in environment.runner.user_classes]
    target = 50 if active_classes == ["WriteTransactionUser"] else 100

    state["count"] = 0
    state["target"] = target
    state["start_time"] = time.perf_counter()
    state["latencies"] = []
    state["stopped"] = False
    print(f"\n[MULAI BENCHMARK] Target: {target} request | Skenario: {active_classes}")


@events.request.add_listener
def on_request(request_type, name, response_time, **kwargs):
    """Mencatat latensi dan mencetak ringkasan tepat saat target request tercapai."""
    if state["stopped"]:
        return

    state["count"] += 1
    state["latencies"].append(response_time)

    if state["count"] >= state["target"]:
        state["stopped"] = True
        elapsed = time.perf_counter() - state["start_time"]
        rps = state["count"] / elapsed if elapsed > 0 else 0.0
        avg_ms = sum(state["latencies"]) / len(state["latencies"])

        print("\n" + "=" * 60)
        print(f"HASIL BENCHMARK ({name} - {state['count']} Request)")
        print(f"Total Waktu       : {elapsed:.2f} detik")
        print(f"Throughput        : {rps:.2f} req/s")
        print(f"Rata-rata Latensi : {avg_ms:.2f} ms")
        print("=" * 60 + "\n")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Menghentikan Locust secara otomatis setelah target request terpenuhi."""
    @events.request.add_listener
    def auto_stop_handler(**req_kwargs):
        if state["stopped"] and environment.runner:
            if environment.web_ui:
                environment.runner.stop()
            else:
                environment.runner.quit()


class ReadConsoleUser(HttpUser):
    """Skenario Read: GET /consoles."""
    wait_time = constant(0.1)

    @task
    def get_consoles(self):
        if not state["stopped"]:
            self.client.get("/consoles?skip=0&limit=10", name="GET /consoles")


class WriteTransactionUser(HttpUser):
    """Skenario Write: POST /transactions."""
    wait_time = constant(0.1)

    @task
    def post_transaction(self):
        if not state["stopped"]:
            payload = {
                "console_id": random.randint(1, 12),
                "nama_penyewa": f"User_LoadTest_{random.randint(1, 1000)}",
                "qty": 1,
                "durasi_jam": random.choice([1, 2, 3]),
            }
            with self.client.post(
                "/transactions",
                json=payload,
                name="POST /transactions",
                catch_response=True,
            ) as response:
                if response.status_code in (202, 409):
                    response.success()
                else:
                    response.failure(f"Status tak terduga: {response.status_code}")