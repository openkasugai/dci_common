import threading
import time
import common

if __name__ == "__main__":
    args = common.parse_args()
    print(f"MEMORY_TYPE: {args.memory_type}")

    fastapi_thread = threading.Thread(
        target=common.start_fastapi_app, daemon=True
    )
    fastapi_thread.start()

    server_process = None

    while True:
        if server_process is None or server_process.poll() is not None:
            print("Server script stopped. Restarting...")
            server_process = common.run_server_script(args)
        time.sleep(1)
