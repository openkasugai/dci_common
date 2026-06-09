import signal
import threading
import time
import common

if __name__ == "__main__":
    connection_thread = None

    args = common.parse_args()
    print(f"MEMORY_TYPE: {args.memory_type}")
    signal.signal(
        signal.SIGHUP,
        common.handle_sighup
    )
    print("Waiting for SIGHUP signal...")

    fastapi_thread = threading.Thread(
        target=common.start_fastapi_app, daemon=True
    )
    fastapi_thread.start()

    server_process = None

    while True:
        if server_process is None or server_process.poll() is not None:
            print("Server script stopped. Restarting...")
            server_process = common.run_server_script(args)
        if connection_thread is None or not connection_thread.is_alive():
            connection_thread = threading.Thread(
                target=common.wait_for_signal_and_connect_to_target,
                args=(args,),
                daemon=True
            )
            connection_thread.start()
        time.sleep(1)
